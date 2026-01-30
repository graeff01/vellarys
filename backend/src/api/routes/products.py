"""
ROTAS: PRODUCTS (PRODUTOS/SERVIÇOS)
===================================

CRUD genérico para gerenciar produtos ou serviços do tenant.
Substitui o antigo sistema de "Empreendimentos".
"""

import re
import logging
from typing import Optional, List, Any, Dict
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.domain.entities import User, Tenant, Seller, Product
from src.api.dependencies import get_current_user, get_current_tenant
from src.infrastructure.services.multi_tenant_property_service import MultiTenantPropertyService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["Produtos"])


# ==========================================
# SCHEMAS (Pydantic)
# ==========================================

class ProductCreate(BaseModel):
    """Schema para criar um produto genérico."""
    name: str = Field(..., min_length=2, max_length=200)
    status: str = Field(default="active")
    description: Optional[str] = None
    url_landing_page: Optional[str] = None
    image_url: Optional[str] = None
    
    # Gatilhos de detecção pela IA
    triggers: List[str] = Field(default_factory=list)
    priority: int = Field(default=0, ge=0, le=100)
    
    # Qualificação
    qualification_questions: List[str] = Field(default_factory=list)
    ai_instructions: Optional[str] = None
    
    # Destino leads
    seller_id: Optional[int] = None
    distribution_method: Optional[str] = None
    notify_manager: bool = False
    
    # Atributos dinâmicos (onde entram campos específicos de nicho)
    attributes: Dict[str, Any] = Field(default_factory=dict)


class ProductUpdate(BaseModel):
    """Schema para atualizar um produto."""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    status: Optional[str] = None
    description: Optional[str] = None
    url_landing_page: Optional[str] = None
    image_url: Optional[str] = None
    active: Optional[bool] = None
    
    triggers: Optional[List[str]] = None
    priority: Optional[int] = None
    
    qualification_questions: Optional[List[str]] = None
    ai_instructions: Optional[str] = None
    
    seller_id: Optional[int] = None
    distribution_method: Optional[str] = None
    notify_manager: Optional[bool] = None
    
    attributes: Optional[Dict[str, Any]] = None


class ProductResponse(BaseModel):
    """Schema de resposta simplificado."""
    id: int
    name: str
    slug: str
    status: str
    active: bool
    total_leads: int
    qualified_leads: int
    seller_name: Optional[str] = None
    attributes: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# HELPERS
# ==========================================

def generate_slug(name: str) -> str:
    """Gera slug a partir do nome."""
    slug = name.lower().strip()
    slug = re.sub(r'[àáâãäå]', 'a', slug)
    slug = re.sub(r'[èéêë]', 'e', slug)
    slug = re.sub(r'[ìíîï]', 'i', slug)
    slug = re.sub(r'[òóôõö]', 'o', slug)
    slug = re.sub(r'[ùúûü]', 'u', slug)
    slug = re.sub(r'[ç]', 'c', slug)
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    return slug


# ==========================================
# ENDPOINTS
# ==========================================

