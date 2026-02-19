"""
PUSH NOTIFICATION SERVICE
=========================

Serviço para enviar notificações push para navegadores/dispositivos.

Usa a biblioteca pywebpush para enviar via protocolo Web Push.

Requer:
- pip install pywebpush

Variáveis de ambiente:
- VAPID_PUBLIC_KEY: Chave pública VAPID
- VAPID_PRIVATE_KEY: Chave privada VAPID  
- VAPID_SUBJECT: Email de contato (mailto:email@exemplo.com)
"""

import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from sqlalchemy import select, update, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.domain.entities import User, Tenant

logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# CONFIGURAÇÃO VAPID
# =============================================================================

@dataclass
class VAPIDConfig:
    """Configuração VAPID para Web Push."""
    public_key: str
    private_key: str
    subject: str  # mailto:email@exemplo.com
    
    @property
    def is_configured(self) -> bool:
        return bool(self.public_key and self.private_key and self.subject)


def get_vapid_config() -> VAPIDConfig:
    """Retorna configuração VAPID das variáveis de ambiente."""
    return VAPIDConfig(
        public_key=getattr(settings, 'vapid_public_key', '') or '',
        private_key=getattr(settings, 'vapid_private_key', '') or '',
        subject=getattr(settings, 'vapid_subject', '') or 'mailto:contato@vellarys.app',
    )


# =============================================================================
# TIPOS DE NOTIFICAÇÃO
# =============================================================================

@dataclass
class PushNotificationPayload:
    """Payload da notificação push."""
    title: str
    body: str
    icon: str = "/icons/icon-192x192.png"
    badge: str = "/icons/icon-72x72.png"
    tag: str = "vellarys-notification"
    url: Optional[str] = None  # URL para abrir ao clicar
    data: Optional[Dict[str, Any]] = None
    require_interaction: bool = False
    renotify: bool = True
    vibrate: List[int] = None
    
    def __post_init__(self):
        if self.vibrate is None:
            self.vibrate = [200, 100, 200]
    
    def to_dict(self) -> dict:
        result = {
            "title": self.title,
            "body": self.body,
            "icon": self.icon,
            "badge": self.badge,
            "tag": self.tag,
            "requireInteraction": self.require_interaction,
            "renotify": self.renotify,
            "vibrate": self.vibrate,
        }
        
        if self.url:
            result["data"] = {"url": self.url, **(self.data or {})}
        elif self.data:
            result["data"] = self.data
            
        return result
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


# =============================================================================
# FUNÇÕES DE ENVIO
# =============================================================================

async def send_push_notification(
    endpoint: str,
    keys: dict,
    payload: PushNotificationPayload,
) -> Dict[str, Any]:
    """
    Envia uma notificação push para uma subscription específica.
    
    Args:
        endpoint: URL do endpoint da subscription
        keys: Dict com 'p256dh' e 'auth'
        payload: Dados da notificação
    
    Returns:
        {"success": True/False, "error": "..."}
    """
    vapid_config = get_vapid_config()
    
    if not vapid_config.is_configured:
        logger.warning("VAPID não configurado - Push notifications desabilitadas")
        return {"success": False, "error": "VAPID não configurado"}
    
    try:
        # Import aqui para não quebrar se pywebpush não estiver instalado
        from pywebpush import webpush, WebPushException
        
        subscription_info = {
            "endpoint": endpoint,
            "keys": keys,
        }
        
        vapid_claims = {
            "sub": vapid_config.subject,
        }
        
        response = webpush(
            subscription_info=subscription_info,
            data=payload.to_json(),
            vapid_private_key=vapid_config.private_key,
            vapid_claims=vapid_claims,
        )
        
        logger.info(f"✅ Push enviado para {endpoint[:50]}...")
        return {"success": True, "status_code": response.status_code}
        
    except ImportError:
        logger.error("pywebpush não instalado. Execute: pip install pywebpush")
        return {"success": False, "error": "pywebpush não instalado"}
        
    except Exception as e:
        error_msg = str(e)
        
        # Verifica se é erro de subscription expirada/inválida
        # 410 = Gone (expirada), 404 = Not Found, 403 = VAPID mismatch
        if "410" in error_msg or "404" in error_msg or "403" in error_msg:
            if "403" in error_msg:
                logger.warning(f"🔑 VAPID mismatch - subscription será removida: {endpoint[:50]}...")
            else:
                logger.warning(f"Subscription inválida/expirada: {endpoint[:50]}...")
            return {"success": False, "error": "subscription_expired", "should_remove": True}

        logger.error(f"❌ Erro ao enviar push: {error_msg}")
        return {"success": False, "error": error_msg}


