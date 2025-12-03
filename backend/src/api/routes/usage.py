"""
USAGE - Informações de uso do tenant
=====================================

Endpoints para o gestor ver seu uso e limites.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.domain.entities import User
from src.api.dependencies import get_current_user
from src.application.services.limits_service import (
    get_usage_summary,
    can_use_feature,
)

router = APIRouter(prefix="/usage", tags=["Uso e Limites"])


@router.get("", include_in_schema=False)
async def get_my_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna o resumo de uso do tenant atual.
    
    Inclui:
    - Limites do plano
    - Uso atual
    - Porcentagem usada
    - Status do trial (se aplicável)
    - Features disponíveis
    """
    
    summary = await get_usage_summary(db, current_user.tenant_id)
    
    if "error" in summary:
        raise HTTPException(status_code=404, detail=summary["error"])
    
    return summary


@router.get("/can-use/{feature}")
async def check_feature_access(
    feature: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Verifica se o tenant pode usar uma feature específica.
    
    Features disponíveis:
    - reengagement
    - advanced_reports
    - api_access
    - priority_support
    - white_label
    - custom_integrations
    """
    
    can_use = await can_use_feature(db, current_user.tenant_id, feature)
    
    return {
        "feature": feature,
        "allowed": can_use,
        "message": "" if can_use else f"Feature '{feature}' não disponível no seu plano"
    }