"""
API Routes: Response Templates
================================

CRUD de templates de respostas rápidas para vendedores.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.domain.entities.response_template import ResponseTemplate
from src.domain.entities.models import Tenant, User
from src.infrastructure.database import get_db
from src.api.dependencies import get_current_user, get_current_tenant


router = APIRouter(prefix="/templates", tags=["templates"])


# =============================================================================
# SCHEMAS
# =============================================================================

class TemplateCreate(BaseModel):
    """Criar template."""
    name: str = Field(..., min_length=3, max_length=100)
    shortcut: Optional[str] = Field(None, max_length=20, pattern=r"^/[a-z0-9_]+$")
    content: str = Field(..., min_length=10, max_length=2000)
    category: Optional[str] = Field(None, max_length=50)
    is_active: bool = True


class TemplateUpdate(BaseModel):
    """Atualizar template."""
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    shortcut: Optional[str] = Field(None, max_length=20, pattern=r"^/[a-z0-9_]+$")
    content: Optional[str] = Field(None, min_length=10, max_length=2000)
    category: Optional[str] = None
    is_active: Optional[bool] = None


class TemplateResponse(BaseModel):
    """Resposta de template."""
    id: int
    name: str
    shortcut: Optional[str]
    content: str
    category: Optional[str]
    is_active: bool
    usage_count: int
    created_by_user_id: Optional[int]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("", response_model=List[TemplateResponse])
async def list_templates(
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista templates do tenant com filtros.

    Filtros:
    - category: Categoria do template (saudacao, followup, etc)
    - is_active: Apenas ativos (true) ou todos
    - search: Busca por nome ou conteúdo
    """
    query = select(ResponseTemplate).where(ResponseTemplate.tenant_id == tenant.id)

    # Filtros
    if category:
        query = query.where(ResponseTemplate.category == category)

    if is_active is not None:
        query = query.where(ResponseTemplate.is_active == is_active)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            (ResponseTemplate.name.ilike(search_term)) |
            (ResponseTemplate.content.ilike(search_term))
        )

    # Ordenar por uso e depois por nome
    query = query.order_by(
        ResponseTemplate.usage_count.desc(),
        ResponseTemplate.name
    )

    result = await db.execute(query)
    templates = result.scalars().all()

    return templates


@router.get("/categories", response_model=List[dict])
async def list_categories(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista categorias de templates com contagem.

    Retorna: [{"category": "saudacao", "count": 5}, ...]
    """
    query = select(
        ResponseTemplate.category,
        func.count(ResponseTemplate.id).label("count")
    ).where(
        ResponseTemplate.tenant_id == tenant.id,
        ResponseTemplate.is_active == True
    ).group_by(
        ResponseTemplate.category
    ).order_by(
        ResponseTemplate.category
    )

    result = await db.execute(query)
    categories = [
        {"category": cat, "count": count}
        for cat, count in result.all()
    ]

    return categories


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Busca template por ID."""
    template = await db.get(ResponseTemplate, template_id)

    if not template or template.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template não encontrado"
        )

    return template


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: TemplateCreate,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Cria novo template.

    Variáveis disponíveis:
    - {{lead_name}}
    - {{seller_name}}
    - {{current_date}}
    - {{current_time}}
    - {{company_name}}
    """
    # Validar se shortcut já existe
    if payload.shortcut:
        existing = await db.execute(
            select(ResponseTemplate).where(
                ResponseTemplate.tenant_id == tenant.id,
                ResponseTemplate.shortcut == payload.shortcut
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Atalho '{payload.shortcut}' já existe"
            )

    template = ResponseTemplate(
        tenant_id=tenant.id,
        created_by_user_id=user.id,
        name=payload.name,
        shortcut=payload.shortcut,
        content=payload.content,
        category=payload.category,
        is_active=payload.is_active,
    )

    db.add(template)
    await db.commit()
    await db.refresh(template)

    return template


@router.patch("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int,
    payload: TemplateUpdate,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Atualiza template existente."""
    template = await db.get(ResponseTemplate, template_id)

    if not template or template.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template não encontrado"
        )

    # Validar shortcut se estiver mudando
    if payload.shortcut and payload.shortcut != template.shortcut:
        existing = await db.execute(
            select(ResponseTemplate).where(
                ResponseTemplate.tenant_id == tenant.id,
                ResponseTemplate.shortcut == payload.shortcut,
                ResponseTemplate.id != template_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Atalho '{payload.shortcut}' já existe"
            )

    # Atualizar campos
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    await db.commit()
    await db.refresh(template)

    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Deleta template."""
    template = await db.get(ResponseTemplate, template_id)

    if not template or template.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template não encontrado"
        )

    await db.delete(template)
    await db.commit()

    return None


@router.post("/{template_id}/use", response_model=dict)
async def increment_usage(
    template_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Incrementa contador de uso do template.

    Chamado automaticamente quando vendedor usa o template.
    """
    template = await db.get(ResponseTemplate, template_id)

    if not template or template.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template não encontrado"
        )

    template.usage_count += 1
    await db.commit()

    return {
        "success": True,
        "template_id": template_id,
        "new_usage_count": template.usage_count
    }


