"""
CASO DE USO: PROCESSAR MENSAGEM - VERSÃO IMOBILIÁRIA SIMPLIFICADA
==================================================================
Versão otimizada SÓ para nicho imobiliário com bugs corrigidos.

CORREÇÕES:
- Bug should_transfer corrigido
- Bug qualification_score removido
- Bug analyze_lead_conversation corrigido
- Bug qualify_lead corrigido
- Prompt enxuto (sem truncar)
"""

import logging
logging.warning("PROCESS_MESSAGE CORRETO CARREGADO")
import traceback

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from src.infrastructure.services.property_lookup_service import (
    buscar_imovel_na_mensagem,
    extrair_codigo_imovel,
)

from src.domain.entities import (
    Tenant, Lead, Message, Channel, LeadEvent, Notification, Empreendimento
)
from src.domain.entities.enums import LeadStatus, EventType


from src.infrastructure.services import (
    extract_lead_data,
    execute_handoff,
    mark_lead_activity,
    check_handoff_triggers,
    check_business_hours,
    notify_lead_empreendimento,
    notify_gestor,
    chat_completion,
)

from src.infrastructure.services.openai_service import (
    detect_sentiment,
    calculate_typing_delay,
    validate_ai_response,
)

from src.infrastructure.services.ai_security import (
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
    log_ai_action,
)
from src.infrastructure.services.lgpd_service import (
    detect_lgpd_request,
    get_lgpd_response,
)



logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES
# =============================================================================

MAX_MESSAGE_LENGTH = 2000
MAX_CONVERSATION_HISTORY = 30

FALLBACK_RESPONSES = {
    "error": "Desculpe, estou com uma instabilidade momentânea. Tente novamente em alguns segundos.",
    "security": "Por segurança, não posso responder a essa mensagem.",
}


# =============================================================================
# HELPERS
# =============================================================================

def sanitize_message_content(content: str) -> str:
    """Remove conteúdo potencialmente perigoso ou muito longo."""
    if not content:
        return ""
    content = content[:MAX_MESSAGE_LENGTH]
    content = content.replace('\0', '').replace('\r', '')
    return content.strip()


def extract_settings(tenant: Tenant) -> dict:
    """Extrai settings do tenant de forma segura."""
    settings = tenant.settings or {}
    
    return {
        "company_name": settings.get("company_name") or settings.get("basic", {}).get("company_name") or tenant.name,
        "tone": settings.get("tone") or settings.get("identity", {}).get("tone_style", {}).get("tone") or "cordial",
        "custom_rules": settings.get("custom_rules") or settings.get("identity", {}).get("business_rules") or [],
        "handoff_triggers": settings.get("handoff_triggers") or settings.get("handoff", {}).get("triggers") or [],
    }


# =============================================================================
# FUNÇÕES DE EMPREENDIMENTO
# =============================================================================

async def detect_empreendimento(
    db: AsyncSession,
    tenant_id: int,
    message: str,
) -> Optional[Empreendimento]:
    """Detecta se a mensagem contém gatilhos de algum empreendimento."""
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
        return result.scalar_one_or_none()
        
    except Exception as e:
        logger.error(f"Erro recuperando empreendimento: {e}")
        return None


def empreendimento_to_dict(emp: Empreendimento) -> dict:
    """Converte Empreendimento para dict."""
    return {
        "id": emp.id,
        "nome": emp.nome,
        "descricao": emp.descricao,
        "endereco": emp.endereco,
        "bairro": emp.bairro,
        "cidade": emp.cidade,
        "estado": emp.estado,
        "tipologias": emp.tipologias,
        "metragem_minima": emp.metragem_minima,
        "metragem_maxima": emp.metragem_maxima,
        "preco_minimo": emp.preco_minimo,
        "preco_maximo": emp.preco_maximo,
        "diferenciais": emp.diferenciais,
        "instrucoes_ia": emp.instrucoes_ia,
        "perguntas_qualificacao": emp.perguntas_qualificacao,
    }


