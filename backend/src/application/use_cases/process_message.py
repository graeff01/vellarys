"""
CASO DE USO: PROCESSAR MENSAGEM (VERSÃO PRD COM EMPREENDIMENTOS + PORTAL)
=========================================================================
"""

import logging
import traceback
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified



from src.infrastructure.services.property_lookup_service import (
    buscar_imovel_na_mensagem,
    build_property_context,
)


from src.domain.entities import (
    Tenant, Lead, Message, Channel, LeadEvent, Notification, Empreendimento
)
from src.domain.entities.enums import LeadStatus, EventType
from src.domain.prompts import build_system_prompt, get_niche_config
from src.infrastructure.services import (
    extract_lead_data,
    qualify_lead,
    generate_lead_summary,
    execute_handoff,
    run_ai_guards_async,
    mark_lead_activity,
    check_handoff_triggers,
    check_business_hours,
    notify_lead_hot,
    notify_lead_empreendimento,
    notify_out_of_hours,
    notify_handoff_requested,
    notify_gestor,
)

from src.infrastructure.services.openai_service import (
    detect_sentiment,
    generate_context_aware_response,
    generate_conversation_summary,
    calculate_typing_delay,
)

from src.infrastructure.services.ai_security import (
    build_security_instructions,
    sanitize_response,
    should_handoff as check_ai_handoff,
)

