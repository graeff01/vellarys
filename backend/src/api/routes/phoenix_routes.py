"""
PHOENIX ENGINE API ROUTES
=========================

Endpoints para o sistema de reativação inteligente de leads.

Funcionalidades:
- Dashboard com métricas de reativação
- Lista de leads inativos
- Upload de CSV para reativação em massa
- Aprovação/rejeição de reativações pelo gestor
- Reativação manual de leads específicos

AUTOR: Vellarys AI
DATA: 2026-01-30
"""

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Body
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List, Optional
from pydantic import BaseModel

from src.infrastructure.database import get_db
from src.domain.entities import Lead, User, Tenant
from src.api.dependencies import get_current_user
from src.infrastructure.jobs.phoenix_engine_service import phoenix_engine_service


router = APIRouter(prefix="/api/v1/phoenix", tags=["Phoenix Engine"])


# =============================================================================
# SCHEMAS
# =============================================================================

class PhoenixMetrics(BaseModel):
    """Métricas do Phoenix Engine."""
    total_reactivated: int
    pending_approval: int
    response_rate: float
    total_potential_commission: float
    contacted_count: int


class PhoenixLeadItem(BaseModel):
    """Lead no Phoenix Engine."""
    id: int
    name: Optional[str]
    phone: Optional[str]
    phoenix_status: Optional[str]
    phoenix_attempts: int
    phoenix_interest_score: int
    phoenix_potential_commission: Optional[float]
    phoenix_ai_analysis: Optional[str]
    last_phoenix_at: Optional[str]
    last_activity_at: Optional[str]
    days_inactive: int
    original_seller_name: Optional[str]


class ApprovalRequest(BaseModel):
    """Request de aprovação."""
    approved: bool
    notify_seller: bool = True


class CSVUploadResponse(BaseModel):
    """Response do upload de CSV."""
    success: bool
    processed: int
    added: int
    errors: List[str]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/metrics", response_model=PhoenixMetrics)
async def get_phoenix_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna métricas do Phoenix Engine.

    Disponível para: Admin, Manager
    """
    # Verifica permissão
    if current_user.role not in ["admin", "manager", "super_admin"]:
        raise HTTPException(status_code=403, detail="Sem permissão para acessar Phoenix Engine")

    metrics = await phoenix_engine_service.get_dashboard_metrics(current_user.tenant_id)

    return PhoenixMetrics(**metrics)


@router.get("/leads", response_model=List[PhoenixLeadItem])
async def get_phoenix_leads(
    status: Optional[str] = None,  # pending, reactivated, approved, rejected
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista leads no Phoenix Engine.

    Filtros:
    - status: Filtra por phoenix_status

    Disponível para: Admin, Manager
    """
    # Verifica permissão
    if current_user.role not in ["admin", "manager", "super_admin"]:
        raise HTTPException(status_code=403, detail="Sem permissão")

    # Query base
    query = (
        select(Lead)
        .options(selectinload(Lead.assigned_seller))
        .where(
            and_(
                Lead.tenant_id == current_user.tenant_id,
                Lead.phoenix_attempts > 0,  # Já foi contactado pelo Phoenix
            )
        )
    )

    # Filtro por status
    if status:
        query = query.where(Lead.phoenix_status == status)

    # Ordena por interest_score (mais interessados primeiro)
    query = query.order_by(Lead.phoenix_interest_score.desc())

    result = await db.execute(query)
    leads = result.scalars().all()

    # Formata response
    from datetime import datetime

    items = []
    for lead in leads:
        # Calcula dias de inatividade
        days_inactive = 0
        if lead.last_activity_at:
            delta = datetime.utcnow() - lead.last_activity_at
            days_inactive = delta.days

        # Nome do vendedor original
        original_seller_name = None
        if lead.assigned_seller:
            original_seller_name = lead.assigned_seller.name

        items.append(PhoenixLeadItem(
            id=lead.id,
            name=lead.name,
            phone=lead.phone,
            phoenix_status=lead.phoenix_status,
            phoenix_attempts=lead.phoenix_attempts or 0,
            phoenix_interest_score=lead.phoenix_interest_score or 0,
            phoenix_potential_commission=lead.phoenix_potential_commission,
            phoenix_ai_analysis=lead.phoenix_ai_analysis,
            last_phoenix_at=lead.last_phoenix_at.isoformat() if lead.last_phoenix_at else None,
            last_activity_at=lead.last_activity_at.isoformat() if lead.last_activity_at else None,
            days_inactive=days_inactive,
            original_seller_name=original_seller_name,
        ))

    return items


