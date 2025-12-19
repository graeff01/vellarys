"""
SERVIÇO DE NOTIFICAÇÕES
========================
Envia notificações imediatas para gestores sobre eventos importantes.
"""

import logging
from datetime import datetime
from typing import Optional, Dict
import os

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Gerencia notificações para gestores/corretores.
    
    Tipos de notificação:
    - Lead quente detectado
    - Lead respondeu após follow-up
    - Objeção importante detectada
    - Lead inativo há muito tempo
    """
    
    def __init__(self):
        self.dashboard_url = os.getenv("DASHBOARD_URL", "https://velaris.app")
    
    async def notify_hot_lead(
        self,
        lead,
        qualification_data: Dict,
        tenant
    ):
        """
        Notifica gestor quando lead vira QUENTE.
        
        CRÍTICO: Notificação imediata!
        """
        try:
            reasons = qualification_data.get("reasons", [])
            score = qualification_data.get("score", 0)
            
            # Monta mensagem
            message = self._build_hot_lead_message(lead, reasons, score)
            
            # Envia notificações
            await self._send_whatsapp_notification(tenant, message)
            await self._send_push_notification(tenant, lead, "hot_lead")
            await self._send_email_notification(tenant, lead, message)
            
            logger.info(f"🔥 Notificação de lead quente enviada: {lead.id}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao notificar lead quente {lead.id}: {e}")
    
    async def notify_lead_replied_after_follow_up(
        self,
        lead,
        tenant
    ):
        """
        Notifica quando lead responde após follow-up.
        Indica reengajamento!
        """
        try:
            message = f"""
🎉 LEAD RESPONDEU APÓS FOLLOW-UP!

📱 {lead.name}
📞 {lead.phone}

O lead voltou a conversar! Aproveite o momentum.

Ver lead: {self.dashboard_url}/leads/{lead.id}
"""
            
            await self._send_push_notification(tenant, lead, "lead_replied")
            
            logger.info(f"💬 Notificação de resposta enviada: {lead.id}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao notificar resposta {lead.id}: {e}")
    
    async def notify_important_objection(
        self,
        lead,
        objection: str,
        tenant
    ):
        """
        Notifica quando lead levanta objeção importante.
        Ex: "Muito caro", "Não tenho orçamento"
        """
        try:
            message = f"""
⚠️ OBJEÇÃO IMPORTANTE DETECTADA

📱 {lead.name}
💬 "{objection}"

Lead demonstrou preocupação. Intervenção do corretor pode ajudar.

Ver conversa: {self.dashboard_url}/leads/{lead.id}
"""
            
            await self._send_push_notification(tenant, lead, "objection")
            
            logger.info(f"⚠️ Notificação de objeção enviada: {lead.id}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao notificar objeção {lead.id}: {e}")
    
    def _build_hot_lead_message(self, lead, reasons: list, score: int) -> str:
        """Constrói mensagem de lead quente."""
        
        reasons_text = "\n".join([f"✅ {r}" for r in reasons[:3]])
        
        message = f"""
🔥🔥🔥 LEAD QUENTE DETECTADO! 🔥🔥🔥

📱 Nome: {lead.name}
📞 Telefone: {lead.phone}
🎯 Score: {score} pontos

POR QUE É QUENTE:
{reasons_text}

⏰ AÇÃO URGENTE: Ligar IMEDIATAMENTE!

Ver detalhes: {self.dashboard_url}/leads/{lead.id}
"""
        
        return message
    
    async def _send_whatsapp_notification(self, tenant, message: str):
        """Envia notificação via WhatsApp para gestor."""
        
        # Busca telefone do gestor/owner
        owner_phone = self._get_owner_phone(tenant)
        
        if not owner_phone:
            logger.warning(f"Owner phone não configurado para tenant {tenant.id}")
            return
        
        try:
            from src.infrastructure.whatsapp.whatsapp_service import WhatsAppService
            
            whatsapp = WhatsAppService()
            await whatsapp.send_message(
                phone=owner_phone,
                message=message,
                tenant_id=tenant.id
            )
            
            logger.info(f"✅ WhatsApp enviado para gestor {owner_phone}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao enviar WhatsApp para gestor: {e}")
    
    async def _send_push_notification(
        self,
        tenant,
        lead,
        notification_type: str
    ):
        """Envia push notification para dashboard."""
        
        try:
            # Implementar quando tiver sistema de push
            # Por enquanto, apenas log
            
            titles = {
                "hot_lead": "🔥 Lead Quente!",
                "lead_replied": "💬 Lead Respondeu",
                "objection": "⚠️ Objeção Detectada"
            }
            
            bodies = {
                "hot_lead": f"{lead.name} está pronto para comprar!",
                "lead_replied": f"{lead.name} voltou a conversar",
                "objection": f"{lead.name} levantou uma preocupação"
            }
            
            title = titles.get(notification_type, "Notificação")
            body = bodies.get(notification_type, "Nova atividade")
            
            logger.info(f"📲 Push notification: {title} - {body}")
            
            # TODO: Implementar push real quando tiver FCM/OneSignal
            # await push_service.send(
            #     user_id=tenant.owner_id,
            #     title=title,
            #     body=body,
            #     data={"lead_id": lead.id, "type": notification_type}
            # )
            
        except Exception as e:
            logger.error(f"❌ Erro ao enviar push notification: {e}")
    
    async def _send_email_notification(
        self,
        tenant,
        lead,
        message: str
    ):
        """Envia email para gestor (opcional)."""
        
        try:
            owner_email = self._get_owner_email(tenant)
            
            if not owner_email:
                return
            
            # TODO: Implementar quando tiver serviço de email
            logger.info(f"📧 Email notification para {owner_email}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao enviar email: {e}")
    
    def _get_owner_phone(self, tenant) -> Optional[str]:
        """Busca telefone do owner/gestor."""
        
        # Tenta buscar de várias formas
        if hasattr(tenant, 'owner') and hasattr(tenant.owner, 'phone'):
            return tenant.owner.phone
        
        if hasattr(tenant, 'notification_phone'):
            return tenant.notification_phone
        
        # Fallback: busca do primeiro user gestor
        try:
            from src.domain.entities import User
            from src.infrastructure.database import async_session
            from sqlalchemy import select
            
            async def get_phone():
                async with async_session() as session:
                    result = await session.execute(
                        select(User).where(
                            User.tenant_id == tenant.id,
                            User.role == "gestor"
                        ).limit(1)
                    )
                    user = result.scalar_one_or_none()
                    return user.phone if user else None
            
            import asyncio
            return asyncio.run(get_phone())
            
        except Exception as e:
            logger.error(f"Erro ao buscar owner phone: {e}")
            return None
    
    def _get_owner_email(self, tenant) -> Optional[str]:
        """Busca email do owner/gestor."""
        
        if hasattr(tenant, 'owner') and hasattr(tenant.owner, 'email'):
            return tenant.owner.email
        
        if hasattr(tenant, 'notification_email'):
            return tenant.notification_email
        
        return None


# Instância global
notification_service = NotificationService()


# Helper functions
async def notify_hot_lead(lead, qualification_data, tenant):
    """Helper para notificar lead quente."""
    await notification_service.notify_hot_lead(lead, qualification_data, tenant)


async def notify_lead_replied(lead, tenant):
    """Helper para notificar resposta."""
    await notification_service.notify_lead_replied_after_follow_up(lead, tenant)


async def notify_objection(lead, objection, tenant):
    """Helper para notificar objeção."""
    await notification_service.notify_important_objection(lead, objection, tenant)