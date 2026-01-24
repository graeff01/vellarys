"""
API: INFORMAÇÕES DO CORRETOR
=============================
Endpoints auxiliares para o frontend do CRM Inbox.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from src.infrastructure.database import get_db
from src.domain.entities import User, Seller, Tenant
from src.domain.entities.enums import UserRole
from src.api.dependencies import get_current_user


router = APIRouter(prefix="/seller/info", tags=["Seller Info"])


# =============================================================================
# SCHEMAS
# =============================================================================

class SellerInfoResponse(BaseModel):
    """Informações completas do corretor logado."""

    # Dados do usuário
    user_id: int
    user_name: str
    user_email: str
    user_role: str

    # Dados do seller (se vinculado)
    seller_id: Optional[int]
    seller_name: Optional[str]
    seller_whatsapp: Optional[str]
    seller_active: Optional[bool]

    # Configuração do tenant
    tenant_id: int
    tenant_name: str
    tenant_slug: str
    handoff_mode: str  # "crm_inbox" ou "whatsapp_pessoal"

    # Estatísticas do corretor
    total_leads: Optional[int]
    leads_today: Optional[int]
    conversion_rate: Optional[float]

    # Status
    is_linked: bool  # Se user está vinculado a um seller
    can_use_inbox: bool  # Se pode usar o inbox (linked + crm_inbox mode)

    class Config:
        from_attributes = True


class TenantConfigResponse(BaseModel):
    """Configuração do tenant para o frontend."""
    tenant_id: int
    tenant_name: str
    handoff_mode: str
    crm_inbox_enabled: bool

    class Config:
        from_attributes = True


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/me", response_model=SellerInfoResponse)
async def get_seller_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna informações completas do corretor logado.

    **Usado pelo frontend para:**
    - Saber se corretor está vinculado
    - Verificar se inbox está disponível
    - Mostrar estatísticas
    - Configurar interface
    """

    # Verifica se é corretor
    if current_user.role != UserRole.SELLER:
        raise HTTPException(
            status_code=403,
            detail="Apenas corretores podem acessar este endpoint"
        )

    # Busca seller vinculado
    seller_result = await db.execute(
        select(Seller)
        .where(Seller.user_id == current_user.id)
        .where(Seller.tenant_id == current_user.tenant_id)
    )
    seller = seller_result.scalar_one_or_none()

    # Busca tenant
    tenant_result = await db.execute(
        select(Tenant)
        .where(Tenant.id == current_user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=404,
            detail="Tenant não encontrado"
        )

    # Verifica modo de handoff
    handoff_mode = tenant.settings.get("handoff_mode", "whatsapp_pessoal") if tenant.settings else "whatsapp_pessoal"

    # Monta response
    return SellerInfoResponse(
        # User
        user_id=current_user.id,
        user_name=current_user.name,
        user_email=current_user.email,
        user_role=current_user.role,

        # Seller (se vinculado)
        seller_id=seller.id if seller else None,
        seller_name=seller.name if seller else None,
        seller_whatsapp=seller.whatsapp if seller else None,
        seller_active=seller.active if seller else None,

        # Tenant
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        tenant_slug=tenant.slug,
        handoff_mode=handoff_mode,

        # Estatísticas
        total_leads=seller.total_leads if seller else 0,
        leads_today=seller.leads_today if seller else 0,
        conversion_rate=seller.conversion_rate if seller else 0.0,

        # Status
        is_linked=(seller is not None),
        can_use_inbox=(seller is not None and handoff_mode == "crm_inbox"),
    )


@router.get("/tenant-config", response_model=TenantConfigResponse)
async def get_tenant_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna configuração do tenant.

    **Usado pelo frontend para:**
    - Saber se deve mostrar tela de inbox
    - Adaptar interface baseado no modo
    """

    # Busca tenant
    tenant_result = await db.execute(
        select(Tenant)
        .where(Tenant.id == current_user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=404,
            detail="Tenant não encontrado"
        )

    handoff_mode = tenant.settings.get("handoff_mode", "whatsapp_pessoal") if tenant.settings else "whatsapp_pessoal"

    return TenantConfigResponse(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        handoff_mode=handoff_mode,
        crm_inbox_enabled=(handoff_mode == "crm_inbox"),
    )


@router.get("/check-inbox-available")
async def check_inbox_available(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Verifica rapidamente se o inbox está disponível para o usuário.

    **Usado pelo frontend para:**
    - Mostrar/esconder menu do inbox
    - Redirecionar corretores para página correta

    **Response:**
    ```json
    {
        "available": true,
        "reason": "CRM Inbox habilitado e corretor vinculado",
        "handoff_mode": "crm_inbox"
    }
    ```
    """

    # Verifica se é corretor
    if current_user.role != UserRole.SELLER:
        return {
            "available": False,
            "reason": "Usuário não é corretor",
            "handoff_mode": None,
        }

    # Busca tenant
    tenant_result = await db.execute(
        select(Tenant)
        .where(Tenant.id == current_user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()

    if not tenant:
        return {
            "available": False,
            "reason": "Tenant não encontrado",
            "handoff_mode": None,
        }

    handoff_mode = tenant.settings.get("handoff_mode", "whatsapp_pessoal") if tenant.settings else "whatsapp_pessoal"

    # Se não está no modo CRM Inbox, inbox não disponível
    if handoff_mode != "crm_inbox":
        return {
            "available": False,
            "reason": f"Tenant está no modo '{handoff_mode}' (precisa ser 'crm_inbox')",
            "handoff_mode": handoff_mode,
        }

    # Busca seller vinculado
    seller_result = await db.execute(
        select(Seller)
        .where(Seller.user_id == current_user.id)
        .where(Seller.tenant_id == current_user.tenant_id)
    )
    seller = seller_result.scalar_one_or_none()

    if not seller:
        return {
            "available": False,
            "reason": "Corretor não vinculado a um seller. Contate o administrador.",
            "handoff_mode": handoff_mode,
        }

    # Tudo OK!
    return {
        "available": True,
        "reason": "CRM Inbox habilitado e corretor vinculado",
        "handoff_mode": handoff_mode,
        "seller_id": seller.id,
        "seller_name": seller.name,
    }