from src.infrastructure.services.security_service import (
    run_security_check,
    get_safe_response_for_threat,
)
from src.infrastructure.services.message_rate_limiter import (
    check_message_rate_limit,
    get_rate_limit_response,
)
from src.infrastructure.services.audit_service import (
    log_message_received,
    log_security_threat,
    log_ai_action,
)
from src.infrastructure.services.lgpd_service import (
    detect_lgpd_request,
    get_lgpd_response,
    export_lead_data,
    delete_lead_data,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES
# =============================================================================

MAX_MESSAGE_LENGTH = 2000
MAX_CONVERSATION_HISTORY = 30

FALLBACK_RESPONSES = {
    "error": "Desculpe, estou com uma instabilidade momentânea. Tente novamente em alguns segundos.",
    "out_of_scope": "Desculpe, não posso ajudá-lo com isso. Posso ajudar com nossos produtos e serviços!",
    "security": "Por segurança, não posso responder a essa mensagem.",
}

NICHOS_IMOBILIARIOS = ["realestate", "imobiliaria", "real_estate", "imobiliario"]


# =============================================================================
# HELPERS
# =============================================================================

def migrate_settings_if_needed(settings: dict) -> dict:
    """Migra settings do formato antigo para o novo (com identity)."""
    if not settings:
        return {}
    
    if "identity" in settings:
        return settings
    
    try:
        migrated = dict(settings)
        
        migrated["identity"] = {
            "description": settings.get("scope_description", ""),
            "products_services": [],
            "not_offered": [],
            "tone_style": {
                "tone": settings.get("tone", "cordial"),
                "personality_traits": [],
                "communication_style": "",
                "avoid_phrases": [],
                "use_phrases": [],
            },
            "target_audience": {"description": "", "segments": [], "pain_points": []},
            "business_rules": settings.get("custom_rules", []),
            "differentials": [],
            "keywords": [],
            "required_questions": settings.get("custom_questions", []),
            "required_info": [],
            "additional_context": "",
        }
        
        migrated["basic"] = {
            "niche": settings.get("niche", "services"),
            "company_name": settings.get("company_name", ""),
        }
        
        migrated["scope"] = {
            "enabled": settings.get("scope_enabled", True),
            "description": settings.get("scope_description", ""),
            "allowed_topics": [],
            "blocked_topics": [],
            "out_of_scope_message": settings.get("out_of_scope_message", 
                "Desculpe, não tenho informações sobre isso."),
        }
        
        migrated["faq"] = {
            "enabled": settings.get("faq_enabled", True),
            "items": settings.get("faq_items", []),
        }
        
        return migrated
    except Exception as e:
        logger.error(f"Erro migrando settings: {e}")
        return settings


def extract_ai_context(tenant: Tenant, settings: dict) -> dict:
    """Extrai contexto necessário para a IA."""
    try:
        identity = settings.get("identity", {})
        basic = settings.get("basic", {})
        scope = settings.get("scope", {})
        faq = settings.get("faq", {})
        
        company_name = basic.get("company_name") or settings.get("company_name") or tenant.name
        niche_id = basic.get("niche") or settings.get("niche") or "services"
        tone = identity.get("tone_style", {}).get("tone") or settings.get("tone") or "cordial"
        
        faq_items = []
        if faq.get("enabled", True):
            faq_items = faq.get("items", []) or settings.get("faq_items", [])
        
        custom_questions = identity.get("required_questions", []) or settings.get("custom_questions", [])
        custom_rules = identity.get("business_rules", []) or settings.get("custom_rules", [])
        scope_description = scope.get("description") or settings.get("scope_description", "")
        
        default_out_of_scope = (
            f"Desculpe, não posso ajudá-lo com isso. "
            f"A {company_name} trabalha com {scope_description or 'nossos produtos e serviços'}. "
            f"Posso te ajudar com algo relacionado?"
        )
        
        out_of_scope_message = (
            scope.get("out_of_scope_message") or 
            settings.get("out_of_scope_message") or 
            default_out_of_scope
        )
        
        return {
            "company_name": company_name,
            "niche_id": niche_id,
            "tone": tone,
            "identity": identity if identity else None,
            "scope_config": scope if scope else None,
            "faq_items": faq_items,
            "custom_questions": custom_questions,
            "custom_rules": custom_rules,
            "scope_description": scope_description,
            "custom_prompt": settings.get("custom_prompt"),
            "ai_scope_description": scope_description,
            "ai_out_of_scope_message": out_of_scope_message,
        }
    except Exception as e:
        logger.error(f"Erro extraindo contexto IA: {e}")
        return {
            "company_name": tenant.name,
            "niche_id": "services",
            "tone": "cordial",
            "ai_out_of_scope_message": "Desculpe, não posso ajudá-lo com isso.",
            "scope_description": "",
        }


def sanitize_message_content(content: str) -> str:
    """Remove conteúdo potencialmente perigoso ou muito longo."""
    if not content:
        return ""
    content = content[:MAX_MESSAGE_LENGTH]
    content = content.replace('\0', '').replace('\r', '')
    return content.strip()


# =============================================================================
# FUNÇÕES DE EMPREENDIMENTO
# =============================================================================

async def detect_empreendimento(
    db: AsyncSession,
    tenant_id: int,
    message: str,
    niche_id: str,
) -> Optional[Empreendimento]:
    """Detecta se a mensagem contém gatilhos de algum empreendimento."""
    if niche_id.lower() not in NICHOS_IMOBILIARIOS:
        return None
    
    try:
        result = await db.execute(
            select(Empreendimento)
            .where(Empreendimento.tenant_id == tenant_id)
            .where(Empreendimento.ativo == True)
            .order_by(Empreendimento.prioridade.desc())
        )
        empreendimentos = result.scalars().all()
        
        if not empreendimentos:
            return None
        
        message_lower = message.lower()
        
        for emp in empreendimentos:
            if emp.gatilhos:
                for gatilho in emp.gatilhos:
                    if gatilho.lower() in message_lower:
                        logger.info(f"🏢 Empreendimento detectado: {emp.nome} (gatilho: {gatilho})")
                        return emp
        
        return None
        
    except Exception as e:
        logger.error(f"Erro detectando empreendimento: {e}")
        return None


async def get_empreendimento_from_lead(
    db: AsyncSession,
    lead: Lead,
) -> Optional[Empreendimento]:
    """Recupera o empreendimento associado ao lead (se houver)."""
    try:
        if not lead.custom_data:
            return None
        
        emp_id = lead.custom_data.get("empreendimento_id")
        if not emp_id:
            return None
        
        result = await db.execute(
            select(Empreendimento)
            .where(Empreendimento.id == emp_id)
            .where(Empreendimento.ativo == True)
        )
        emp = result.scalar_one_or_none()
        
        if emp:
            logger.info(f"🏢 Empreendimento recuperado do lead: {emp.nome}")
        
        return emp
        
    except Exception as e:
        logger.error(f"Erro recuperando empreendimento do lead: {e}")
        return None


def build_empreendimento_context(empreendimento: Empreendimento) -> str:
    """Constrói o contexto do empreendimento para adicionar ao prompt da IA."""
    sections = []
    
    sections.append(f"{'=' * 60}")
    sections.append(f"🏢 EMPREENDIMENTO: {empreendimento.nome.upper()}")
    sections.append(f"{'=' * 60}")
    
    status_map = {
        "lancamento": "🚀 Lançamento",
        "em_obras": "🏗️ Em Obras",
        "pronto_para_morar": "🏠 Pronto para Morar",
    }
    sections.append(f"\n**Status:** {status_map.get(empreendimento.status, empreendimento.status)}")
    
    if empreendimento.descricao:
        sections.append(f"\n**Sobre o empreendimento:**\n{empreendimento.descricao}")
    
    loc_parts = []
    if empreendimento.endereco:
        loc_parts.append(empreendimento.endereco)
    if empreendimento.bairro:
        loc_parts.append(f"Bairro: {empreendimento.bairro}")
    if empreendimento.cidade:
        loc_parts.append(f"Cidade: {empreendimento.cidade}")
        if empreendimento.estado:
            loc_parts[-1] += f"/{empreendimento.estado}"
    
    if loc_parts:
        sections.append(f"\n**Localização:**\n" + "\n".join(loc_parts))
    
    if empreendimento.descricao_localizacao:
        sections.append(f"\n**Sobre a região:**\n{empreendimento.descricao_localizacao}")
    
    if empreendimento.tipologias:
        sections.append(f"\n**Tipologias disponíveis:**\n" + ", ".join(empreendimento.tipologias))
    
    if empreendimento.metragem_minima or empreendimento.metragem_maxima:
        if empreendimento.metragem_minima and empreendimento.metragem_maxima:
            metragem = f"{empreendimento.metragem_minima}m² a {empreendimento.metragem_maxima}m²"
        elif empreendimento.metragem_minima:
            metragem = f"A partir de {empreendimento.metragem_minima}m²"
        else:
            metragem = f"Até {empreendimento.metragem_maxima}m²"
        sections.append(f"\n**Metragem:** {metragem}")
    
    if empreendimento.vagas_minima or empreendimento.vagas_maxima:
        if empreendimento.vagas_minima and empreendimento.vagas_maxima:
            if empreendimento.vagas_minima == empreendimento.vagas_maxima:
                vagas = f"{empreendimento.vagas_minima} vaga(s)"
            else:
                vagas = f"{empreendimento.vagas_minima} a {empreendimento.vagas_maxima} vagas"
        elif empreendimento.vagas_minima:
            vagas = f"A partir de {empreendimento.vagas_minima} vaga(s)"
        else:
            vagas = f"Até {empreendimento.vagas_maxima} vagas"
        sections.append(f"**Vagas de garagem:** {vagas}")
    
    estrutura_parts = []
    if empreendimento.torres:
        estrutura_parts.append(f"{empreendimento.torres} torre(s)")
    if empreendimento.andares:
        estrutura_parts.append(f"{empreendimento.andares} andares")
    if empreendimento.total_unidades:
        estrutura_parts.append(f"{empreendimento.total_unidades} unidades")
    
    if estrutura_parts:
        sections.append(f"**Estrutura:** {', '.join(estrutura_parts)}")
    
    if empreendimento.previsao_entrega:
        sections.append(f"\n**Previsão de entrega:** {empreendimento.previsao_entrega}")
    
    if empreendimento.preco_minimo or empreendimento.preco_maximo:
        if empreendimento.preco_minimo and empreendimento.preco_maximo:
            preco = f"R$ {empreendimento.preco_minimo:,.0f} a R$ {empreendimento.preco_maximo:,.0f}".replace(",", ".")
        elif empreendimento.preco_minimo:
            preco = f"A partir de R$ {empreendimento.preco_minimo:,.0f}".replace(",", ".")
        else:
            preco = f"Até R$ {empreendimento.preco_maximo:,.0f}".replace(",", ".")
        sections.append(f"\n**Faixa de investimento:** {preco}")
    
    condicoes = []
    if empreendimento.aceita_financiamento:
        condicoes.append("Financiamento bancário")
    if empreendimento.aceita_fgts:
        condicoes.append("FGTS")
    if empreendimento.aceita_permuta:
        condicoes.append("Permuta")
    if empreendimento.aceita_consorcio:
        condicoes.append("Consórcio")
    
    if condicoes:
        sections.append(f"**Formas de pagamento:** {', '.join(condicoes)}")
    
    if empreendimento.condicoes_especiais:
        sections.append(f"**Condições especiais:** {empreendimento.condicoes_especiais}")
    
    if empreendimento.itens_lazer:
        sections.append(f"\n**Itens de lazer:**\n" + ", ".join(empreendimento.itens_lazer))
    
    if empreendimento.diferenciais:
        sections.append(f"\n**Diferenciais:**\n" + ", ".join(empreendimento.diferenciais))
    
    if empreendimento.instrucoes_ia:
        sections.append(f"\n**Instruções especiais:**\n{empreendimento.instrucoes_ia}")
    
    if empreendimento.perguntas_qualificacao:
        sections.append(f"\n**Perguntas que você DEVE fazer sobre este empreendimento:**")
        for i, pergunta in enumerate(empreendimento.perguntas_qualificacao, 1):
            sections.append(f"{i}. {pergunta}")
    
    sections.append(f"\n{'=' * 60}")
    
    return "\n".join(sections)


async def update_empreendimento_stats(
    db: AsyncSession,
    empreendimento: Empreendimento,
    is_new_lead: bool = False,
    is_qualified: bool = False,
):
    """Atualiza estatísticas do empreendimento."""
    try:
        if is_new_lead:
            empreendimento.total_leads = (empreendimento.total_leads or 0) + 1
        if is_qualified:
            empreendimento.leads_qualificados = (empreendimento.leads_qualificados or 0) + 1
    except Exception as e:
        logger.error(f"Erro atualizando stats do empreendimento: {e}")


# =============================================================================
# FUNÇÕES DE BANCO
# =============================================================================

async def get_or_create_lead(
    db: AsyncSession,
    tenant: Tenant,
    channel: Channel,
    external_id: str,
    sender_name: str = None,
    sender_phone: str = None,
    source: str = "organico",
    campaign: str = None,
) -> tuple[Lead, bool]:
    """Busca lead existente ou cria um novo."""
    result = await db.execute(
        select(Lead)
        .where(Lead.tenant_id == tenant.id)
        .where(Lead.external_id == external_id)
    )
    lead = result.scalar_one_or_none()
    
    if lead:
        return lead, False
    
    lead = Lead(
        tenant_id=tenant.id,
        channel_id=channel.id if channel else None,
        external_id=external_id,
        name=sender_name,
        phone=sender_phone,
        source=source,
        campaign=campaign,
        status=LeadStatus.NEW.value,
    )
    db.add(lead)
    await db.flush()
    
    event = LeadEvent(
        lead_id=lead.id,
        event_type=EventType.STATUS_CHANGE.value,
        old_value=None,
        new_value=LeadStatus.NEW.value,
        description="Lead criado automaticamente via atendimento"
    )
    db.add(event)
    
    return lead, True


async def get_conversation_history(
    db: AsyncSession,
    lead_id: int,
    limit: int = MAX_CONVERSATION_HISTORY,
) -> list[dict]:
    """Busca histórico de mensagens do lead."""
    try:
        result = await db.execute(
            select(Message)
            .where(Message.lead_id == lead_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        return [{"role": msg.role, "content": msg.content} for msg in reversed(messages)]
    except Exception as e:
        logger.error(f"Erro ao buscar histórico: {e}")
        return []


async def get_last_message_time(db: AsyncSession, lead_id: int) -> Optional[datetime]:
    """Retorna o timestamp da última mensagem do lead."""
    try:
        result = await db.execute(
            select(Message.created_at)
            .where(Message.lead_id == lead_id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Erro ao buscar última mensagem: {e}")
        return None


async def count_lead_messages(db: AsyncSession, lead_id: int) -> int:
    """Conta total de mensagens do lead."""
    try:
        result = await db.execute(
            select(func.count(Message.id)).where(Message.lead_id == lead_id)
        )
        return result.scalar() or 0
    except Exception as e:
        logger.error(f"Erro ao contar mensagens: {e}")
        return 0


# =============================================================================
# FUNÇÃO PRINCIPAL
# =============================================================================

async def process_message(
    db: AsyncSession,
    tenant_slug: str,
    channel_type: str,
    external_id: str,
    content: str,
    sender_name: str = None,
    sender_phone: str = None,
    source: str = "organico",
    campaign: str = None,
) -> dict:
    """Processa uma mensagem recebida de um lead."""
    
    empreendimento_detectado: Optional[Empreendimento] = None
    imovel_portal: Optional[Dict] = None  # ← INICIALIZA AQUI
    gestor_ja_notificado = False
    
    # =========================================================================
    # 1. SANITIZAÇÃO
    # =========================================================================
    try:
        content = sanitize_message_content(content)
        if not content or len(content.strip()) < 1:
            return {"success": False, "error": "Mensagem vazia", "reply": FALLBACK_RESPONSES["error"]}
        
        logger.info(f"📥 Processando: Tenant={tenant_slug}, Sender={sender_phone or external_id}")
    except Exception as e:
        logger.error(f"Erro na sanitização: {e}")
        return {"success": False, "error": str(e), "reply": FALLBACK_RESPONSES["error"]}
    
    # =========================================================================
    # 2. RATE LIMITING
    # =========================================================================
    try:
        rate_limit_result = await check_message_rate_limit(
            phone=sender_phone or external_id,
            tenant_id=None,
        )
        if not rate_limit_result.allowed:
            logger.warning(f"Rate limit: {sender_phone or external_id}")
            return {
                "success": True,
                "reply": get_rate_limit_response(),
                "lead_id": None,
                "is_new_lead": False,
                "blocked_reason": "rate_limit",
            }
    except Exception as e:
        logger.error(f"Erro no rate limit: {e}")
    
    # =========================================================================
    # 3. SECURITY CHECK
    # =========================================================================
    try:
        security_result = run_security_check(
            content=content,
            sender_id=sender_phone or external_id,
            tenant_id=None,
        )
        if not security_result.is_safe and security_result.should_block:
            logger.warning(f"Mensagem bloqueada: {security_result.threat_type}")
            return {
                "success": True,
                "reply": get_safe_response_for_threat(security_result.threat_type),
                "lead_id": None,
                "is_new_lead": False,
                "security_blocked": True,
            }
        content = security_result.sanitized_content
    except Exception as e:
        logger.error(f"Erro no security check: {e}")
    
    # =========================================================================
    # 4. BUSCA TENANT E CANAL
    # =========================================================================
    try:
        result = await db.execute(
            select(Tenant).where(Tenant.slug == tenant_slug).where(Tenant.active == True)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            logger.error(f"Tenant não encontrado: {tenant_slug}")
            return {"success": False, "error": "Tenant não encontrado", "reply": FALLBACK_RESPONSES["error"]}
        
        result = await db.execute(
            select(Channel)
            .where(Channel.tenant_id == tenant.id)
            .where(Channel.type == channel_type)
            .where(Channel.active == True)
        )
        channel = result.scalar_one_or_none()
        
    except Exception as e:
        logger.error(f"Erro ao buscar tenant/canal: {e}")
        return {"success": False, "error": "Erro interno", "reply": FALLBACK_RESPONSES["error"]}
    
    # =========================================================================
    # 5. VERIFICAÇÃO DE HORÁRIO COMERCIAL
    # =========================================================================
    is_out_of_hours = False
    out_of_hours_message = ""
    
    try:
        bh_result = check_business_hours(tenant)
        
        if not bh_result.is_open:
            is_out_of_hours = True
            logger.info(f"⏰ Fora do horário comercial: {bh_result.reason}")
            
            out_of_hours_message = (
                "\n\n---\n"
                "⏰ *Você está entrando em contato fora do nosso horário comercial.*\n"
                "Mas fique tranquilo! Já registramos seu contato e um especialista "
                "entrará em contato com você o mais breve possível! 🙌"
            )
            
    except Exception as e:
        logger.error(f"Erro na verificação de horário: {e}")
    
    # =========================================================================
    # 6. EXTRAI CONTEXTO E SETTINGS
    # =========================================================================
    settings = migrate_settings_if_needed(tenant.settings or {})
    ai_context = extract_ai_context(tenant, settings)
    
    logger.info(f"Contexto: {ai_context['company_name']} - Nicho: {ai_context['niche_id']}")
    
    # =========================================================================
    # 7. BUSCA/CRIA LEAD
    # =========================================================================
    try:
        lead, is_new = await get_or_create_lead(
            db=db, tenant=tenant, channel=channel, external_id=external_id,
            sender_name=sender_name, sender_phone=sender_phone,
            source=source, campaign=campaign,
        )
        
        await log_message_received(
            db=db, tenant_id=tenant.id, lead_id=lead.id,
            content_preview=content[:100], channel=channel_type,
        )
        
        logger.info(f"Lead {'criado' if is_new else 'encontrado'}: {lead.id}")
    except Exception as e:
        logger.error(f"Erro ao buscar/criar lead: {e}")
        return {"success": False, "error": "Erro ao processar lead", "reply": FALLBACK_RESPONSES["error"]}
    
    # =========================================================================
    # 8. NOTIFICAÇÃO DE LEAD NOVO
    # =========================================================================
    if is_new:
        try:
            if not lead.custom_data:
                lead.custom_data = {}
            lead.custom_data["primeira_mensagem"] = content[:500]
            
            notification_type = "lead_out_of_hours" if is_out_of_hours else "lead_new"
            
            await notify_gestor(
                db=db,
                tenant=tenant,
                lead=lead,
                notification_type=notification_type,
                extra_context={"primeira_mensagem": content[:200]},
            )
            
            gestor_ja_notificado = True
            logger.info(f"📲 Gestor notificado sobre lead NOVO: {lead.id}")
            
        except Exception as e:
            logger.error(f"Erro notificando gestor sobre lead novo: {e}")
    
    # =========================================================================
    # 9. DETECÇÃO DE EMPREENDIMENTO
    # =========================================================================
    try:
        empreendimento_detectado = await detect_empreendimento(
            db=db,
            tenant_id=tenant.id,
            message=content,
            niche_id=ai_context["niche_id"],
        )
        
        if not empreendimento_detectado and not is_new:
            empreendimento_detectado = await get_empreendimento_from_lead(db, lead)
        
        if empreendimento_detectado:
            logger.info(f"🏢 Empreendimento ativo: {empreendimento_detectado.nome}")
            
            if not lead.custom_data:
                lead.custom_data = {}
            
            old_emp_id = lead.custom_data.get("empreendimento_id")
            if old_emp_id != empreendimento_detectado.id:
                lead.custom_data["empreendimento_id"] = empreendimento_detectado.id
                lead.custom_data["empreendimento_nome"] = empreendimento_detectado.nome
            
            if is_new:
                await update_empreendimento_stats(db, empreendimento_detectado, is_new_lead=True)
                
                if empreendimento_detectado.vendedor_id:
                    lead.assigned_seller_id = empreendimento_detectado.vendedor_id
                    lead.assignment_method = "empreendimento"
                    lead.assigned_at = datetime.now(timezone.utc)
            
            if empreendimento_detectado.perguntas_qualificacao:
                ai_context["custom_questions"] = (
                    ai_context.get("custom_questions", []) + 
                    empreendimento_detectado.perguntas_qualificacao
                )
                
    except Exception as e:
        logger.error(f"Erro na detecção de empreendimento: {e}")

    # =========================================================================
    # 10. NOTIFICAÇÃO ESPECÍFICA DE EMPREENDIMENTO
    # =========================================================================
    if empreendimento_detectado and empreendimento_detectado.notificar_gestor and is_new and not gestor_ja_notificado:
        try:
            await notify_lead_empreendimento(db, tenant, lead, empreendimento_detectado)
            gestor_ja_notificado = True
            logger.info(f"📲 Notificação específica de empreendimento: {empreendimento_detectado.nome}")
        except Exception as e:
            logger.error(f"Erro criando notificação de empreendimento: {e}")
    
    # =========================================================================
    # 11. LGPD CHECK
    # =========================================================================
    try:
        lgpd_request = detect_lgpd_request(content)
        if lgpd_request:
            logger.info(f"LGPD request: {lgpd_request}")
            
            user_message = Message(lead_id=lead.id, role="user", content=content, tokens_used=0)
            db.add(user_message)
            
            lgpd_reply = get_lgpd_response(lgpd_request, tenant_name=ai_context["company_name"])
            
            assistant_message = Message(lead_id=lead.id, role="assistant", content=lgpd_reply, tokens_used=0)
            db.add(assistant_message)
            await db.commit()
            
            return {
                "success": True,
                "reply": lgpd_reply,
                "lead_id": lead.id,
                "is_new_lead": is_new,
                "lgpd_request": lgpd_request,
            }
    except Exception as e:
        logger.error(f"Erro no LGPD check: {e}")
    
    # =========================================================================
    # 12. STATUS CHECK (lead já transferido)
    # =========================================================================
    if lead.status == LeadStatus.HANDED_OFF.value:
        user_message = Message(lead_id=lead.id, role="user", content=content, tokens_used=0)
        db.add(user_message)
        await db.commit()
        
        return {
            "success": True,
            "reply": None,
            "lead_id": lead.id,
            "is_new_lead": False,
            "status": "transferido",
            "message": "Lead já transferido",
        }
    
    # =========================================================================
    # 13. BUSCA HISTÓRICO
    # =========================================================================
    history = await get_conversation_history(db, lead.id)
    message_count = await count_lead_messages(db, lead.id)


    """
SEÇÃO 13.5 MELHORADA - DETECTA MUDANÇA DE IMÓVEL
================================================
Substitua a seção 13.5 no process_message.py

Esta versão:
1. Detecta quando o lead pergunta sobre um NOVO imóvel
2. Faz nova busca quando detecta código diferente
3. Atualiza o contexto corretamente
"""

    # =========================================================================
    # 13.5 PRÉ-CONTEXTO IMOBILIÁRIO (VERSÃO MELHORADA)
    # =========================================================================
    
    logger.info(f"🔍 [13.5] Iniciando pré-contexto imobiliário")
    logger.info(f"🔍 [13.5] niche_id = {ai_context['niche_id']}")
    
    # Só processa se for nicho imobiliário
    if ai_context["niche_id"].lower() in NICHOS_IMOBILIARIOS:
        logger.info(f"🏠 [13.5] Nicho imobiliário confirmado!")
        
        # 🔍 PRIMEIRO: Verifica se a mensagem atual menciona um código
        from src.infrastructure.services.property_lookup_service import extrair_codigo_imovel
        codigo_na_mensagem = extrair_codigo_imovel(content)
        
        # 📦 Pega código do imóvel salvo (se houver)
        codigo_salvo = None
        if lead.custom_data and lead.custom_data.get("imovel_portal"):
            codigo_salvo = lead.custom_data["imovel_portal"].get("codigo")
        
        logger.info(f"🔍 [13.5] código_na_mensagem = {codigo_na_mensagem}")
        logger.info(f"🔍 [13.5] código_salvo = {codigo_salvo}")
        
        # 🔄 DECISÃO: Buscar novo ou reutilizar salvo?
        if codigo_na_mensagem:
            # Lead mencionou um código na mensagem
            if codigo_na_mensagem != codigo_salvo:
                # É um código DIFERENTE - faz nova busca!
                logger.info(f"🆕 [13.5] NOVO código detectado: {codigo_na_mensagem} (era {codigo_salvo})")
                imovel_portal = buscar_imovel_na_mensagem(content)
                
                if imovel_portal:
                    logger.info(f"✅ [13.5] Novo imóvel encontrado: {imovel_portal.get('codigo')}")
                else:
                    logger.warning(f"⚠️ [13.5] Código {codigo_na_mensagem} não encontrado no portal")
            else:
                # É o MESMO código - reutiliza
                logger.info(f"🔄 [13.5] Mesmo código, reutilizando salvo")
                imovel_portal = lead.custom_data.get("imovel_portal")
        
        elif codigo_salvo:
            # Mensagem não tem código, mas tem um salvo - reutiliza
            logger.info(f"🔄 [13.5] Reutilizando imóvel salvo: {codigo_salvo}")
            imovel_portal = lead.custom_data.get("imovel_portal")
        
        else:
            # Não tem código na mensagem nem salvo - busca no histórico
            logger.info(f"🕰️ [13.5] Buscando no histórico...")
            if history:
                for msg in reversed(history):
                    if msg.get("role") == "user":
                        imovel_portal = buscar_imovel_na_mensagem(msg.get("content", ""))
                        if imovel_portal:
                            logger.info(f"✅ [13.5] Encontrado no histórico: {imovel_portal.get('codigo')}")
                            break
        
        # 💾 SALVA no lead (se encontrou algo)
        if imovel_portal:
            logger.info(f"💾 [13.5] Salvando imóvel {imovel_portal.get('codigo')} no lead")
            
            if not lead.custom_data:
                lead.custom_data = {}
            
            lead.custom_data["imovel_portal"] = {
                "codigo": imovel_portal.get("codigo"),
                "titulo": imovel_portal.get("titulo"),
                "tipo": imovel_portal.get("tipo"),
                "regiao": imovel_portal.get("regiao"),
                "quartos": imovel_portal.get("quartos"),
                "banheiros": imovel_portal.get("banheiros"),
                "vagas": imovel_portal.get("vagas"),
                "metragem": imovel_portal.get("metragem"),
                "preco": imovel_portal.get("preco"),
                "descricao": imovel_portal.get("descricao", ""),
            }
            lead.custom_data["contexto_ativo"] = "imovel_portal"
            
            # ⚠️ CRÍTICO: Força SQLAlchemy a detectar mudança
            flag_modified(lead, "custom_data")
            
            logger.info(f"✅ [13.5] Imóvel salvo com flag_modified!")
        else:
            logger.info(f"❌ [13.5] Nenhum imóvel encontrado")
    else:
        logger.info(f"⏭️ [13.5] Nicho não é imobiliário, pulando...")
    
    logger.info(f"🔍 [13.5] FIM - imovel_portal = {imovel_portal}")


    # =========================================================================
    # 14. AI GUARDS (APÓS PRÉ-CONTEXTO)
    # =========================================================================

    guards_result = {"can_respond": True}

    try:
        if empreendimento_detectado or imovel_portal:
            logger.info("🟢 Guards bypassados por contexto imobiliário ativo")
            guards_result = {"can_respond": True, "bypass": True}

        else:
            guards_result = await run_ai_guards_async(
                message=content,
                message_count=message_count,
                settings=settings,
                lead_qualification=lead.qualification or "frio",
            )

            if not guards_result.get("can_respond", True):
                guard_reason = guards_result.get("reason", "unknown")
                guard_response = (
                    guards_result.get("response")
                    or ai_context.get("ai_out_of_scope_message")
                    or FALLBACK_RESPONSES["out_of_scope"]
                )

                user_message = Message(
                    lead_id=lead.id, role="user", content=content, tokens_used=0
                )
                db.add(user_message)

                assistant_message = Message(
                    lead_id=lead.id, role="assistant", content=guard_response, tokens_used=0
                )
                db.add(assistant_message)

                await db.commit()

                return {
                    "success": True,
                    "reply": guard_response,
                    "lead_id": lead.id,
                    "is_new_lead": is_new,
                    "guard": guard_reason,
                }

    except Exception as e:
        logger.error(f"Erro nos guards: {e}")




    # =========================================================================
    # 15. HANDOFF TRIGGERS
    # =========================================================================
    try:
        handoff_triggers = settings.get("handoff", {}).get("triggers", []) or settings.get("handoff_triggers", [])
        trigger_found, trigger_matched = check_handoff_triggers(
            message=content,
            custom_triggers=handoff_triggers,
        )
        
        if trigger_found:
            logger.info(f"Handoff trigger: {trigger_matched}")
            
            user_message = Message(lead_id=lead.id, role="user", content=content, tokens_used=0)
            db.add(user_message)
            await db.flush()
            
            if not lead.summary:
                lead.summary = await generate_lead_summary(
                    conversation=history,
                    extracted_data=lead.custom_data or {},
                    qualification={"qualification": lead.qualification},
                )
            
            await notify_handoff_requested(db, tenant, lead, f"Trigger: {trigger_matched}")
            
            handoff_result = await execute_handoff(lead, tenant, "user_requested", db)
            
            assistant_message = Message(
                lead_id=lead.id, role="assistant",
                content=handoff_result["message_for_lead"], tokens_used=0,
            )
            db.add(assistant_message)
            await db.commit()
            
            return {
                "success": True,
                "reply": handoff_result["message_for_lead"],
                "lead_id": lead.id,
                "is_new_lead": is_new,
                "status": "transferido",
            }
    except Exception as e:
        logger.error(f"Erro nos handoff triggers: {e}")
    
    # =========================================================================
    # 16. ATUALIZA STATUS
    # =========================================================================
    if lead.status == LeadStatus.NEW.value:
        lead.status = LeadStatus.IN_PROGRESS.value
        event = LeadEvent(
            lead_id=lead.id,
            event_type=EventType.STATUS_CHANGE.value,
            old_value=LeadStatus.NEW.value,
            new_value=LeadStatus.IN_PROGRESS.value,
            description="Lead iniciou conversa"
        )
        db.add(event)
    
    # =========================================================================
    # 17. SALVA MENSAGEM DO USUÁRIO
    # =========================================================================
    user_message = Message(lead_id=lead.id, role="user", content=content, tokens_used=0)
    db.add(user_message)
    await db.flush()
    
    await mark_lead_activity(db, lead)
    history = await get_conversation_history(db, lead.id)
    
    # =========================================================================
    # 18. DETECÇÃO DE SENTIMENTO E CONTEXTO
    # =========================================================================
    sentiment = {"sentiment": "neutral", "confidence": 0.5}
    is_returning_lead = False
    hours_since_last = 0
    previous_summary = None
    
    try:
        sentiment = await detect_sentiment(content)
        
        if not is_new:
            last_message_time = await get_last_message_time(db, lead.id)
            if last_message_time:
                now = datetime.now(timezone.utc)
                if last_message_time.tzinfo is None:
                    last_message_time = last_message_time.replace(tzinfo=timezone.utc)
                
                time_diff = now - last_message_time
                hours_since_last = time_diff.total_seconds() / 3600
                
                if hours_since_last > 6:
                    is_returning_lead = True
                    if hours_since_last > 24 and len(history) >= 4:
                        previous_summary = await generate_conversation_summary(history)
                        if not lead.summary and previous_summary:
                            lead.summary = previous_summary
    except Exception as e:
        logger.error(f"Erro na detecção de sentimento: {e}")
    
    # =========================================================================
    # 19. CONTEXTO DO LEAD
    # =========================================================================
    lead_context = None
    if lead.custom_data:
        lead_context = {k: v for k, v in {
            "name": lead.name,
            "family_situation": lead.custom_data.get("family_situation"),
            "work_info": lead.custom_data.get("work_info"),
            "budget_range": lead.custom_data.get("budget_range"),
            "urgency_level": lead.custom_data.get("urgency_level"),
            "preferences": lead.custom_data.get("preferences"),
            "pain_points": lead.custom_data.get("pain_points"),
            "objections": lead.custom_data.get("objections"),
            "buying_signals": lead.custom_data.get("buying_signals"),
            "empreendimento_nome": lead.custom_data.get("empreendimento_nome"),
        }.items() if v is not None}
        if not lead_context:
            lead_context = None



    """
SEÇÃO 20 SUPER ROBUSTA - PROMPT INTELIGENTE
===========================================
Substitua a seção 20 no process_message.py

Esta versão tem instruções MUITO mais enfáticas para a IA:
1. NUNCA dizer "não tenho informações"
2. Responder qualquer pergunta sobre o imóvel
3. Lidar com objeções de forma natural
4. Manter contexto entre mensagens
"""

    # =========================================================================
    # 20. MONTA PROMPT (VERSÃO SUPER ROBUSTA)
    # =========================================================================
    
    logger.info(f"=" * 60)
    logger.info(f"🔍 [SEÇÃO 20] MONTANDO PROMPT")
    logger.info(f"🔍 [SEÇÃO 20] empreendimento = {empreendimento_detectado}")
    logger.info(f"🔍 [SEÇÃO 20] imovel_portal = {imovel_portal}")
    logger.info(f"=" * 60)
    
    try:
        system_prompt = build_system_prompt(
            niche_id=ai_context["niche_id"],
            company_name=ai_context["company_name"],
            tone=ai_context["tone"],
            custom_questions=ai_context.get("custom_questions", []),
            custom_rules=ai_context.get("custom_rules", []),
            custom_prompt=ai_context.get("custom_prompt"),
            faq_items=ai_context.get("faq_items", []),
            scope_description=ai_context.get("scope_description", ""),
            lead_context=lead_context,
            identity=ai_context.get("identity"),
            scope_config=ai_context.get("scope_config"),
        )
        
        # =================================================================
        # EMPREENDIMENTO (prioridade 1)
        # =================================================================
        if empreendimento_detectado:
            logger.info(f"🏢 [SEÇÃO 20] Injetando empreendimento: {empreendimento_detectado.nome}")
            empreendimento_context = build_empreendimento_context(empreendimento_detectado)
            system_prompt += f"\n\n{empreendimento_context}"
            
            system_prompt += f"""

⚠️ ATENÇÃO MÁXIMA - EMPREENDIMENTO DETECTADO ⚠️

O cliente demonstrou interesse específico no empreendimento **{empreendimento_detectado.nome}**.

VOCÊ DEVE:
✅ Usar TODAS as informações acima para responder
✅ Falar sobre endereço, preço, tipologias, lazer quando perguntado
✅ Fazer as perguntas de qualificação listadas
✅ Ser especialista neste empreendimento

VOCÊ NÃO PODE:
❌ Dizer "não tenho essa informação" se ela está acima
❌ Inventar dados que não estão listados
"""
        
        # =================================================================
        # 🏠 IMÓVEL PORTAL (prioridade 2)
        # =================================================================
        elif imovel_portal:
            cod = imovel_portal.get('codigo', 'N/A')
            quartos = imovel_portal.get('quartos', 'N/A')
            banheiros = imovel_portal.get('banheiros', 'N/A')
            vagas = imovel_portal.get('vagas', 'N/A')
            metragem = imovel_portal.get('metragem', 'N/A')
            preco = imovel_portal.get('preco', 'Consulte')
            regiao = imovel_portal.get('regiao', 'N/A')
            tipo = imovel_portal.get('tipo', 'Imóvel')
            descricao = imovel_portal.get('descricao', '')
            
            logger.info(f"🏠 [SEÇÃO 20] Injetando imóvel: {cod}")
            
            system_prompt += f"""

###############################################################
#                                                             #
#    🏠 CONTEXTO DO IMÓVEL - VOCÊ TEM TODAS AS INFORMAÇÕES    #
#                                                             #
###############################################################

DADOS DO IMÓVEL (código {cod}):
┌─────────────────────────────────────────────────────────────┐
│ Código:     {cod}
│ Tipo:       {tipo}
│ Localização: {regiao}
│ Quartos:    {quartos}
│ Banheiros:  {banheiros}
│ Vagas:      {vagas}
│ Área:       {metragem} m²
│ Preço:      {preco}
│ Descrição:  {descricao[:200] if descricao else 'N/A'}
└─────────────────────────────────────────────────────────────┘

###############################################################
#                COMO VOCÊ DEVE RESPONDER                     #
###############################################################

REGRA #1 - RESPOSTAS DIRETAS (use os dados acima!):
- "quantos quartos?" → "Este imóvel tem {quartos} quartos!"
- "qual o preço?" / "quanto custa?" / "valor?" → "O valor é {preco}"
- "qual o tamanho?" / "metragem?" / "área?" → "A área é de {metragem} m²"
- "onde fica?" / "localização?" → "Fica em {regiao}"
- "tem garagem?" / "vagas?" → "Tem {vagas} vaga(s)"
- "banheiros?" → "Tem {banheiros} banheiro(s)"
- "qual o código?" → "O código é {cod}"

REGRA #2 - PERGUNTAS DE CONTEXTO (continue naturalmente):
- "é bom?" → "Sim! É um ótimo {tipo} com {quartos} quartos em {regiao}. Quer saber mais?"
- "vale a pena?" → "Com certeza! Por {preco} você tem {metragem}m² com {quartos} quartos!"
- "tem mais fotos?" → "Posso te enviar mais detalhes! Você prefere agendar uma visita?"
- "aceita financiamento?" → "Vou verificar as condições de pagamento. Você tem interesse em financiar?"

REGRA #3 - PERGUNTAS DE QUALIFICAÇÃO (faça uma por vez):
Após responder, faça UMA dessas perguntas:
- "Você está buscando para morar ou investir?"
- "Esse tamanho atende sua necessidade?"  
- "Quer que eu agende uma visita?"
- "Tem mais alguém que vai decidir junto com você?"
- "Qual é o seu prazo para se mudar?"

###############################################################
#                    PROIBIÇÕES ABSOLUTAS                     #
###############################################################

🚫 NUNCA, EM HIPÓTESE ALGUMA, DIGA:
- "Desculpe, não tenho informações sobre isso"
- "Não tenho essa informação"
- "Não posso ajudar com isso"
- "Não sei responder"
- "Preciso verificar"

Se você não souber algo específico, RESPONDA com o que você SABE:
❌ ERRADO: "Não tenho informações sobre isso"
✅ CERTO: "O imóvel tem {quartos} quartos e {metragem}m². Quer saber mais algum detalhe?"

###############################################################
#                     ESTILO DE RESPOSTA                      #
###############################################################

✅ Seja BREVE (2-3 frases no máximo)
✅ Seja SIMPÁTICO e NATURAL (como um corretor amigo)
✅ Use emojis com moderação (1-2 por mensagem)
✅ SEMPRE termine com uma pergunta de engajamento
✅ Chame o cliente pelo nome se souber

EXEMPLOS DE BOAS RESPOSTAS:
- "Este apartamento tem 2 quartos e 36m²! 🏠 Você está buscando para morar ou investir?"
- "O valor é R$ 245.000! Ótimo custo-benefício para a região. Quer agendar uma visita?"
- "Fica em Porto Alegre, região bem valorizada! Esse tamanho atende você?"

###############################################################
"""
        
        # =================================================================
        # NICHO IMOBILIÁRIO SEM IMÓVEL ESPECÍFICO
        # =================================================================
        elif ai_context["niche_id"].lower() in NICHOS_IMOBILIARIOS:
            logger.info(f"🏠 [SEÇÃO 20] Nicho imobiliário sem imóvel específico")
            
            # Verifica se mencionou código não encontrado
            from src.infrastructure.services.property_lookup_service import extrair_codigo_imovel
            codigo_mencionado = extrair_codigo_imovel(content)
            
            if codigo_mencionado:
                logger.warning(f"⚠️ [SEÇÃO 20] Código {codigo_mencionado} não encontrado")
                system_prompt += f"""

###############################################################
#    ⚠️ CLIENTE PERGUNTOU SOBRE IMÓVEL NÃO ENCONTRADO        #
###############################################################

O cliente mencionou o código {codigo_mencionado}, mas não temos os dados deste imóvel.

RESPONDA DE FORMA ACOLHEDORA:
"Oi! Vi que você se interessou pelo imóvel {codigo_mencionado}! 
Vou verificar os detalhes pra você. Me conta: você tá buscando pra morar ou investir?"

OU

"Que bom seu interesse! Deixa eu checar esse imóvel. Enquanto isso, 
me fala: qual região você prefere?"

🚫 NUNCA DIGA:
- "Não tenho informações sobre esse código"
- "Código não encontrado"
- "Não existe"

###############################################################
"""
            else:
                # Conversa geral sobre imóveis
                system_prompt += f"""

###############################################################
#         🏠 CONVERSA GERAL SOBRE IMÓVEIS                    #
###############################################################

Você é um corretor simpático da {ai_context['company_name']}.
O cliente ainda não mencionou um imóvel específico.

SEU OBJETIVO:
1. Entender o que o cliente procura
2. Fazer perguntas de qualificação
3. Oferecer ajuda para encontrar o imóvel ideal

PERGUNTAS ÚTEIS:
- "Você está buscando para morar ou investir?"
- "Qual região você prefere?"
- "Quantos quartos você precisa?"
- "Qual sua faixa de investimento?"

###############################################################
"""
        else:
            logger.info(f"⏭️ [SEÇÃO 20] Nicho não é imobiliário")
            
    except Exception as e:
        logger.error(f"💥 [SEÇÃO 20] ERRO: {e}")
        import traceback
        logger.error(traceback.format_exc())
        system_prompt = f"Você é assistente da {ai_context['company_name']}. Seja educado e profissional."
    
    logger.info(f"✅ [SEÇÃO 20] Prompt montado!")


    # =========================================================================
    # 21. PREPARA MENSAGENS E CHAMA IA
    # =========================================================================
    messages = [{"role": "system", "content": system_prompt}, *history]
    
    if ai_context.get("ai_scope_description") and not empreendimento_detectado and not imovel_portal:
        security_instructions = build_security_instructions(
            company_name=ai_context["company_name"],
            scope_description=ai_context["ai_scope_description"],
            out_of_scope_message=ai_context["ai_out_of_scope_message"]
        )
        messages[0]["content"] += f"\n\n{security_instructions}"
    
    if guards_result.get("reason") == "faq" and guards_result.get("response"):
        messages.append({
            "role": "system",
            "content": f"INFORMAÇÃO DO FAQ: {guards_result['response']}"
        })
    
    ai_response = None
    final_response = ""
    was_blocked = False
    tokens_used = 0
    
    try:
        ai_response = await generate_context_aware_response(
            messages=messages,
            lead_data=lead_context or {},
            sentiment=sentiment,
            tone=ai_context["tone"],
            is_returning_lead=is_returning_lead,
            hours_since_last_message=hours_since_last,
            previous_summary=previous_summary or lead.summary,
        )
        
        final_response, was_blocked = sanitize_response(
            ai_response["content"],
            ai_context["ai_out_of_scope_message"]
        )
        
        # Bypass do bloqueio para contexto imobiliário
        if was_blocked and (empreendimento_detectado or imovel_portal):
            logger.warning(f"⚠️ Resposta bloqueada mas contexto imobiliário detectado - usando original")
            final_response = ai_response["content"]
            was_blocked = False
        
        tokens_used = ai_response.get("tokens_used", 0)
        
        if was_blocked:
            logger.warning(f"⚠️ Resposta bloqueada - Lead: {lead.id}")
            await log_ai_action(
                db=db, tenant_id=tenant.id, lead_id=lead.id,
                action_type="blocked_response",
                details={"reason": "hallucination_detected"},
            )
            
    except Exception as e:
        logger.error(f"Erro chamando IA: {e}")
        
        if empreendimento_detectado:
            final_response = (
                f"Olá! Que bom que você se interessou pelo {empreendimento_detectado.nome}! "
                f"É um empreendimento incrível. Como posso ajudá-lo?"
            )
        elif imovel_portal:
            final_response = (
                f"Olá! Vi que você se interessou pelo imóvel {imovel_portal.get('codigo')}! "
                f"Como posso ajudá-lo?"
            )
        else:
            final_response = (
                f"Olá! Sou a assistente da {ai_context['company_name']}. "
                f"O que você gostaria de saber sobre nossos serviços?"
            )
    
    # =========================================================================
    # 22. VERIFICA HANDOFF SUGERIDO PELA IA
    # =========================================================================
    should_transfer_by_ai = False
    try:
        handoff_check = check_ai_handoff(content, final_response)
        should_transfer_by_ai = handoff_check["should_handoff"]
    except Exception as e:
        logger.error(f"Erro verificando handoff IA: {e}")
    
    # =========================================================================
    # 23. SALVA RESPOSTA
    # =========================================================================
    assistant_message = Message(
        lead_id=lead.id,
        role="assistant",
        content=final_response,
        tokens_used=tokens_used,
    )
    db.add(assistant_message)
    
    await log_ai_action(
        db=db, tenant_id=tenant.id, lead_id=lead.id,
        action_type="response",
        details={
            "tokens_used": tokens_used,
            "sentiment": sentiment.get("sentiment"),
            "was_blocked": was_blocked,
            "identity_loaded": bool(ai_context.get("identity")),
            "empreendimento_id": empreendimento_detectado.id if empreendimento_detectado else None,
            "imovel_portal_codigo": imovel_portal.get("codigo") if imovel_portal else None,
        },
    )
    
    # =========================================================================
    # 24. EXTRAI DADOS E QUALIFICA
    # =========================================================================
    try:
        total_messages = await count_lead_messages(db, lead.id)
        if total_messages % 3 == 0 or total_messages >= 4:
            await update_lead_data(db, lead, tenant, history + [
                {"role": "user", "content": content},
                {"role": "assistant", "content": final_response},
            ])
            
            if empreendimento_detectado and lead.qualification in ["morno", "quente", "hot"]:
                await update_empreendimento_stats(db, empreendimento_detectado, is_qualified=True)
    except Exception as e:
        logger.error(f"Erro extraindo dados: {e}")
    
    # =========================================================================
    # 25. HANDOFF FINAL
    # =========================================================================
    should_transfer = lead.qualification in ["quente", "hot"] or should_transfer_by_ai
    
    if should_transfer:
        try:
            handoff_reason = "lead_hot" if lead.qualification in ["quente", "hot"] else "ai_suggested"
            
            if not lead.summary:
                lead.summary = await generate_lead_summary(
                    conversation=history + [
                        {"role": "user", "content": content},
                        {"role": "assistant", "content": final_response},
                    ],
                    extracted_data=lead.custom_data or {},
                    qualification={"qualification": lead.qualification},
                )
            
            await notify_lead_hot(db, tenant, lead, empreendimento_detectado)
            
            handoff_result = await execute_handoff(lead, tenant, handoff_reason, db)
            
            transfer_message = Message(
                lead_id=lead.id,
                role="assistant",
                content=handoff_result["message_for_lead"],
                tokens_used=0,
            )
            db.add(transfer_message)
            
            reply_with_handoff = final_response + "\n\n" + handoff_result["message_for_lead"]
            if is_out_of_hours and is_new:
                reply_with_handoff += out_of_hours_message
            
            await db.commit()
            
            return {
                "success": True,
                "reply": reply_with_handoff,
                "lead_id": lead.id,
                "is_new_lead": is_new,
                "qualification": lead.qualification,
                "status": "transferido",
                "typing_delay": calculate_typing_delay(len(final_response)),
                "out_of_hours": is_out_of_hours,
            }
        except Exception as e:
            logger.error(f"Erro no handoff final: {e}")
    
    # =========================================================================
    # 26. AVISO DE FORA DO HORÁRIO
    # =========================================================================
    if is_out_of_hours and is_new:
        final_response += out_of_hours_message
        logger.info(f"⏰ Aviso de fora do horário adicionado para lead NOVO {lead.id}")
    
    # =========================================================================
    # 27. COMMIT E RETORNO
    # =========================================================================
    try:
        await db.commit()
        
        return {
            "success": True,
            "reply": final_response,
            "lead_id": lead.id,
            "is_new_lead": is_new,
            "qualification": lead.qualification,
            "typing_delay": calculate_typing_delay(len(final_response)),
            "sentiment": sentiment.get("sentiment"),
            "is_returning_lead": is_returning_lead,
            "was_blocked": was_blocked,
            "out_of_hours": is_out_of_hours,
            "imovel_portal_codigo": imovel_portal.get("codigo") if imovel_portal else None,
        }
    except Exception as e:
        logger.error(f"Erro no commit: {e}")
        try:
            await db.rollback()
        except:
            pass
        return {
            "success": False,
            "error": "Erro interno",
            "reply": FALLBACK_RESPONSES["error"],
            "lead_id": lead.id,
        }


async def update_lead_data(
    db: AsyncSession,
    lead: Lead,
    tenant: Tenant,
    conversation: list[dict],
) -> None:
    """Extrai dados da conversa e atualiza o lead."""
    try:
        settings = migrate_settings_if_needed(tenant.settings or {})
        ai_context = extract_ai_context(tenant, settings)
        niche_config = get_niche_config(ai_context["niche_id"])
        
        if not niche_config:
            return
        
        extracted = await extract_lead_data(
            conversation=conversation,
            required_fields=niche_config.required_fields,
            optional_fields=niche_config.optional_fields,
        )
        
        if extracted.get("name") and not lead.name:
            lead.name = extracted["name"]
        if extracted.get("phone") and not lead.phone:
            lead.phone = extracted["phone"]
        if extracted.get("email") and not lead.email:
            lead.email = extracted["email"]
        if extracted.get("city") and not lead.city:
            lead.city = extracted["city"]
        
        custom_fields = {k: v for k, v in extracted.items() 
                         if k not in ["name", "phone", "email", "city"] and v is not None}
        if custom_fields:
            lead.custom_data = {**(lead.custom_data or {}), **custom_fields}
        
        qualification_result = await qualify_lead(
            conversation=conversation,
            extracted_data=extracted,
            qualification_rules=niche_config.qualification_rules,
        )
        
        new_qualification = qualification_result.get("qualification", "frio")
        old_qualification = lead.qualification
        
        if new_qualification != old_qualification:
            event = LeadEvent(
                lead_id=lead.id,
                event_type=EventType.QUALIFICATION_CHANGE.value,
                old_value=old_qualification,
                new_value=new_qualification,
                description=qualification_result.get("reason", ""),
            )
            db.add(event)
            lead.qualification = new_qualification
                
    except Exception as e:
        logger.error(f"Erro atualizando dados do lead {lead.id}: {e}")