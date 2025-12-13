"""
ROTAS: TENANTS (CORRIGIDO)
===========================

Endpoints para gerenciar tenants (empresas clientes).

CORREÇÃO: Endpoint /niches agora busca do banco de dados
ao invés de retornar lista hardcoded.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.domain.entities import Tenant, User, Channel, Niche  # ← Adicionado Niche
from src.api.schemas import TenantCreate, TenantResponse, NicheInfo

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.get("/niches", response_model=list[NicheInfo])
async def list_niches(
    db: AsyncSession = Depends(get_db),  # ← Adicionado db
):
    """
    Lista todos os nichos disponíveis.
    
    CORRIGIDO: Agora busca do banco de dados (tabela Niche)
    ao invés de retornar lista hardcoded.
    """
    
    # Busca nichos ativos do banco
    result = await db.execute(
        select(Niche)
        .where(Niche.active == True)
        .order_by(Niche.name)
    )
    niches = result.scalars().all()
    
    # Retorna no formato esperado pelo frontend
    return [
        {
            "id": niche.slug,  # Frontend usa slug como id
            "name": niche.name,
            "description": niche.description or "",
        }
        for niche in niches
    ]


@router.post("", response_model=TenantResponse)
async def create_tenant(
    payload: TenantCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Cria um novo tenant.
    
    Este endpoint é usado no onboarding de novos clientes.
    """
    
    # Verifica se slug já existe
    result = await db.execute(
        select(Tenant).where(Tenant.slug == payload.slug)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="Slug já está em uso")
    
    # Cria tenant
    tenant = Tenant(
        name=payload.name,
        slug=payload.slug,
        plan=payload.plan,
        settings=payload.settings.model_dump(),
        active=True,
    )
    db.add(tenant)
    await db.flush()
    
    # Cria canal WhatsApp padrão
    channel = Channel(
        tenant_id=tenant.id,
        type="whatsapp",
        name="WhatsApp Principal",
        config={},
        active=True,
    )
    db.add(channel)
    
    await db.commit()
    await db.refresh(tenant)
    
    return TenantResponse.model_validate(tenant)


@router.get("/{slug}", response_model=TenantResponse)
async def get_tenant(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Busca tenant por slug."""
    
    result = await db.execute(
        select(Tenant).where(Tenant.slug == slug)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    
    return TenantResponse.model_validate(tenant)


@router.patch("/{slug}", response_model=TenantResponse)
async def update_tenant(
    slug: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """Atualiza configurações do tenant."""
    
    result = await db.execute(
        select(Tenant).where(Tenant.slug == slug)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    
    # Atualiza campos permitidos
    allowed_fields = ["name", "plan", "settings", "active"]
    
    for field, value in payload.items():
        if field in allowed_fields and hasattr(tenant, field):
            setattr(tenant, field, value)
    
    await db.commit()
    await db.refresh(tenant)
    
    return TenantResponse.model_validate(tenant)