async def update_empreendimento_stats(
    db: AsyncSession,
    empreendimento: Empreendimento,
    is_new_lead: bool = False,
):
    """Atualiza estatísticas do empreendimento."""
    try:
        if is_new_lead:
            empreendimento.total_leads = (empreendimento.total_leads or 0) + 1
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


async def detect_property_context(
    content: str,
    lead: Lead,
    history: list[dict],
) -> Optional[Dict]:
    """
    Detecta contexto de imóvel (portal) para nichos imobiliários.
    Retorna dados do imóvel ou None.
    """
    logger.info(f"🏠 Detectando contexto imobiliário")
    
    # Extrai código da mensagem atual
    codigo_na_mensagem = extrair_codigo_imovel(content)
    
    # Pega código salvo (se houver)
    codigo_salvo = None
    if lead.custom_data and lead.custom_data.get("imovel_portal"):
        codigo_salvo = lead.custom_data["imovel_portal"].get("codigo")
    
    imovel_portal = None
    
    # Decisão: buscar novo ou reutilizar?
    if codigo_na_mensagem:
        if codigo_na_mensagem != codigo_salvo:
            logger.info(f"🆕 Novo código: {codigo_na_mensagem}")
            imovel_portal = buscar_imovel_na_mensagem(content)
        else:
            logger.info(f"🔄 Reutilizando código: {codigo_salvo}")
            imovel_portal = lead.custom_data.get("imovel_portal")
    
    elif codigo_salvo:
        logger.info(f"🔄 Usando salvo: {codigo_salvo}")
        imovel_portal = lead.custom_data.get("imovel_portal")
    
    else:
        logger.info(f"🕰️ Buscando no histórico")
        for msg in reversed(history):
            if msg.get("role") == "user":
                imovel_portal = buscar_imovel_na_mensagem(msg.get("content", ""))
                if imovel_portal:
                    logger.info(f"✅ Encontrado no histórico: {imovel_portal.get('codigo')}")
                    break
    
    # Salva no lead se encontrou
    if imovel_portal:
        logger.info(f"💾 Salvando imóvel: {imovel_portal.get('codigo')}")
        
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
        flag_modified(lead, "custom_data")
    
    return imovel_portal


def build_lead_context_dict(lead: Lead, message_count: int) -> dict:
    """Constrói dicionário de contexto do lead."""
    context = {
        "message_count": message_count,
    }
    
    if lead.name:
        context["name"] = lead.name
    
    if lead.phone:
        context["phone"] = lead.phone
    
    if lead.custom_data:
        for key in ["urgency_level", "budget_range", "preferences", "empreendimento_nome"]:
            if key in lead.custom_data:
                context[key] = lead.custom_data[key]
    
    return context

