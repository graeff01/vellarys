"""
ROTAS: REENGAJAMENTO
=====================

Endpoints para gerenciar reengajamento de leads inativos.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.domain.entities import Lead, Tenant, User
from src.api.dependencies import get_current_user, get_current_tenant
from src.infrastructure.services import (
    get_leads_to_reengage,
    execute_reengagement,
    process_reengagement_batch,
    get_reengagement_message,
    DEFAULT_REENGAGEMENT_CONFIG,
)

router = APIRouter(prefix="/reengagement", tags=["Reengagement"])


# ==========================================
# SCHEMAS
# ==========================================

class ReengagementConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    inactivity_hours: Optional[int] = None
    max_attempts: Optional[int] = None
    min_hours_between_attempts: Optional[int] = None
    respect_business_hours: Optional[bool] = None
    exclude_hot_leads: Optional[bool] = None
    exclude_handed_off: Optional[bool] = None
    custom_message: Optional[str] = None


class ManualReengageRequest(BaseModel):
    lead_id: int
    custom_message: Optional[str] = None


# ==========================================
# ENDPOINTS
# ==========================================

@router.get("/config")
async def get_reengagement_config(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """
    Retorna a configuração atual de reengajamento.
    """
    settings = tenant.settings or {}
    config = {**DEFAULT_REENGAGEMENT_CONFIG, **settings.get("reengagement", {})}
    
    return {
        "config": config,
        "templates_available": True,
    }


@router.patch("/config")
async def update_reengagement_config(
    payload: ReengagementConfigUpdate,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Atualiza a configuração de reengajamento.
    """
    settings = tenant.settings or {}
    current_config = settings.get("reengagement", {})
    
    # Atualiza apenas os campos enviados
    update_data = payload.model_dump(exclude_unset=True)
    new_config = {**current_config, **update_data}
    
    # Validações
    if new_config.get("inactivity_hours", 24) < 1:
        raise HTTPException(status_code=400, detail="Tempo de inatividade deve ser pelo menos 1 hora")
    
    if new_config.get("max_attempts", 3) < 1 or new_config.get("max_attempts", 3) > 10:
        raise HTTPException(status_code=400, detail="Máximo de tentativas deve ser entre 1 e 10")
    
    # Salva
    settings["reengagement"] = new_config
    tenant.settings = settings
    
    await db.commit()
    
    return {
        "success": True,
        "config": new_config,
    }


@router.get("/pending")
async def get_pending_reengagements(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista leads que estão pendentes de reengajamento.
    """
    leads = await get_leads_to_reengage(db, tenant)
    
    return {
        "count": len(leads),
        "leads": [
            {
                "id": lead.id,
                "name": lead.name,
                "phone": lead.phone,
                "qualification": lead.qualification,
                "last_activity_at": lead.last_activity_at,
                "reengagement_attempts": lead.reengagement_attempts,
                "reengagement_status": lead.reengagement_status,
            }
            for lead in leads
        ],
    }


@router.post("/execute")
async def execute_batch_reengagement(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Executa o reengajamento em lote para todos os leads pendentes.
    Este endpoint pode ser chamado por um cron job.
    """
    result = await process_reengagement_batch(db, tenant)
    
    return {
        "success": True,
        **result,
    }


@router.post("/manual")
async def manual_reengage_lead(
    payload: ManualReengageRequest,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Reengage manualmente um lead específico.
    """
    # Busca o lead
    result = await db.execute(
        select(Lead)
        .where(Lead.id == payload.lead_id)
        .where(Lead.tenant_id == tenant.id)
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    
    # Verifica se pode reengajar
    settings = tenant.settings or {}
    config = {**DEFAULT_REENGAGEMENT_CONFIG, **settings.get("reengagement", {})}
    
    if lead.reengagement_attempts >= config["max_attempts"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Lead já atingiu o máximo de {config['max_attempts']} tentativas"
        )
    
    # Executa
    result = await execute_reengagement(db, lead, tenant)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Erro ao reengajar"))
    
    return {
        "success": True,
        "message": result["message"],
        "attempt": result["attempt"],
        "status": result["status"],
    }


@router.get("/stats")
async def get_reengagement_stats(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna estatísticas de reengajamento.
    """
    from sqlalchemy import func
    
    # Total de leads por status de reengajamento
    result = await db.execute(
        select(
            Lead.reengagement_status,
            func.count(Lead.id)
        )
        .where(Lead.tenant_id == tenant.id)
        .group_by(Lead.reengagement_status)
    )
    status_counts = dict(result.all())
    
    # Total de tentativas
    result = await db.execute(
        select(func.sum(Lead.reengagement_attempts))
        .where(Lead.tenant_id == tenant.id)
    )
    total_attempts = result.scalar() or 0
    
    # Leads recuperados (responderam após reengajamento)
    recovered = status_counts.get("responded", 0)
    
    # Taxa de sucesso
    total_sent = status_counts.get("sent", 0) + status_counts.get("responded", 0) + status_counts.get("given_up", 0)
    success_rate = round((recovered / total_sent * 100), 1) if total_sent > 0 else 0
    
    return {
        "total_attempts": total_attempts,
        "recovered_leads": recovered,
        "success_rate": success_rate,
        "by_status": {
            "none": status_counts.get("none", 0) + status_counts.get(None, 0),
            "sent": status_counts.get("sent", 0),
            "responded": status_counts.get("responded", 0),
            "given_up": status_counts.get("given_up", 0),
            "failed": status_counts.get("failed", 0),
        },
        "pending": len(await get_leads_to_reengage(db, tenant)),
    }


@router.get("/preview-message")
async def preview_reengagement_message(
    attempt: int = 1,
    lead_name: Optional[str] = None,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """
    Preview da mensagem de reengajamento.
    """
    settings = tenant.settings or {}
    niche = settings.get("niche", "services")
    config = settings.get("reengagement", {})
    
    message = get_reengagement_message(
        niche=niche,
        attempt=attempt,
        lead_name=lead_name or "João",
        custom_message=config.get("custom_message"),
    )
    
    return {
        "message": message,
        "attempt": attempt,
        "niche": niche,
        "is_custom": bool(config.get("custom_message")),
    }