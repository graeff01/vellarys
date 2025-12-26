"""
SERVIÇO DE FOLLOW-UP AUTOMÁTICO - VERSÃO 2.0
=============================================

Envia mensagens automáticas para leads que pararam de responder.

CARACTERÍSTICAS:
- Multi-tenant (cada cliente tem suas próprias configurações)
- Respeita horário comercial do tenant
- Mensagens personalizadas por tentativa
- Usa campos existentes no model Lead
- Logs detalhados para debug

CAMPOS DO LEAD UTILIZADOS:
- last_activity_at: Última atividade do lead
- reengagement_attempts: Número de follow-ups enviados
- last_reengagement_at: Data do último follow-up
- reengagement_status: Status do reengajamento

ÚLTIMA ATUALIZAÇÃO: 2024-12-26
VERSÃO: 2.0
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infrastructure.database import async_session
from src.domain.entities import Lead, Message, Tenant, Channel
from src.infrastructure.services.whatsapp_service import send_whatsapp_message

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURAÇÕES PADRÃO (fallback se tenant não configurou)
# =============================================================================

DEFAULT_FOLLOW_UP_CONFIG = {
    "enabled": False,
    "inactivity_hours": 24,
    "max_attempts": 3,
    "interval_hours": 24,
    "respect_business_hours": True,
    "messages": {
        "attempt_1": "Oi {nome}! Vi que você se interessou por nossos serviços. Posso te ajudar com mais alguma informação? 😊",
        "attempt_2": "Oi {nome}! Ainda está procurando? Estou aqui se precisar!",
        "attempt_3": "{nome}, vou encerrar nosso atendimento por aqui. Se precisar, é só chamar novamente! 👋",
    },
    "exclude_statuses": ["converted", "lost", "handed_off"],
    "exclude_qualifications": [],
    "allowed_hours": {
        "start": "08:00",
        "end": "20:00",
    },
}


# =============================================================================
# SERVIÇO PRINCIPAL
# =============================================================================

class FollowUpService:
    """
    Gerencia follow-ups automáticos de forma multi-tenant.
    
    Cada tenant tem suas próprias configurações de follow-up,
    definidas nas settings do dashboard.
    """
    
    def __init__(self):
        self.processed_count = 0
        self.sent_count = 0
        self.skipped_count = 0
        self.error_count = 0
    
    # =========================================================================
    # MÉTODO PRINCIPAL - PROCESSA TODOS OS TENANTS
    # =========================================================================
    
    async def process_all_tenants(self):
        """
        Processa follow-ups para todos os tenants ativos.
        
        CHAMADO PELO: Scheduler (a cada hora)
        """
        logger.info("=" * 60)
        logger.info("🔄 INICIANDO JOB DE FOLLOW-UP AUTOMÁTICO")
        logger.info("=" * 60)
        
        self.processed_count = 0
        self.sent_count = 0
        self.skipped_count = 0
        self.error_count = 0
        
        try:
            async with async_session() as session:
                # Busca todos os tenants ativos
                result = await session.execute(
                    select(Tenant).where(Tenant.active == True)
                )
                tenants = result.scalars().all()
                
                logger.info(f"📊 Encontrados {len(tenants)} tenants ativos")
                
                for tenant in tenants:
                    await self._process_tenant(session, tenant)
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"❌ Erro crítico no job de follow-up: {e}", exc_info=True)
        
        # Log final
        logger.info("=" * 60)
        logger.info(f"✅ JOB FINALIZADO")
        logger.info(f"   Processados: {self.processed_count}")
        logger.info(f"   Enviados: {self.sent_count}")
        logger.info(f"   Pulados: {self.skipped_count}")
        logger.info(f"   Erros: {self.error_count}")
        logger.info("=" * 60)
        
        return {
            "processed": self.processed_count,
            "sent": self.sent_count,
            "skipped": self.skipped_count,
            "errors": self.error_count,
        }
    
    # =========================================================================
    # PROCESSA UM TENANT ESPECÍFICO
    # =========================================================================
    
    async def _process_tenant(self, session: AsyncSession, tenant: Tenant):
        """Processa follow-ups de um tenant específico."""
        
        try:
            # Obtém configurações de follow-up do tenant
            config = self._get_follow_up_config(tenant)
            
            # Verifica se follow-up está habilitado
            if not config.get("enabled", False):
                logger.debug(f"⏭️ Tenant {tenant.slug}: Follow-up desabilitado")
                return
            
            logger.info(f"🏢 Processando tenant: {tenant.name} ({tenant.slug})")
            
            # Verifica se está em horário permitido
            if not self._is_allowed_time(tenant, config):
                logger.info(f"⏰ Tenant {tenant.slug}: Fora do horário permitido")
                return
            
            # Busca leads elegíveis para follow-up
            leads = await self._get_eligible_leads(session, tenant, config)
            
            logger.info(f"📋 Tenant {tenant.slug}: {len(leads)} leads elegíveis")
            
            for lead in leads:
                self.processed_count += 1
                await self._process_lead(session, tenant, lead, config)
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar tenant {tenant.slug}: {e}", exc_info=True)
            self.error_count += 1
    
    # =========================================================================
    # BUSCA LEADS ELEGÍVEIS
    # =========================================================================
    
    async def _get_eligible_leads(
        self,
        session: AsyncSession,
        tenant: Tenant,
        config: dict,
    ) -> list[Lead]:
        """
        Busca leads que precisam de follow-up.
        
        CRITÉRIOS:
        1. Pertence ao tenant
        2. Tem telefone
        3. Status não está na lista de exclusão
        4. Última atividade há mais de X horas
        5. Não atingiu máximo de tentativas
        6. Último follow-up foi há mais de Y horas (se houver)
        """
        
        now = datetime.utcnow()
        inactivity_threshold = now - timedelta(hours=config["inactivity_hours"])
        interval_threshold = now - timedelta(hours=config["interval_hours"])
        
        # Status excluídos
        exclude_statuses = config.get("exclude_statuses", [])
        
        # Qualificações excluídas
        exclude_qualifications = config.get("exclude_qualifications", [])
        
        # Query base
        query = (
            select(Lead)
            .options(selectinload(Lead.messages))
            .where(
                and_(
                    # Pertence ao tenant
                    Lead.tenant_id == tenant.id,
                    
                    # Tem telefone
                    Lead.phone.isnot(None),
                    Lead.phone != "",
                    
                    # Última atividade há mais de X horas
                    or_(
                        Lead.last_activity_at.is_(None),
                        Lead.last_activity_at < inactivity_threshold,
                    ),
                    
                    # Não atingiu máximo de tentativas
                    or_(
                        Lead.reengagement_attempts.is_(None),
                        Lead.reengagement_attempts < config["max_attempts"],
                    ),
                    
                    # Último follow-up foi há mais de Y horas
                    or_(
                        Lead.last_reengagement_at.is_(None),
                        Lead.last_reengagement_at < interval_threshold,
                    ),
                    
                    # Status de reengajamento não é "stopped" ou "responded"
                    or_(
                        Lead.reengagement_status.is_(None),
                        Lead.reengagement_status == "none",
                        Lead.reengagement_status == "pending",
                    ),
                )
            )
        )
        
        # Adiciona filtro de status se houver exclusões
        if exclude_statuses:
            query = query.where(
                or_(
                    Lead.status.is_(None),
                    ~Lead.status.in_(exclude_statuses),
                )
            )
        
        # Adiciona filtro de qualificação se houver exclusões
        if exclude_qualifications:
            query = query.where(
                or_(
                    Lead.qualification.is_(None),
                    ~Lead.qualification.in_(exclude_qualifications),
                )
            )
        
        # Limita para não sobrecarregar
        query = query.limit(100)
        
        result = await session.execute(query)
        leads = result.scalars().all()
        
        # Filtro adicional: última mensagem foi da IA (lead não respondeu)
        filtered_leads = []
        for lead in leads:
            if self._last_message_was_assistant(lead):
                filtered_leads.append(lead)
        
        return filtered_leads
    
    def _last_message_was_assistant(self, lead: Lead) -> bool:
        """Verifica se a última mensagem foi da IA (lead não respondeu)."""
        if not lead.messages:
            return False
        
        # Ordena por data (mais recente primeiro)
        sorted_messages = sorted(
            lead.messages,
            key=lambda m: m.created_at or datetime.min,
            reverse=True
        )
        
        if sorted_messages:
            return sorted_messages[0].role == "assistant"
        
        return False
    
    # =========================================================================
    # PROCESSA UM LEAD
    # =========================================================================
    
    async def _process_lead(
        self,
        session: AsyncSession,
        tenant: Tenant,
        lead: Lead,
        config: dict,
    ):
        """Processa follow-up de um lead específico."""
        
        try:
            # Determina qual tentativa é essa
            attempt = (lead.reengagement_attempts or 0) + 1
            
            # Obtém mensagem personalizada
            message = self._get_personalized_message(lead, attempt, config)
            
            if not message:
                logger.warning(f"⚠️ Lead {lead.id}: Sem mensagem para tentativa {attempt}")
                self.skipped_count += 1
                return
            
            # Envia mensagem via WhatsApp
            logger.info(f"📤 Enviando follow-up #{attempt} para lead {lead.id} ({lead.name or 'Sem nome'})")
            
            result = await send_whatsapp_message(
                to=lead.phone,
                message=message,
            )
            
            if result.get("success"):
                # Salva mensagem no histórico
                msg = Message(
                    lead_id=lead.id,
                    role="assistant",
                    content=f"[FOLLOW-UP #{attempt}] {message}",
                    tokens_used=0,
                )
                session.add(msg)
                
                # Atualiza lead
                lead.reengagement_attempts = attempt
                lead.last_reengagement_at = datetime.utcnow()
                lead.reengagement_status = "pending"
                
                # Se foi a última tentativa, marca como "final"
                if attempt >= config["max_attempts"]:
                    lead.reengagement_status = "exhausted"
                
                self.sent_count += 1
                logger.info(f"✅ Follow-up #{attempt} enviado para lead {lead.id}")
                
            else:
                error = result.get("error", "Erro desconhecido")
                logger.error(f"❌ Falha ao enviar follow-up para lead {lead.id}: {error}")
                self.error_count += 1
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar lead {lead.id}: {e}", exc_info=True)
            self.error_count += 1
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    def _get_follow_up_config(self, tenant: Tenant) -> dict:
        """Obtém configurações de follow-up do tenant."""
        settings = tenant.settings or {}
        follow_up = settings.get("follow_up", {})
        
        # Merge com defaults
        config = DEFAULT_FOLLOW_UP_CONFIG.copy()
        config.update(follow_up)
        
        # Garante que messages existe
        if "messages" not in config or not config["messages"]:
            config["messages"] = DEFAULT_FOLLOW_UP_CONFIG["messages"]
        
        return config
    
    def _is_allowed_time(self, tenant: Tenant, config: dict) -> bool:
        """Verifica se está em horário permitido para enviar follow-up."""
        
        settings = tenant.settings or {}
        
        # Se deve respeitar horário comercial
        if config.get("respect_business_hours", True):
            business_hours = settings.get("business_hours", {})
            
            if business_hours.get("enabled", False):
                return self._is_within_business_hours(business_hours)
        
        # Se não respeita horário comercial, usa allowed_hours
        allowed_hours = config.get("allowed_hours", {})
        return self._is_within_allowed_hours(allowed_hours, settings)
    
    def _is_within_business_hours(self, business_hours: dict) -> bool:
        """Verifica se está dentro do horário comercial."""
        
        timezone_str = business_hours.get("timezone", "America/Sao_Paulo")
        
        try:
            tz = ZoneInfo(timezone_str)
        except Exception:
            tz = ZoneInfo("America/Sao_Paulo")
        
        now = datetime.now(tz)
        day_name = now.strftime("%A").lower()
        
        schedule = business_hours.get("schedule", {})
        day_config = schedule.get(day_name, {})
        
        if not day_config.get("enabled", False):
            return False
        
        try:
            open_time = datetime.strptime(day_config.get("open", "08:00"), "%H:%M").time()
            close_time = datetime.strptime(day_config.get("close", "18:00"), "%H:%M").time()
            current_time = now.time()
            
            return open_time <= current_time <= close_time
            
        except Exception as e:
            logger.warning(f"Erro ao verificar horário comercial: {e}")
            return True  # Na dúvida, permite
    
    def _is_within_allowed_hours(self, allowed_hours: dict, settings: dict) -> bool:
        """Verifica se está dentro das horas permitidas."""
        
        business_hours = settings.get("business_hours", {})
        timezone_str = business_hours.get("timezone", "America/Sao_Paulo")
        
        try:
            tz = ZoneInfo(timezone_str)
        except Exception:
            tz = ZoneInfo("America/Sao_Paulo")
        
        now = datetime.now(tz)
        
        try:
            start_time = datetime.strptime(allowed_hours.get("start", "08:00"), "%H:%M").time()
            end_time = datetime.strptime(allowed_hours.get("end", "20:00"), "%H:%M").time()
            current_time = now.time()
            
            return start_time <= current_time <= end_time
            
        except Exception as e:
            logger.warning(f"Erro ao verificar horário permitido: {e}")
            return True
    
    def _get_personalized_message(self, lead: Lead, attempt: int, config: dict) -> str:
        """Gera mensagem personalizada para o lead."""
        
        messages = config.get("messages", {})
        message_key = f"attempt_{attempt}"
        
        # Obtém template da mensagem
        template = messages.get(message_key)
        
        if not template:
            # Fallback para última mensagem se tentativa exceder
            template = messages.get(f"attempt_{config['max_attempts']}")
        
        if not template:
            # Fallback final
            template = "Oi! Posso te ajudar com mais alguma informação?"
        
        # Extrai informações do lead para personalização
        nome = lead.name or "cliente"
        
        # Tenta extrair interesse do custom_data ou da última mensagem
        interesse = self._extract_interesse(lead)
        
        # Substitui placeholders
        message = template.replace("{nome}", nome)
        message = message.replace("{interesse}", interesse)
        
        return message
    
    def _extract_interesse(self, lead: Lead) -> str:
        """Extrai o interesse do lead para personalizar mensagem."""
        
        # Tenta do custom_data
        custom_data = lead.custom_data or {}
        
        if custom_data.get("interesse"):
            return custom_data["interesse"]
        
        if custom_data.get("interest"):
            return custom_data["interest"]
        
        if custom_data.get("property_type"):
            return custom_data["property_type"]
        
        if custom_data.get("servico"):
            return custom_data["servico"]
        
        if custom_data.get("produto"):
            return custom_data["produto"]
        
        # Fallback genérico
        return "nossos serviços"
    
    # =========================================================================
    # MÉTODOS PÚBLICOS PARA USO EXTERNO
    # =========================================================================
    
    async def send_manual_follow_up(
        self,
        lead_id: int,
        custom_message: str = None,
    ) -> dict:
        """
        Envia follow-up manual para um lead específico.
        
        Útil para o gestor enviar follow-up customizado pelo painel.
        """
        
        async with async_session() as session:
            # Busca lead
            result = await session.execute(
                select(Lead)
                .options(selectinload(Lead.tenant))
                .where(Lead.id == lead_id)
            )
            lead = result.scalar_one_or_none()
            
            if not lead:
                return {"success": False, "error": "Lead não encontrado"}
            
            if not lead.phone:
                return {"success": False, "error": "Lead sem telefone"}
            
            # Determina mensagem
            if custom_message:
                message = custom_message
            else:
                config = self._get_follow_up_config(lead.tenant)
                attempt = (lead.reengagement_attempts or 0) + 1
                message = self._get_personalized_message(lead, attempt, config)
            
            # Envia
            result = await send_whatsapp_message(
                to=lead.phone,
                message=message,
            )
            
            if result.get("success"):
                # Salva mensagem
                msg = Message(
                    lead_id=lead.id,
                    role="assistant",
                    content=f"[FOLLOW-UP MANUAL] {message}",
                    tokens_used=0,
                )
                session.add(msg)
                
                # Atualiza lead
                lead.reengagement_attempts = (lead.reengagement_attempts or 0) + 1
                lead.last_reengagement_at = datetime.utcnow()
                lead.last_activity_at = datetime.utcnow()
                
                await session.commit()
                
                return {"success": True, "message": "Follow-up enviado com sucesso"}
            else:
                return {"success": False, "error": result.get("error", "Erro ao enviar")}
    
    async def reset_follow_up_status(self, lead_id: int) -> dict:
        """
        Reseta o status de follow-up de um lead.
        
        Útil quando lead responde e queremos reiniciar o ciclo.
        """
        
        async with async_session() as session:
            result = await session.execute(
                select(Lead).where(Lead.id == lead_id)
            )
            lead = result.scalar_one_or_none()
            
            if not lead:
                return {"success": False, "error": "Lead não encontrado"}
            
            lead.reengagement_attempts = 0
            lead.last_reengagement_at = None
            lead.reengagement_status = "none"
            
            await session.commit()
            
            return {"success": True, "message": "Status de follow-up resetado"}


# =============================================================================
# INSTÂNCIA GLOBAL
# =============================================================================

follow_up_service = FollowUpService()


# =============================================================================
# FUNÇÕES PARA O SCHEDULER
# =============================================================================

async def run_follow_up_job():
    """Função que o scheduler vai chamar a cada hora."""
    return await follow_up_service.process_all_tenants()


async def send_manual_follow_up(lead_id: int, message: str = None):
    """Função helper para enviar follow-up manual."""
    return await follow_up_service.send_manual_follow_up(lead_id, message)