@router.post("/csv-upload", response_model=CSVUploadResponse)
async def upload_phoenix_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload de CSV com lista de leads para reativar.

    Formato CSV esperado:
    ```
    phone,name,note
    5551999999999,João Silva,Lead interessado em 2Q
    5551988888888,Maria Santos,Queria casa em Canoas
    ```

    Disponível para: Admin, Manager
    """
    # Verifica permissão
    if current_user.role not in ["admin", "manager", "super_admin"]:
        raise HTTPException(status_code=403, detail="Sem permissão")

    # Valida tipo de arquivo
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Arquivo deve ser CSV")

    try:
        # Lê conteúdo
        content = await file.read()
        csv_text = content.decode('utf-8')

        # Processa CSV
        result = await phoenix_engine_service.process_csv_upload(
            csv_content=csv_text,
            tenant_id=current_user.tenant_id,
        )

        return CSVUploadResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar CSV: {str(e)}")


@router.post("/approve/{lead_id}")
async def approve_phoenix_reactivation(
    lead_id: int,
    request: ApprovalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Aprova ou rejeita a reativação de um lead.

    Se aprovado, o vendedor original será notificado (se notify_seller=true).

    Disponível para: Admin, Manager
    """
    # Verifica permissão
    if current_user.role not in ["admin", "manager", "super_admin"]:
        raise HTTPException(status_code=403, detail="Sem permissão")

    # Verifica se lead existe e pertence ao tenant
    result = await db.execute(
        select(Lead).where(
            and_(
                Lead.id == lead_id,
                Lead.tenant_id == current_user.tenant_id,
            )
        )
    )
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    # Processa aprovação
    result = await phoenix_engine_service.approve_reactivation(
        lead_id=lead_id,
        approved=request.approved,
        notify_seller=request.notify_seller,
    )

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])

    return {
        "success": True,
        "message": f"Lead {'aprovado' if request.approved else 'rejeitado'} com sucesso",
        "status": result["status"],
    }


@router.post("/manual/{lead_id}")
async def manual_phoenix_reactivation(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Força reativação manual de um lead específico.

    Útil quando o gestor quer reativar um lead que não está no ciclo automático.

    Disponível para: Admin, Manager
    """
    # Verifica permissão
    if current_user.role not in ["admin", "manager", "super_admin"]:
        raise HTTPException(status_code=403, detail="Sem permissão")

    # Verifica se lead existe
    result = await db.execute(
        select(Lead)
        .options(selectinload(Lead.assigned_seller))
        .where(
            and_(
                Lead.id == lead_id,
                Lead.tenant_id == current_user.tenant_id,
            )
        )
    )
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    if not lead.phone:
        raise HTTPException(status_code=400, detail="Lead sem telefone")

    # Reseta Phoenix status para forçar nova tentativa
    lead.phoenix_status = "none"
    lead.phoenix_attempts = 0
    lead.last_phoenix_at = None

    await db.commit()

    return {
        "success": True,
        "message": "Lead adicionado à fila de reativação Phoenix",
    }


@router.get("/inactive-count")
async def get_inactive_leads_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna contagem de leads inativos elegíveis para Phoenix.

    Útil para mostrar badge/contador no menu.
    """
    from datetime import datetime, timedelta

    # Busca configuração do tenant
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        return {"count": 0}

    # Obtém configuração Phoenix
    config = phoenix_engine_service._get_phoenix_config(tenant)

    if not config.get("enabled", False):
        return {"count": 0}

    # Calcula threshold de inatividade
    now = datetime.utcnow()
    inactivity_threshold = now - timedelta(days=config["inactivity_days"])

    # Conta leads inativos elegíveis
    result = await db.execute(
        select(Lead).where(
            and_(
                Lead.tenant_id == current_user.tenant_id,
                Lead.phone.isnot(None),
                Lead.phone != "",
                or_(
                    Lead.last_activity_at.is_(None),
                    Lead.last_activity_at < inactivity_threshold,
                ),
                Lead.status != "converted",
                Lead.status != "lost",
                or_(
                    Lead.phoenix_attempts.is_(None),
                    Lead.phoenix_attempts < config["max_attempts"],
                ),
                or_(
                    Lead.phoenix_status.is_(None),
                    Lead.phoenix_status == "none",
                    Lead.phoenix_status == "pending",
                ),
                Lead.archived_at.is_(None),
            )
        )
    )
    leads = result.scalars().all()

    return {
        "count": len(leads),
        "config_enabled": config.get("enabled", False),
    }