async def send_push_to_user(
    db: AsyncSession,
    user_id: int,
    payload: PushNotificationPayload,
) -> Dict[str, Any]:
    """
    Envia notificação push para todas as subscriptions de um usuário.
    
    Args:
        db: Sessão do banco
        user_id: ID do usuário
        payload: Dados da notificação
    
    Returns:
        {"sent": int, "failed": int, "errors": [...]}
    """
    from src.domain.entities.push_subscription import PushSubscription
    
    # Busca todas as subscriptions ativas do usuário
    result = await db.execute(
        select(PushSubscription)
        .where(PushSubscription.user_id == user_id)
        .where(PushSubscription.active == True)
    )
    subscriptions = result.scalars().all()
    
    if not subscriptions:
        logger.debug(f"Usuário {user_id} não tem subscriptions ativas")
        return {"sent": 0, "failed": 0, "errors": []}
    
    sent = 0
    failed = 0
    errors = []
    subscriptions_to_remove = []
    
    for sub in subscriptions:
        result = await send_push_notification(
            endpoint=sub.endpoint,
            keys=sub.keys,
            payload=payload,
        )
        
        if result.get("success"):
            sent += 1
            # Atualiza last_used_at
            sub.last_used_at = datetime.now(timezone.utc)
            sub.failure_count = 0
        else:
            failed += 1
            errors.append(result.get("error"))
            
            # Se subscription expirou, marca para remover
            if result.get("should_remove"):
                subscriptions_to_remove.append(sub.id)
            else:
                # Incrementa contador de falhas
                sub.failure_count += 1
                
                # Desativa após 5 falhas consecutivas
                if sub.failure_count >= 5:
                    sub.active = False
                    logger.warning(f"Subscription {sub.id} desativada por múltiplas falhas")
    
    # Remove subscriptions expiradas
    if subscriptions_to_remove:
        await db.execute(
            update(PushSubscription)
            .where(PushSubscription.id.in_(subscriptions_to_remove))
            .values(active=False)
        )
    
    await db.commit()
    
    return {"sent": sent, "failed": failed, "errors": errors}


async def send_push_to_tenant(
    db: AsyncSession,
    tenant_id: int,
    payload: PushNotificationPayload,
    user_roles: List[str] = None,
) -> Dict[str, Any]:
    """
    Envia notificação push para todos os usuários de um tenant.
    
    Args:
        db: Sessão do banco
        tenant_id: ID do tenant
        payload: Dados da notificação
        user_roles: Lista de roles para filtrar (ex: ['admin', 'manager'])
    
    Returns:
        {"total_users": int, "sent": int, "failed": int}
    """
    from src.domain.entities.push_subscription import PushSubscription
    
    # Busca todas as subscriptions ativas do tenant
    query = (
        select(PushSubscription)
        .where(PushSubscription.tenant_id == tenant_id)
        .where(PushSubscription.active == True)
    )
    
    # Se especificou roles, filtra
    if user_roles:
        query = query.join(User).where(User.role.in_(user_roles))
    
    result = await db.execute(query)
    subscriptions = result.scalars().all()
    
    if not subscriptions:
        return {"total_users": 0, "sent": 0, "failed": 0}
    
    # Agrupa por usuário para contar
    user_ids = set(sub.user_id for sub in subscriptions)
    
    sent = 0
    failed = 0
    
    for sub in subscriptions:
        result = await send_push_notification(
            endpoint=sub.endpoint,
            keys=sub.keys,
            payload=payload,
        )
        
        if result.get("success"):
            sent += 1
            sub.last_used_at = datetime.now(timezone.utc)
            sub.failure_count = 0
        else:
            failed += 1

            if result.get("should_remove"):
                sub.active = False
                logger.info(f"🗑️ Subscription {sub.id} desativada (expirada/VAPID mismatch)")
            else:
                sub.failure_count += 1
                if sub.failure_count >= 5:
                    sub.active = False
                    logger.warning(f"Subscription {sub.id} desativada por múltiplas falhas")

    await db.commit()
    
    return {
        "total_users": len(user_ids),
        "sent": sent,
        "failed": failed,
    }


