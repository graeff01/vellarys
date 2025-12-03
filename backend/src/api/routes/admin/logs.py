"""
ADMIN: Logs de Auditoria
=========================

Visualização de logs de ações administrativas.
"""

from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.domain.entities import AdminLog, User
from src.api.routes.admin.deps import get_current_superadmin

router = APIRouter(prefix="/admin/logs", tags=["Admin - Logs"])


@router.get("")
async def list_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    action: Optional[str] = None,
    target_type: Optional[str] = None,
    admin_id: Optional[int] = None,
    days: int = Query(30, ge=1, le=365, description="Logs dos últimos N dias"),
    current_user: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Lista logs de auditoria com filtros."""
    
    date_limit = datetime.now() - timedelta(days=days)
    
    query = select(AdminLog).where(AdminLog.created_at >= date_limit)
    count_query = select(func.count(AdminLog.id)).where(AdminLog.created_at >= date_limit)
    
    if action:
        query = query.where(AdminLog.action == action)
        count_query = count_query.where(AdminLog.action == action)
    
    if target_type:
        query = query.where(AdminLog.target_type == target_type)
        count_query = count_query.where(AdminLog.target_type == target_type)
    
    if admin_id:
        query = query.where(AdminLog.admin_id == admin_id)
        count_query = count_query.where(AdminLog.admin_id == admin_id)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    offset = (page - 1) * limit
    query = query.order_by(AdminLog.created_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return {
        "logs": [
            {
                "id": log.id,
                "admin_id": log.admin_id,
                "admin_email": log.admin_email,
                "action": log.action,
                "target_type": log.target_type,
                "target_id": log.target_id,
                "target_name": log.target_name,
                "details": log.details,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@router.get("/actions")
async def list_available_actions(
    current_user: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Lista todas as ações disponíveis para filtro."""
    
    result = await db.execute(
        select(AdminLog.action).distinct()
    )
    actions = [row[0] for row in result.all()]
    
    return {"actions": sorted(actions)}


@router.get("/stats")
async def get_logs_stats(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Estatísticas dos logs."""
    
    date_limit = datetime.now() - timedelta(days=days)
    
    total = await db.execute(
        select(func.count(AdminLog.id)).where(AdminLog.created_at >= date_limit)
    )
    total = total.scalar() or 0
    
    by_action = await db.execute(
        select(AdminLog.action, func.count(AdminLog.id))
        .where(AdminLog.created_at >= date_limit)
        .group_by(AdminLog.action)
    )
    by_action = {row[0]: row[1] for row in by_action.all()}
    
    by_target = await db.execute(
        select(AdminLog.target_type, func.count(AdminLog.id))
        .where(AdminLog.created_at >= date_limit)
        .group_by(AdminLog.target_type)
    )
    by_target = {row[0]: row[1] for row in by_target.all()}
    
    by_admin = await db.execute(
        select(AdminLog.admin_email, func.count(AdminLog.id))
        .where(AdminLog.created_at >= date_limit)
        .group_by(AdminLog.admin_email)
    )
    by_admin = {row[0]: row[1] for row in by_admin.all()}
    
    return {
        "period_days": days,
        "total": total,
        "by_action": by_action,
        "by_target": by_target,
        "by_admin": by_admin,
    }