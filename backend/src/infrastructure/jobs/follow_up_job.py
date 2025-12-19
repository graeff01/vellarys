"""
JOB DE FOLLOW-UP AUTOMÁTICO
============================
Envia mensagens automáticas para leads que pararam de responder.
"""

import asyncio
import random
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import async_session
from src.domain.entities import Lead, Message
from src.infrastructure.whatsapp.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)


class FollowUpService:
    """Gerencia follow-ups automáticos."""
    
    def __init__(self):
        self.whatsapp = WhatsAppService()
        
        # Mensagens de follow-up (sorteia aleatoriamente)
        self.follow_up_messages = [
            "Oi! Ficou com alguma dúvida? Estou por aqui! 😊",
            "Opa! Se precisar de mais informações, é só chamar! 👋",
            "Qualquer dúvida que tiver, pode perguntar!",
            "Oi! Tudo bem por aí? Se precisar de algo, me chama! 😊",
            "Olá! Ficou com alguma pergunta? Estou aqui pra ajudar!",
        ]
        
        # Configurações
        self.config = {
            "first_follow_up_hours": 2,    # Primeiro follow-up após 2h
            "second_follow_up_hours": 24,   # Segundo após 24h
            "max_follow_ups": 2,            # Máximo de 2 follow-ups
        }
    
    async def check_and_send_follow_ups(self):
        """
        Verifica leads que precisam de follow-up e envia mensagens.
        
        RODA: A cada hora (configurar no cron/scheduler)
        """
        try:
            async with async_session() as session:
                logger.info("🔍 Verificando leads para follow-up...")
                
                # Busca leads elegíveis para follow-up
                leads_to_follow_up = await self._get_leads_needing_follow_up(session)
                
                logger.info(f"📊 Encontrados {len(leads_to_follow_up)} leads para follow-up")
                
                for lead in leads_to_follow_up:
                    await self._send_follow_up(session, lead)
                
                await session.commit()
                
                logger.info(f"✅ Follow-ups processados: {len(leads_to_follow_up)}")
                
        except Exception as e:
            logger.error(f"❌ Erro no job de follow-up: {e}", exc_info=True)
    
    async def _get_leads_needing_follow_up(self, session: AsyncSession):
        """Busca leads que precisam de follow-up."""
        
        now = datetime.utcnow()
        first_follow_up_time = now - timedelta(hours=self.config["first_follow_up_hours"])
        second_follow_up_time = now - timedelta(hours=self.config["second_follow_up_hours"])
        
        # Query para leads elegíveis
        query = (
            select(Lead)
            .where(
                and_(
                    # Status em conversação
                    Lead.status.in_(["new", "in_conversation"]),
                    
                    # Última mensagem foi NOSSA (IA respondeu)
                    # E cliente não respondeu ainda
                    Lead.last_message_role == "assistant",
                    
                    # Follow-ups enviados < máximo
                    Lead.follow_up_count < self.config["max_follow_ups"],
                    
                    # Última mensagem há mais de X horas
                    Lead.last_message_at < first_follow_up_time,
                )
            )
        )
        
        result = await session.execute(query)
        leads = result.scalars().all()
        
        # Filtra leads que já receberam follow-up recentemente
        filtered_leads = []
        for lead in leads:
            # Se já enviou follow-up, verifica se já passou tempo suficiente
            if lead.last_follow_up_at:
                time_since_last = now - lead.last_follow_up_at
                required_wait = timedelta(hours=self.config["second_follow_up_hours"])
                
                if time_since_last < required_wait:
                    continue  # Ainda não chegou hora do próximo
            
            filtered_leads.append(lead)
        
        return filtered_leads
    
    async def _send_follow_up(self, session: AsyncSession, lead):
        """Envia mensagem de follow-up para um lead."""
        
        try:
            # Escolhe mensagem aleatória
            message_text = random.choice(self.follow_up_messages)
            
            # Envia via WhatsApp
            success = await self.whatsapp.send_message(
                phone=lead.phone,
                message=message_text,
                tenant_id=lead.tenant_id
            )
            
            if success:
                # Salva mensagem no histórico
                message = Message(
                    lead_id=lead.id,
                    role="assistant",
                    content=message_text,
                    message_type="follow_up",
                    created_at=datetime.utcnow()
                )
                session.add(message)
                
                # Atualiza lead
                lead.follow_up_count = (lead.follow_up_count or 0) + 1
                lead.last_follow_up_at = datetime.utcnow()
                lead.last_message_at = datetime.utcnow()
                lead.last_message_role = "assistant"
                
                logger.info(f"✅ Follow-up enviado para lead {lead.id} ({lead.name})")
            else:
                logger.warning(f"⚠️ Falha ao enviar follow-up para lead {lead.id}")
                
        except Exception as e:
            logger.error(f"❌ Erro ao enviar follow-up para lead {lead.id}: {e}")
    
    async def manual_follow_up(self, lead_id: int, custom_message: str = None):
        """
        Envia follow-up manual para um lead específico.
        
        Útil para gestor enviar follow-up customizado pelo painel.
        """
        async with async_session() as session:
            result = await session.execute(
                select(Lead).where(Lead.id == lead_id)
            )
            lead = result.scalar_one_or_none()
            
            if not lead:
                raise ValueError(f"Lead {lead_id} não encontrado")
            
            message_text = custom_message or random.choice(self.follow_up_messages)
            
            success = await self.whatsapp.send_message(
                phone=lead.phone,
                message=message_text,
                tenant_id=lead.tenant_id
            )
            
            if success:
                message = Message(
                    lead_id=lead.id,
                    role="assistant",
                    content=message_text,
                    message_type="follow_up_manual",
                    created_at=datetime.utcnow()
                )
                session.add(message)
                
                lead.last_message_at = datetime.utcnow()
                lead.last_message_role = "assistant"
                
                await session.commit()
                
                logger.info(f"✅ Follow-up manual enviado para lead {lead_id}")
                return True
            
            return False


# Instância global
follow_up_service = FollowUpService()


# Função para scheduler
async def run_follow_up_job():
    """Função que o scheduler vai chamar."""
    await follow_up_service.check_and_send_follow_ups()