def detect_hot_lead_signals(content: str) -> bool:
    """
    Detecta sinais de lead QUENTE na mensagem.
    Versão MELHORADA com regex simplificada.
    """
    import re
    
    content_lower = content.lower()
    
    hot_signals = [
        # INTENÇÃO DE COMPRA (SIMPLIFICADO)
        r"\bquero\s+comprar\b",
        r"\bvou\s+comprar\b",
        r"\bquero\s+fechar\b",
        r"\bvou\s+fechar\b",
        r"\bquero\s+esse\b",
        r"\bquero\s+essa\b",
        r"\bquero\s+visitar\b",
        r"\bgostei\s+desse\b",
        r"\bgostei\s+dessa\b",
        r"\bme\s+interessei\b",
        
        # DINHEIRO À VISTA
        r"\btenho.*\bdinheiro\b",
        r"\btenho.*\bvalor\b.*\bvista\b",
        r"\bdinheiro.*\bvista\b",
        r"\bpagamento.*\bvista\b",
        r"\bpagar.*\bvista\b",
        r"\btenho\s+\d+\s*mil\b",  # "tenho 50 mil"
        
        # CRÉDITO/FINANCIAMENTO APROVADO
        r"\btenho.*\baprovado\b",
        r"\bfinanciamento.*\baprovado\b",
        r"\bcredito.*\baprovado\b",
        r"\bja.*\baprovado\b",
        r"\bpre.*\baprovado\b",
        
        # URGÊNCIA TEMPORAL
        r"\bmais\s+rapido\b",
        r"\bo\s+mais\s+rapido\b",
        r"\brapido\s+possivel\b",
        r"\bmais\s+rapido\s+possivel\b",
        r"\bpreciso.*\bmudar\b",
        r"\bpreciso.*\burgente\b",
        r"\burgente\b",
        r"\bpreciso.*\brapido\b",
        r"\bpreciso.*\bhoje\b",
        r"\bpreciso.*\bagora\b",
        r"\bpara.*\bontem\b",
        r"\bcom\s+urgencia\b",
        
        # PERGUNTAS DE DECISÃO
        r"\bquando.*\bposso.*\bvisitar\b",
        r"\bquando.*\bpodemos.*\bver\b",
        r"\bposso.*\bir.*\bhoje\b",
        r"\bposso.*\bver.*\bagora\b",
        r"\bquais.*\bdocumentos\b",
        r"\bquando.*\bpodemos.*\bfechar\b",
        
        # SINAIS DE ENTRADA/FINANCIAMENTO
        r"\btenho.*\bentrada\b",
        r"\btenho\s+entrada\b",
        r"\bquero\s+ir\s+a[ií]\b",
        r"\bendere[çc]o.*\bimobili[aá]ria\b",
        r"\bquero.*\bpresencial\b",
        r"\bposso.*\bir.*\ba[ií]\b",
        r"\bvisita.*\bpresencial\b",
    ]
    
    for pattern in hot_signals:
        if re.search(pattern, content_lower):
            logger.info(f"🔥 Sinal quente detectado: '{pattern}' em '{content[:50]}...'")
            return True
    
    return False

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
    
    # =========================================================================
    # INICIALIZAÇÃO DE VARIÁVEIS
    # =========================================================================
    empreendimento_detectado: Optional[Empreendimento] = None
    imovel_portal: Optional[Dict] = None
    gestor_ja_notificado = False
    history: list[dict] = []
    message_count: int = 0
    should_transfer = False  # ← CORREÇÃO BUG #1: Inicializa ANTES de usar
    
    # =========================================================================
    # 1. SANITIZAÇÃO
    # =========================================================================
    content = sanitize_message_content(content)
    if not content or len(content.strip()) < 1:
        return {
            "success": False,
            "error": "Mensagem vazia",
            "reply": FALLBACK_RESPONSES["error"]
        }
    
    logger.info(f"📥 Processando: {tenant_slug} | {sender_phone or external_id}")
    
    # =========================================================================
    # 2. RATE LIMITING
    # =========================================================================
    rate_limit_result = await check_message_rate_limit(
        phone=sender_phone or external_id,
        tenant_id=None,
    )
    if not rate_limit_result.allowed:
        logger.warning(f"⚠️ Rate limit: {sender_phone or external_id}")
        return {
            "success": True,
            "reply": get_rate_limit_response(),
            "lead_id": None,
            "is_new_lead": False,
            "blocked_reason": "rate_limit",
        }
    
    # =========================================================================
    # 3. SECURITY CHECK
    # =========================================================================
    security_result = run_security_check(
        content=content,
        sender_id=sender_phone or external_id,
        tenant_id=None,
    )
    if not security_result.is_safe and security_result.should_block:
        logger.warning(f"🚨 Bloqueado: {security_result.threat_type}")
        return {
            "success": True,
            "reply": get_safe_response_for_threat(security_result.threat_type),
            "lead_id": None,
            "is_new_lead": False,
            "security_blocked": True,
        }
    content = security_result.sanitized_content
    
    # =========================================================================
    # 4. BUSCA TENANT E CANAL
    # =========================================================================
    result = await db.execute(
        select(Tenant).where(Tenant.slug == tenant_slug).where(Tenant.active == True)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        logger.error(f"❌ Tenant não encontrado: {tenant_slug}")
        return {
            "success": False,
            "error": "Tenant não encontrado",
            "reply": FALLBACK_RESPONSES["error"]
        }
    
    result = await db.execute(
        select(Channel)
        .where(Channel.tenant_id == tenant.id)
        .where(Channel.type == channel_type)
        .where(Channel.active == True)
    )
    channel = result.scalar_one_or_none()
    
    # =========================================================================
    # 5. VERIFICAÇÃO DE HORÁRIO COMERCIAL
    # =========================================================================
    is_out_of_hours = False
    out_of_hours_message = ""
    
    bh_result = check_business_hours(tenant)
    if not bh_result.is_open:
        is_out_of_hours = True
        logger.info(f"⏰ Fora do horário: {bh_result.reason}")
        out_of_hours_message = (
            "\n\n---\n"
            "⏰ *Você está entrando em contato fora do nosso horário comercial.*\n"
            "Mas fique tranquilo! Já registramos seu contato e um especialista "
            "entrará em contato com você o mais breve possível! 🙌"
        )
    
    # =========================================================================
    # 6. EXTRAI SETTINGS
    # =========================================================================
    settings = extract_settings(tenant)
    
    logger.info(f"🔧 Tenant: {settings['company_name']}")
    
    # =========================================================================
    # 7. BUSCA/CRIA LEAD
    # =========================================================================
    lead, is_new = await get_or_create_lead(
        db=db, tenant=tenant, channel=channel, external_id=external_id,
        sender_name=sender_name, sender_phone=sender_phone,
        source=source, campaign=campaign,
    )
    
    await log_message_received(
        db=db, tenant_id=tenant.id, lead_id=lead.id,
        content_preview=content[:100], channel=channel_type,
    )
    
    logger.info(f"👤 Lead {'✨ NOVO' if is_new else '🔄 existente'}: {lead.id}")
    
    # =========================================================================
    # 8. PRÉ-CARREGA HISTÓRICO E CONTAGEM
    # =========================================================================
    history = await get_conversation_history(db, lead.id)
    message_count = await count_lead_messages(db, lead.id)
    
    logger.info(f"📊 Lead {lead.id}: {message_count} mensagens no histórico")
        
    # =========================================================================
    # 9. DETECÇÃO DE EMPREENDIMENTO
    # =========================================================================
    empreendimento_detectado = await detect_empreendimento(
        db=db,
        tenant_id=tenant.id,
        message=content,
    )
    
    if not empreendimento_detectado and not is_new:
        empreendimento_detectado = await get_empreendimento_from_lead(db, lead)
    
    if empreendimento_detectado:
        logger.info(f"🏢 Empreendimento: {empreendimento_detectado.nome}")
        
        if not lead.custom_data:
            lead.custom_data = {}
        
        old_emp_id = lead.custom_data.get("empreendimento_id")
        if old_emp_id != empreendimento_detectado.id:
            lead.custom_data["empreendimento_id"] = empreendimento_detectado.id
            lead.custom_data["empreendimento_nome"] = empreendimento_detectado.nome
            flag_modified(lead, "custom_data")
        
        if is_new:
            await update_empreendimento_stats(db, empreendimento_detectado, is_new_lead=True)
            
            if empreendimento_detectado.vendedor_id:
                lead.assigned_seller_id = empreendimento_detectado.vendedor_id
                lead.assignment_method = "empreendimento"
                lead.assigned_at = datetime.now(timezone.utc)
    
    # =========================================================================
    # 10. NOTIFICAÇÃO ESPECÍFICA DE EMPREENDIMENTO
    # =========================================================================
    if (empreendimento_detectado and 
        empreendimento_detectado.notificar_gestor and 
        is_new and 
        not gestor_ja_notificado):
        await notify_lead_empreendimento(db, tenant, lead, empreendimento_detectado)
        gestor_ja_notificado = True
        logger.info(f"📲 Notificação empreendimento: {empreendimento_detectado.nome}")
    
    # =========================================================================
    # 11. LGPD CHECK
    # =========================================================================
    lgpd_request = detect_lgpd_request(content)
    if lgpd_request:
        logger.info(f"🔒 LGPD request: {lgpd_request}")
        
        user_message = Message(lead_id=lead.id, role="user", content=content, tokens_used=0)
        db.add(user_message)
        
        lgpd_reply = get_lgpd_response(lgpd_request, tenant_name=settings["company_name"])
        
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
    
    # =========================================================================
    # 12. STATUS CHECK (lead já transferido)
    # =========================================================================
    if lead.status == LeadStatus.HANDED_OFF.value or lead.handed_off_at is not None:
        logger.warning(f"⚠️ Lead {lead.id} já foi transferido! Ignorando mensagem.")
        
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
    # 13. DETECÇÃO DE CONTEXTO IMOBILIÁRIO (PORTAL)
    # =========================================================================
    imovel_portal = await detect_property_context(
        content=content,
        lead=lead,
        history=history,
    )
    
    if imovel_portal:
        logger.info(f"🏠 Imóvel portal: {imovel_portal.get('codigo')}")
    
    # =========================================================================
    # 14. HANDOFF TRIGGERS
    # =========================================================================
    trigger_found, trigger_matched = check_handoff_triggers(
        message=content,
        custom_triggers=settings["handoff_triggers"],
    )
    
    if trigger_found:
        logger.info(f"🔔 Handoff trigger: {trigger_matched}")
        
        user_message = Message(lead_id=lead.id, role="user", content=content, tokens_used=0)
        db.add(user_message)
        await db.flush()
        
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
    
    # =========================================================================
    # 15. ATUALIZA STATUS
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
    # 16. SALVA MENSAGEM DO USUÁRIO
    # =========================================================================
    user_message = Message(lead_id=lead.id, role="user", content=content, tokens_used=0)
    db.add(user_message)
    await db.flush()

    await mark_lead_activity(db, lead)
    
    # =========================================================================
    # 17. NOTIFICAÇÃO DE LEAD NOVO
    # =========================================================================
    if is_new and not gestor_ja_notificado:
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
        logger.info(f"📲 Gestor notificado: lead NOVO {lead.id}")

    # =========================================================================
    # 18. DETECÇÃO DE SENTIMENTO
    # =========================================================================
    sentiment = await detect_sentiment(content)
    
    # =========================================================================
    # 19. PRÉ-VALIDAÇÃO: DETECTA LEAD QUENTE ANTES DE RESPONDER
    # =========================================================================
    is_hot_lead = detect_hot_lead_signals(content)
    
    if is_hot_lead and lead.qualification not in ["quente", "hot"]:
        logger.warning(f"🔥 LEAD QUENTE DETECTADO na mensagem: '{content[:50]}...'")
        
        # Força qualificação
        lead.qualification = "quente"
        
        # Responde e faz handoff IMEDIATAMENTE
        if lead.name:
            first_name = lead.name.split()[0]
            hot_response = f"Perfeito, {first_name}! Você está pronto. Vou te passar pro corretor agora!"
        else:
            hot_response = "Show! Você tá pronto. Qual seu nome pra eu passar pro corretor?"
        
        # Salva resposta
        assistant_message = Message(
            lead_id=lead.id,
            role="assistant",
            content=hot_response,
            tokens_used=0
        )
        db.add(assistant_message)
        
        # Executa handoff
        handoff_result = await execute_handoff(lead, tenant, "lead_hot_detected", db)
        
        transfer_message = Message(
            lead_id=lead.id,
            role="assistant",
            content=handoff_result["message_for_lead"],
            tokens_used=0
        )
        db.add(transfer_message)
        
        await db.commit()
        
        logger.info(f"🔥 Lead {lead.id} transferido por detecção automática de sinal quente")
        
        return {
            "success": True,
            "reply": hot_response + "\n\n" + handoff_result["message_for_lead"],
            "lead_id": lead.id,
            "is_new_lead": is_new,
            "qualification": "quente",
            "status": "transferido",
            "hot_signal_detected": True,
        }
    
    # =========================================================================
    # 20. MONTA PROMPT (USANDO PROMPT IMOBILIÁRIA ENXUTO)
    # =========================================================================
    logger.info(f"🔨 Montando prompt | Emp: {bool(empreendimento_detectado)} | Imóvel: {bool(imovel_portal)}")

    # Contexto do lead
    lead_context = build_lead_context_dict(lead, message_count)

    # Converte empreendimento para dict
    emp_dict = None
    if empreendimento_detectado:
        emp_dict = empreendimento_to_dict(empreendimento_detectado)

    # ═══════════════════════════════════════════════════════════════
    # MONTA PROMPT INLINE - IA QUALIFICADORA IMOBILIÁRIA
    # ═══════════════════════════════════════════════════════════════
    
    # Seção de dados do imóvel
    imovel_section = ""
    if imovel_portal:
        imovel_section = f"""
═══════════════════════════════════════════════════════════════
📍 IMÓVEL DISPONÍVEL - CÓDIGO {imovel_portal.get('codigo', 'N/A')}
═══════════════════════════════════════════════════════════════

{imovel_portal.get('tipo', 'Imóvel')} em {imovel_portal.get('regiao', 'N/A')}, Canoas
- {imovel_portal.get('quartos', 'N/A')} quartos
- {imovel_portal.get('banheiros', 'N/A')} banheiros
- {imovel_portal.get('vagas', 'N/A')} vagas de garagem
- {imovel_portal.get('metragem', 'N/A')}m²
- Valor: {imovel_portal.get('preco', 'Consulte')}

USE esses dados para responder perguntas sobre o imóvel!
"""
    
    # Seção de histórico
    historico_section = ""
    if history and len(history) >= 2:
        historico_section = "\n═══════════════════════════════════════════════════════════════\n"
        historico_section += "📜 HISTÓRICO DA CONVERSA (LEIA ANTES DE RESPONDER!):\n"
        historico_section += "═══════════════════════════════════════════════════════════════\n\n"
        for msg in history[-5:]:
            role = "👤 Cliente" if msg.get('role') == 'user' else "🤖 Você"
            content = msg.get('content', '')[:100]
            historico_section += f"{role}: {content}\n"
        historico_section += "\n⚠️ NÃO REPITA informações já ditas! Avance na conversa!\n"
    
    system_prompt = f"""Você é {settings['company_name']} no WhatsApp.

    ═══════════════════════════════════════════════════════════════
    ⚠️ LEIA ANTES DE RESPONDER!
    ═══════════════════════════════════════════════════════════════

    1. **LEIA A PERGUNTA DO CLIENTE**
    - Cliente perguntou ESCOLA? → Responda ESCOLA
    - Cliente perguntou VAGA? → Responda VAGA
    - Cliente perguntou PREÇO? → Responda PREÇO
    - NUNCA responda algo que NÃO foi perguntado!

    2. **MÁXIMO 1 LINHA (máx 50 caracteres)**
    - Seja DIRETA
    - Responda SÓ o perguntado
    - 0-1 emoji

    3. **LEIA O HISTÓRICO**
    - Se JÁ respondeu, diga: "Como disse, [resposta]"
    - NUNCA dê a mesma resposta 2x

    ═══════════════════════════════════════════════════════════════
    📍 DADOS DO IMÓVEL (use quando perguntarem)
    ═══════════════════════════════════════════════════════════════

    Código 442025 - Casa no Centro, Canoas
    - 3 quartos
    - 2 banheiros  
    - 2 vagas
    - 108m²
    - R$ 680.000

    ═══════════════════════════════════════════════════════════════
    {historico_section}
    ═══════════════════════════════════════════════════════════════

    🧠 VOCÊ CONHECE CANOAS:
    - Escolas: La Salle, SESI
    - Mercados: Zaffari, Big
    - Centro: muito comércio

    ═══════════════════════════════════════════════════════════════
    ✅ EXEMPLOS CORRETOS
    ═══════════════════════════════════════════════════════════════

    Cliente: "tem vaga?"
    Você: "Tem! 2 vagas."

    Cliente: "tem escola?"
    Você: "Sim! La Salle e SESI próximos."

    Cliente: "quanto custa?"
    Você: "R$ 680.000."

    ═══════════════════════════════════════════════════════════════
    ❌ NUNCA FAÇA
    ═══════════════════════════════════════════════════════════════

    ❌ Responder tudo de uma vez: "3 quartos, 2 banheiros..."
    ❌ Responder coisa não perguntada
    ❌ Repetir informação
    ❌ Dizer "fazendo busca"

    ═══════════════════════════════════════════════════════════════
    🔥 TRANSFERIR SE DISSER:
    ═══════════════════════════════════════════════════════════════

    - "Quero visitar"
    - "Quero ir aí"
    - "Tenho dinheiro"
    - "Endereço da imobiliária"

    → "Perfeito! Te passo pro corretor!"

    ═══════════════════════════════════════════════════════════════
    """
    
    logger.info(f"📝 Prompt inline: {len(system_prompt)} chars")


    # =========================================================================
    # 21. PREPARA MENSAGENS E CHAMA IA
    # =========================================================================
    messages = [{"role": "system", "content": system_prompt}, *history]

    final_response = ""
    tokens_used = 0

    try:
        ai_response = await chat_completion(
        messages=messages,
        temperature=0.4,  # ← Aumenta um pouco
        max_tokens=120,   # ← Aumenta um pouco
    )
        
        ai_response_raw = ai_response["content"]
        
        # ═══════════════════════════════════════════════════════════════
        # PÓS-PROCESSAMENTO: TRUNCA E LIMPA
        # ═══════════════════════════════════════════════════════════════
        
        # 1. Trunca se muito longo (máx 2 linhas)
        lines = ai_response_raw.split('\n')
        if len(lines) > 2:
            ai_response_raw = '\n'.join(lines[:2])
            logger.warning(f"⚠️ Resposta truncada de {len(lines)} para 2 linhas")
        
        # 2. Remove menções a "busca/pesquisa"
        if 'fazendo uma busca' in ai_response_raw.lower() or 'pesquisando' in ai_response_raw.lower():
            ai_response_raw = ai_response_raw.replace('Fazendo uma busca específica', 'Pelo que sei')
            ai_response_raw = ai_response_raw.replace('fazendo uma busca', 'verificando')
            ai_response_raw = ai_response_raw.replace('pesquisando', 'checando')
            ai_response_raw = ai_response_raw.replace('Pesquisei', 'Verifiquei')
            logger.warning(f"⚠️ Menção a 'busca' removida")
        
        # 3. Valida resposta
        final_response, was_corrected = validate_ai_response(
            response=ai_response_raw,
            lead_name=lead.name,
            lead_phone=lead.phone,
            history=history
        )
        
        # ═══════════════════════════════════════════════════════════════
        # 4. ANTI-REPETIÇÃO: VERIFICA SE JÁ DISSE ISSO ANTES
        # ═══════════════════════════════════════════════════════════════
        
        if history:
            # Pega últimas 3 mensagens da IA
            assistant_messages = [msg.get("content", "") for msg in history[-6:] if msg.get("role") == "assistant"]
            
            # Verifica se a resposta atual é muito similar às anteriores
            for prev_msg in assistant_messages:
                # Se mais de 50% do conteúdo é igual, é repetição
                if len(final_response) > 20 and len(prev_msg) > 20:
                    # Remove pontuação e espaços para comparar
                    import re
                    clean_final = re.sub(r'[^\w\s]', '', final_response.lower())
                    clean_prev = re.sub(r'[^\w\s]', '', prev_msg.lower())
                    
                    # Conta palavras em comum
                    words_final = set(clean_final.split())
                    words_prev = set(clean_prev.split())
                    
                    if words_final and words_prev:
                        common_words = words_final.intersection(words_prev)
                        similarity = len(common_words) / len(words_final)
                        
                        if similarity > 0.6:  # Mais de 60% igual
                            logger.warning(f"⚠️ REPETIÇÃO DETECTADA! Similaridade: {similarity:.0%}")
                            
                            # Pega a última mensagem do cliente
                            last_user_msg = ""
                            for msg in reversed(history):
                                if msg.get("role") == "user":
                                    last_user_msg = msg.get("content", "")
                                    break
                            
                            # Regenera resposta com prompt anti-repetição
                            retry_prompt = f"""ATENÇÃO: Você ACABOU DE REPETIR informação!

Mensagem anterior sua: "{prev_msg}"

Pergunta do cliente AGORA: "{last_user_msg}"

RESPONDA DIFERENTE! Seja DIRETA e responda SÓ o que foi perguntado!
NÃO REPITA O QUE JÁ DISSE!

Resposta:"""
                            
                            # Adiciona ao contexto e tenta de novo
                            retry_messages = messages + [
                                {"role": "assistant", "content": final_response},
                                {"role": "user", "content": retry_prompt}
                            ]
                            
                            try:
                                retry_response = await chat_completion(
                                    messages=retry_messages,
                                    temperature=0.3,
                                    max_tokens=100,
                                )
                                
                                final_response = retry_response["content"].strip()
                                logger.info(f"✅ Resposta regenerada: '{final_response}'")
                                break
                                
                            except Exception as e:
                                logger.error(f"❌ Erro ao regenerar: {e}")
                                # Mantém resposta original se falhar
        
        if was_corrected:
            logger.warning(f"🔧 Resposta da IA foi corrigida - Lead {lead.id}")
        
        tokens_used = ai_response.get("tokens_used", 0)
        
    except Exception as e:
        logger.error(f"❌ Erro chamando IA: {e}")
        logger.error(traceback.format_exc())
        
        if empreendimento_detectado:
            final_response = f"Olá! Que bom seu interesse no {empreendimento_detectado.nome}! Como posso ajudar?"
        elif imovel_portal:
            final_response = f"Olá! Vi seu interesse no imóvel {imovel_portal.get('codigo')}! Como posso ajudar?"
        else:
            final_response = f"Olá! Sou da {settings['company_name']}. Como posso ajudar?"



    # =========================================================================
    # 22. VERIFICA HANDOFF SUGERIDO PELA IA
    # =========================================================================
    handoff_check = check_ai_handoff(content, final_response)
    should_transfer_by_ai = handoff_check["should_handoff"]
    
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
            "empreendimento_id": empreendimento_detectado.id if empreendimento_detectado else None,
            "imovel_portal_codigo": imovel_portal.get("codigo") if imovel_portal else None,
        },
    )

    # =========================================================================
    # 24. HANDOFF FINAL
    # =========================================================================
    should_transfer = lead.qualification in ["quente", "hot"] or should_transfer_by_ai  # ← BUG CORRIGIDO
    
    if should_transfer:
        handoff_reason = "lead_hot" if lead.qualification in ["quente", "hot"] else "ai_suggested"
        
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
    
    # =========================================================================
    # 25. AVISO DE FORA DO HORÁRIO
    # =========================================================================
    if is_out_of_hours and is_new:
        final_response += out_of_hours_message
        logger.info(f"⏰ Aviso horário adicionado: {lead.id}")
    
    # =========================================================================
    # 26. COMMIT E RETORNO
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
            "out_of_hours": is_out_of_hours,
            "imovel_portal_codigo": imovel_portal.get("codigo") if imovel_portal else None,
        }
    except Exception as e:
        logger.error(f"❌ Erro no commit: {e}")
        logger.error(traceback.format_exc())
        await db.rollback()
        return {
            "success": False,
            "error": "Erro interno",
            "reply": FALLBACK_RESPONSES["error"],
            "lead_id": lead.id,
        }