@router.get("/stats")
async def products_stats(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Retorna estatísticas gerais de produtos."""
    total_result = await db.execute(
        select(func.count(Product.id)).where(Product.tenant_id == tenant.id)
    )
    active_result = await db.execute(
        select(func.count(Product.id)).where(Product.tenant_id == tenant.id, Product.active == True)
    )
    
    leads_result = await db.execute(
        select(func.sum(Product.total_leads)).where(Product.tenant_id == tenant.id)
    )
    qualified_result = await db.execute(
        select(func.sum(Product.qualified_leads)).where(Product.tenant_id == tenant.id)
    )
    
    return {
        "total": total_result.scalar() or 0,
        "active": active_result.scalar() or 0,
        "total_leads": leads_result.scalar() or 0,
        "qualified_leads": qualified_result.scalar() or 0,
    }


@router.get("")
async def list_products(
    active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Lista produtos do tenant."""
    query = select(Product).where(Product.tenant_id == tenant.id)
    
    if active is not None:
        query = query.where(Product.active == active)
    
    if search:
        query = query.where(Product.name.ilike(f"%{search}%"))
        
    query = query.order_by(Product.priority.desc(), Product.name)
    
    result = await db.execute(query)
    products = list(result.scalars().all())
    
    # Se houver busca por termo, tentamos também nas fontes externas (on-the-fly)
    if search and len(products) < 15:
        try:
            property_service = MultiTenantPropertyService(db, tenant.id)
            
            async def normalize_ext(ext):
                # Converte o preço formatado "R$ 500.000" de volta para centavos se possível
                try:
                    price_str = ext.get("preco", "0")
                    # No PropertyResult o preço original também está lá se precisássemos, 
                    # mas vamos inferir do formatado por segurança ou usar o raw_data
                    raw_price = ext.get("preco") # Atualmente o legacy_dict tem o price_formatted aqui
                    # Vamos assumir que se for string com R$, limpamos.
                    if isinstance(price_str, str) and "R$" in price_str:
                         v = price_str.replace("R$", "").replace(".", "").replace(",", ".").strip()
                         cents = int(float(v) * 100) if v else 0
                    else:
                         cents = int(float(price_str) * 100) if price_str else 0
                except:
                    cents = 0

                return {
                    "id": 0,
                    "name": ext.get("titulo"),
                    "description": ext.get("descricao"),
                    "active": True,
                    "status": "active",
                    "attributes": {
                        **ext,
                        "codigo": ext.get("codigo"),
                        "tipo": ext.get("tipo"),
                        "regiao": ext.get("regiao"),
                        "preco": cents,
                        "quartos": ext.get("quartos"),
                        "banheiros": ext.get("banheiros"),
                        "vagas": ext.get("vagas"),
                        "metragem": ext.get("metragem")
                    }
                }

            # Busca por código (prioridade)
            ext_by_code = await property_service.buscar_por_codigo(search)
            if ext_by_code:
                # Evita duplicado se já estiver no DB
                exists_in_db = any(getattr(p, "attributes", {}).get("codigo") == ext_by_code.get("codigo") for p in products)
                if not exists_in_db:
                    products.insert(0, await normalize_ext(ext_by_code))

            # Busca por critérios (região/nome)
            external_results = await property_service.buscar_por_criterios(regiao=search, limit=10)
            for ext in external_results:
                # Evita duplicados
                existing_codes = []
                for p in products:
                    if hasattr(p, "attributes"):
                        existing_codes.append(p.attributes.get("codigo"))
                    elif isinstance(p, dict):
                        existing_codes.append(p.get("attributes", {}).get("codigo"))

                if ext.get("codigo") not in existing_codes:
                     products.append(await normalize_ext(ext))
        except Exception as e:
            logger.error(f"Erro ao buscar produtos externos: {e}", exc_info=True)
    
    return products


@router.post("")
async def create_product(
    payload: ProductCreate,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Cria um novo produto."""
    slug = generate_slug(payload.name)
    
    # Verifica slug duplicado
    check = await db.execute(
        select(Product).where(Product.tenant_id == tenant.id, Product.slug == slug)
    )
    if check.scalar_one_or_none():
        slug = f"{slug}-{int(datetime.now().timestamp())}"

    product = Product(
        tenant_id=tenant.id,
        name=payload.name,
        slug=slug,
        status=payload.status,
        description=payload.description,
        url_landing_page=payload.url_landing_page,
        image_url=payload.image_url,
        triggers=payload.triggers,
        priority=payload.priority,
        qualification_questions=payload.qualification_questions,
        ai_instructions=payload.ai_instructions,
        seller_id=payload.seller_id,
        distribution_method=payload.distribution_method,
        notify_manager=payload.notify_manager,
        attributes=payload.attributes
    )
    
    db.add(product)
    await db.commit()
    await db.refresh(product)
    
    return product


@router.get("/check-access")
async def check_access(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Verifica se o tenant tem acesso ao módulo de produtos/imóveis."""
    # Por padrão, no Vellarys, quase todos têm acesso. 
    # Podemos colocar lógica de plano aqui no futuro.
    return {
        "has_access": True,
        "niche": tenant.settings.get("basic", {}).get("niche", "services") if tenant.settings else "services"
    }


@router.get("/{product_id}")
async def get_product(
    product_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant.id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return product


@router.patch("/{product_id}")
async def update_product(
    product_id: int,
    payload: ProductUpdate,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant.id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
        
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(product, key, value)
        
    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant.id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
        
    await db.delete(product)
    await db.commit()
    return {"success": True}
