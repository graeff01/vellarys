"""
ROTAS: NOTIFICAÇÕES
====================

Endpoints para gerenciar notificações do gestor.
Inclui Push Notifications (subscribe/unsubscribe).
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel

from src.infrastructure.database import get_db
from src.domain.entities import Notification, User, Tenant
from src.api.dependencies import get_current_user, get_current_tenant
from src.config import get_settings

router = APIRouter(prefix="/notifications", tags=["Notificações"])


@router.get("/vapid-public-key")
async def get_vapid_public_key():
    """Retorna a chave pública VAPID para registro no navegador."""
    settings = get_settings()
    return {"public_key": settings.vapid_public_key}


# =============================================================================
# SCHEMAS
# =============================================================================

class PushSubscriptionKeys(BaseModel):
    """Chaves de autenticação da subscription."""
    p256dh: str
    auth: str


class PushSubscriptionCreate(BaseModel):
    """Dados para criar uma subscription."""
    endpoint: str
    keys: PushSubscriptionKeys
    

class PushSubscriptionResponse(BaseModel):
    """Resposta da subscription."""
    id: int
    endpoint: str
    active: bool
    device_name: Optional[str] = None


# =============================================================================
# NOTIFICAÇÕES DO DASHBOARD
# =============================================================================

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

    return {"count": count, "unread_count": count}


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


# =============================================================================
# PUSH NOTIFICATIONS - SUBSCRIPTION
# =============================================================================

@router.post("/subscribe")
async def subscribe_push(
    data: PushSubscriptionCreate,
    request: Request,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Registra subscription para receber Push Notifications.
    
    O frontend envia os dados da PushSubscription do navegador.
    """
    from src.domain.entities.push_subscription import PushSubscription
    
    # Verifica se já existe subscription com esse endpoint
    result = await db.execute(
        select(PushSubscription).where(PushSubscription.endpoint == data.endpoint)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        # Atualiza subscription existente
        existing.user_id = user.id
        existing.tenant_id = tenant.id
        existing.keys = {"p256dh": data.keys.p256dh, "auth": data.keys.auth}
        existing.active = True
        existing.failure_count = 0
        existing.user_agent = request.headers.get("user-agent", "")[:500]
        
        await db.commit()
        
        return {
            "success": True,
            "message": "Subscription atualizada",
            "subscription_id": existing.id,
        }
    
    # Cria nova subscription
    subscription = PushSubscription(
        user_id=user.id,
        tenant_id=tenant.id,
        endpoint=data.endpoint,
        keys={"p256dh": data.keys.p256dh, "auth": data.keys.auth},
        user_agent=request.headers.get("user-agent", "")[:500],
        active=True,
    )
    
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)
    
    return {
        "success": True,
        "message": "Subscription criada",
        "subscription_id": subscription.id,
    }


@router.post("/unsubscribe")
async def unsubscribe_push(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove todas as subscriptions do usuário atual.
    """
    from src.domain.entities.push_subscription import PushSubscription
    
    await db.execute(
        delete(PushSubscription)
        .where(PushSubscription.user_id == user.id)
        .where(PushSubscription.tenant_id == tenant.id)
    )
    await db.commit()
    
    return {"success": True, "message": "Subscriptions removidas"}


@router.delete("/subscribe/{subscription_id}")
async def delete_subscription(
    subscription_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove uma subscription específica.
    """
    from src.domain.entities.push_subscription import PushSubscription
    
    result = await db.execute(
        select(PushSubscription)
        .where(PushSubscription.id == subscription_id)
        .where(PushSubscription.user_id == user.id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription não encontrada")
    
    await db.delete(subscription)
    await db.commit()
    
    return {"success": True}


@router.get("/subscriptions")
async def list_subscriptions(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista todas as subscriptions do usuário.
    """
    from src.domain.entities.push_subscription import PushSubscription
    
    result = await db.execute(
        select(PushSubscription)
        .where(PushSubscription.user_id == user.id)
        .where(PushSubscription.tenant_id == tenant.id)
        .where(PushSubscription.active == True)
    )
    subscriptions = result.scalars().all()
    
    return [
        {
            "id": s.id,
            "endpoint": s.endpoint[:50] + "..." if len(s.endpoint) > 50 else s.endpoint,
            "active": s.active,
            "device_name": s.device_name,
            "last_used_at": s.last_used_at.isoformat() if s.last_used_at else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in subscriptions
    ]


# =============================================================================
# PUSH NOTIFICATIONS - ENVIO (para testes)
# =============================================================================

@router.post("/test-push")
async def test_push_notification(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Envia uma notificação push de teste para o usuário atual.
    """
    from src.infrastructure.services.push_service import (
        send_push_to_user,
        PushNotificationPayload,
    )
    
    payload = PushNotificationPayload(
        title="🔔 Teste de Notificação",
        body="Se você está vendo isso, as notificações push estão funcionando!",
        tag="test-notification",
        url="/dashboard",
    )
    
    result = await send_push_to_user(db, user.id, payload)
    
    return {
        "success": result.get("sent", 0) > 0,
        "sent": result.get("sent", 0),
        "failed": result.get("failed", 0),
        "errors": result.get("errors", []),
    }