@router.post("/{template_id}/interpolate", response_model=dict)
async def interpolate_template(
    template_id: int,
    lead_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Interpola variáveis do template com dados reais do lead.

    Busca dados do lead e vendedor, substitui variáveis e retorna conteúdo pronto.
    Também incrementa contador de uso automaticamente.
    """
    from datetime import datetime
    from src.domain.entities.models import Lead
    from src.domain.entities.seller import Seller

    # Buscar template
    template = await db.get(ResponseTemplate, template_id)
    if not template or template.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template não encontrado"
        )

    # Buscar lead
    lead = await db.get(Lead, lead_id)
    if not lead or lead.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead não encontrado"
        )

    # Buscar vendedor (se existir seller_id no lead)
    seller_name = user.name  # Default: nome do usuário atual
    if hasattr(lead, 'seller_id') and lead.seller_id:
        seller = await db.get(Seller, lead.seller_id)
        if seller:
            seller_name = seller.name

    # Interpolar variáveis
    content = template.content
    content = content.replace("{{lead_name}}", lead.name or "Cliente")
    content = content.replace("{{seller_name}}", seller_name)
    content = content.replace("{{company_name}}", tenant.name)
    content = content.replace("{{current_date}}", datetime.now().strftime("%d/%m/%Y"))
    content = content.replace("{{current_time}}", datetime.now().strftime("%H:%M"))

    # Incrementar contador de uso
    template.usage_count += 1
    await db.commit()

    return {
        "template_id": template_id,
        "content": content,
        "variables_used": {
            "lead_name": lead.name,
            "seller_name": seller_name,
            "company_name": tenant.name,
            "current_date": datetime.now().strftime("%d/%m/%Y"),
            "current_time": datetime.now().strftime("%H:%M"),
        }
    }


@router.post("/preview", response_model=dict)
async def preview_template(
    content: str,
    lead_name: str = "João Silva",
    seller_name: str = "Maria Santos",
    company_name: str = "Empresa X",
    user: User = Depends(get_current_user),
):
    """
    Pré-visualiza template com variáveis substituídas.

    Útil para mostrar ao vendedor como ficará a mensagem final.
    """
    from datetime import datetime

    # Substituir variáveis
    preview = content
    preview = preview.replace("{{lead_name}}", lead_name)
    preview = preview.replace("{{seller_name}}", seller_name)
    preview = preview.replace("{{company_name}}", company_name)
    preview = preview.replace("{{current_date}}", datetime.now().strftime("%d/%m/%Y"))
    preview = preview.replace("{{current_time}}", datetime.now().strftime("%H:%M"))

    return {
        "original": content,
        "preview": preview,
        "variables_used": {
            "lead_name": lead_name,
            "seller_name": seller_name,
            "company_name": company_name,
            "current_date": datetime.now().strftime("%d/%m/%Y"),
            "current_time": datetime.now().strftime("%H:%M"),
        }
    }
