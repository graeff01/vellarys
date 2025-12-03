"""
ROTAS: NOTIFICAÇÕES
====================

Endpoints para gerenciar notificações do gestor.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from src.infrastructure.database import get_db
from src.domain.entities import Notification, User, Tenant
from src.api.dependencies import get_current_user, get_current_tenant

router = APIRouter(prefix="/notifications", tags=["Notificações"])


@router.get("")
async def list_notifications(
    unread_only: bool = False,
    limit: int = 20,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista notificações do tenant.
    """
    query = select(Notification).where(Notification.tenant_id == tenant.id)
    
    if unread_only:
        query = query.where(Notification.read == False)
    
    query = query.order_by(Notification.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    notifications = result.scalars().all()
    
    return [
        {
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "message": n.message,
            "reference_type": n.reference_type,
            "reference_id": n.reference_id,
            "read": n.read,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifications
    ]


@router.get("/count")
async def count_unread(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna contagem de notificações não lidas.
    """
    result = await db.execute(
        select(func.count(Notification.id))
        .where(Notification.tenant_id == tenant.id)
        .where(Notification.read == False)
    )
    count = result.scalar() or 0
    
    return {"unread_count": count}


@router.patch("/{notification_id}/read")
async def mark_as_read(
    notification_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Marca notificação como lida.
    """
    result = await db.execute(
        select(Notification)
        .where(Notification.id == notification_id)
        .where(Notification.tenant_id == tenant.id)
    )
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    
    notification.read = True
    await db.commit()
    
    return {"success": True}


@router.patch("/read-all")
async def mark_all_as_read(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Marca todas notificações como lidas.
    """
    await db.execute(
        update(Notification)
        .where(Notification.tenant_id == tenant.id)
        .where(Notification.read == False)
        .values(read=True)
    )
    await db.commit()
    
    return {"success": True}