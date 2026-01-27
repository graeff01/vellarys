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
from sqlalchemy.orm.attributes import flag_modified
from pydantic import BaseModel
from typing import Literal

from src.infrastructure.database import get_db
from src.domain.entities import Tenant, User, Channel, Niche  # ← Adicionado Niche
from src.api.schemas import TenantCreate, TenantResponse, NicheInfo
from src.api.dependencies import get_current_user
from src.domain.entities.enums import UserRole

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
    current_user: User = Depends(get_current_user), # 🔥 Adicionado autenticação
):
    """Busca tenant por slug."""
    
    result = await db.execute(
        select(Tenant).where(Tenant.slug == slug)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    
    # 🛡️ PROTEÇÃO: Apenas superadmin ou o administrador do próprio tenant pode ver os detalhes
    if current_user.role != UserRole.SUPERADMIN and current_user.tenant_id != tenant.id:
        raise HTTPException(status_code=403, detail="Você não tem permissão para visualizar este tenant")
    
    return TenantResponse.model_validate(tenant)


@router.patch("/{slug}", response_model=TenantResponse)
async def update_tenant(
    slug: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user), # 🔥 Adicionado autenticação
):
    """Atualiza configurações do tenant."""

    result = await db.execute(
        select(Tenant).where(Tenant.slug == slug)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    # 🛡️ PROTEÇÃO: Apenas admins do próprio tenant ou superadmin
    if current_user.role != UserRole.SUPERADMIN and (current_user.tenant_id != tenant.id or current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]):
        raise HTTPException(status_code=403, detail="Apenas administradores podem modificar as configurações da empresa")

    # Atualiza campos permitidos
    allowed_fields = ["name", "plan", "settings", "active"]

    for field, value in payload.items():
        if field in allowed_fields and hasattr(tenant, field):
            setattr(tenant, field, value)

    await db.commit()
    await db.refresh(tenant)

    return TenantResponse.model_validate(tenant)


# =============================================================================
# CONFIGURAÇÃO DE HANDOFF MODE (CRM INBOX)
# =============================================================================

class HandoffModeConfig(BaseModel):
    """Schema para configuração de handoff mode."""
    handoff_mode: Literal["crm_inbox", "whatsapp_pessoal"]


class HandoffModeResponse(BaseModel):
    """Response com configuração atual."""
    success: bool
    handoff_mode: str
    message: str


@router.post("/{slug}/handoff-mode", response_model=HandoffModeResponse)
async def configure_handoff_mode(
    slug: str,
    config: HandoffModeConfig,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Configura o modo de handoff do tenant.

    MODOS DISPONÍVEIS:

    1. **crm_inbox** (NOVO):
       - IA atende e qualifica lead
       - Sistema atribui lead ao corretor
       - Corretor recebe notificação
       - Corretor faz login no CRM
       - Corretor responde pelo CRM (usando WhatsApp da empresa)
       - IA para de responder quando corretor assume

    2. **whatsapp_pessoal** (LEGADO):
       - IA atende e qualifica lead
       - Sistema envia lead para WhatsApp pessoal do corretor
       - Corretor responde pelo WhatsApp pessoal

    **Requisito**: Apenas ADMIN, MANAGER ou SUPERADMIN podem alterar.
    """

    # Verifica permissão
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=403,
            detail="Apenas administradores podem configurar o modo de handoff"
        )

    # Busca tenant
    result = await db.execute(
        select(Tenant).where(Tenant.slug == slug)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    # Verifica se user pertence ao tenant
    if current_user.tenant_id != tenant.id and current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para modificar este tenant"
        )

    # Atualiza configuração
    if not tenant.settings:
        tenant.settings = {}

    old_mode = tenant.settings.get("handoff_mode", "whatsapp_pessoal")
    tenant.settings["handoff_mode"] = config.handoff_mode
    flag_modified(tenant, "settings")

    await db.commit()

    # Monta mensagem explicativa
    messages = {
        "crm_inbox": "✅ Modo CRM Inbox ativado! Agora os corretores podem atender via painel do CRM. Configure os usuários corretores em Equipe > Corretores.",
        "whatsapp_pessoal": "✅ Modo WhatsApp Pessoal ativado! Os leads qualificados serão enviados para o WhatsApp pessoal dos corretores."
    }

    return HandoffModeResponse(
        success=True,
        handoff_mode=config.handoff_mode,
        message=messages[config.handoff_mode]
    )


@router.get("/{slug}/handoff-mode", response_model=HandoffModeResponse)
async def get_handoff_mode(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retorna o modo de handoff atual do tenant.
    """

    # Busca tenant
    result = await db.execute(
        select(Tenant).where(Tenant.slug == slug)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    # Verifica se user pertence ao tenant
    if current_user.tenant_id != tenant.id and current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para acessar este tenant"
        )

    # Retorna configuração atual (padrão: whatsapp_pessoal)
    current_mode = tenant.settings.get("handoff_mode", "whatsapp_pessoal") if tenant.settings else "whatsapp_pessoal"

    descriptions = {
        "crm_inbox": "Modo CRM Inbox: Corretores atendem via painel",
        "whatsapp_pessoal": "Modo WhatsApp Pessoal: Leads enviados para WhatsApp do corretor"
    }

    return HandoffModeResponse(
        success=True,
        handoff_mode=current_mode,
        message=descriptions[current_mode]
    )