# =============================================================================
# FUNÇÕES DE CONVENIÊNCIA
# =============================================================================

async def notify_lead_hot(
    db: AsyncSession,
    tenant_id: int,
    lead_name: str,
    lead_id: int,
) -> Dict[str, Any]:
    """Envia push notification quando lead fica quente."""
    payload = PushNotificationPayload(
        title="🔥 Lead Quente!",
        body=f"{lead_name} está muito interessado!",
        tag=f"lead-hot-{lead_id}",
        url=f"/dashboard/leads?lead={lead_id}",
        require_interaction=True,
        data={"lead_id": lead_id, "type": "lead_hot"},
    )
    
    return await send_push_to_tenant(db, tenant_id, payload)


async def notify_lead_assigned(
    db: AsyncSession,
    user_id: int,
    lead_name: str,
    lead_id: int,
) -> Dict[str, Any]:
    """Envia push notification quando lead é atribuído ao vendedor."""
    payload = PushNotificationPayload(
        title="👋 Novo Lead!",
        body=f"Você recebeu o lead: {lead_name}",
        tag=f"lead-assigned-{lead_id}",
        url=f"/dashboard/leads?lead={lead_id}",
        require_interaction=True,
        data={"lead_id": lead_id, "type": "lead_assigned"},
    )
    
    return await send_push_to_user(db, user_id, payload)


async def notify_new_message(
    db: AsyncSession,
    tenant_id: int,
    lead_name: str,
    lead_id: int,
    message_preview: str,
) -> Dict[str, Any]:
    """Envia push notification quando chega nova mensagem."""
    # Limita preview
    if len(message_preview) > 100:
        message_preview = message_preview[:97] + "..."
    
    payload = PushNotificationPayload(
        title=f"💬 {lead_name}",
        body=message_preview,
        tag=f"message-{lead_id}",
        url=f"/dashboard/leads?lead={lead_id}",
        data={"lead_id": lead_id, "type": "new_message"},
    )
    
    return await send_push_to_tenant(db, tenant_id, payload)


# =============================================================================
# LIMPEZA DE SUBSCRIPTIONS INVÁLIDAS
# =============================================================================

async def cleanup_invalid_subscriptions(db: AsyncSession) -> Dict[str, int]:
    """
    Remove subscriptions inativas ou com muitas falhas.
    Útil para limpar subscriptions com VAPID keys antigas.
    """
    from src.domain.entities.push_subscription import PushSubscription

    # Conta antes
    result = await db.execute(
        select(func.count(PushSubscription.id))
        .where(
            (PushSubscription.active == False) |
            (PushSubscription.failure_count >= 3)
        )
    )
    invalid_count = result.scalar() or 0

    if invalid_count == 0:
        return {"removed": 0}

    # Remove inativas e com muitas falhas
    await db.execute(
        delete(PushSubscription)
        .where(
            (PushSubscription.active == False) |
            (PushSubscription.failure_count >= 3)
        )
    )
    await db.commit()

    logger.info(f"🧹 Limpeza push: {invalid_count} subscriptions inválidas removidas")
    return {"removed": invalid_count}


# Import necessário
from datetime import datetime, timezone