"""
CASO DE USO: PROCESSAR MENSAGEM - VERSÃO IMOBILIÁRIA SIMPLIFICADA
==================================================================
Versão MINIMALISTA - Confia no GPT-4o-mini para responder naturalmente.
Apenas regras de segurança e dados do imóvel.
"""

import logging
logging.warning("PROCESS_MESSAGE MINIMALISTA CARREGADO")
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
    """Detecta contexto de imóvel (portal) para nichos imobiliários."""
    logger.info(f"🏠 Detectando contexto imobiliário")
    
    codigo_na_mensagem = extrair_codigo_imovel(content)
    
    codigo_salvo = None
    if lead.custom_data and lead.custom_data.get("imovel_portal"):
        codigo_salvo = lead.custom_data["imovel_portal"].get("codigo")
    
    imovel_portal = None
    
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


def detect_hot_lead_signals(content: str) -> bool:
    """Detecta sinais de lead QUENTE na mensagem."""
    import re
    
    content_lower = content.lower()
    
    hot_signals = [
        r"\bquero\s+comprar\b",
        r"\bvou\s+comprar\b",
        r"\bquero\s+fechar\b",
        r"\bvou\s+fechar\b",
        r"\bquero\s+visitar\b",
        r"\btenho.*\bdinheiro\b",
        r"\bdinheiro.*\bvista\b",
        r"\btenho.*\baprovado\b",
        r"\bfinanciamento.*\baprovado\b",
        r"\burgente\b",
        r"\bquando.*\bposso.*\bvisitar\b",
        r"\bquero\s+ir\s+a[ií]\b",
        r"\bendere[çc]o.*\bimobili[aá]ria\b",
    ]
    
    for pattern in hot_signals:
        if re.search(pattern, content_lower):
            logger.info(f"🔥 Sinal quente detectado: '{pattern}'")
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
    should_transfer = False
    
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
    # 19. DETECÇÃO DE LEAD QUENTE
    # =========================================================================
    is_hot_lead = detect_hot_lead_signals(content)
    
    if is_hot_lead and lead.qualification not in ["quente", "hot"]:
        logger.warning(f"🔥 LEAD QUENTE DETECTADO: '{content[:50]}...'")
        
        lead.qualification = "quente"
        
        if lead.name:
            first_name = lead.name.split()[0]
            hot_response = f"Perfeito, {first_name}! Vou te passar pro corretor agora!"
        else:
            hot_response = "Show! Vou te passar pro corretor. Qual seu nome?"
        
        assistant_message = Message(
            lead_id=lead.id,
            role="assistant",
            content=hot_response,
            tokens_used=0
        )
        db.add(assistant_message)
        
        handoff_result = await execute_handoff(lead, tenant, "lead_hot_detected", db)
        
        transfer_message = Message(
            lead_id=lead.id,
            role="assistant",
            content=handoff_result["message_for_lead"],
            tokens_used=0
        )
        db.add(transfer_message)
        
        await db.commit()
        
        logger.info(f"🔥 Lead {lead.id} transferido por sinal quente")
        
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
    # 20. MONTA PROMPT MINIMALISTA
    # =========================================================================
    logger.info(f"🤖 Chamando GPT-4o-mini | Imóvel: {bool(imovel_portal)}")
    
    system_prompt = f"""Você é assistente virtual da {settings['company_name']}, imobiliária em Canoas/RS.

Responda naturalmente as perguntas do cliente sobre imóveis."""

    # Adiciona dados do imóvel se houver
    if imovel_portal:
        system_prompt += f"""

Imóvel código {imovel_portal.get('codigo')}:
- {imovel_portal.get('tipo')} em {imovel_portal.get('regiao')}, Canoas
- {imovel_portal.get('quartos')} quartos, {imovel_portal.get('banheiros')} banheiros, {imovel_portal.get('vagas')} vagas
- {imovel_portal.get('metragem')}m²
- R$ {imovel_portal.get('preco')}"""
    
    # Conhecimento local
    system_prompt += """

Você conhece Canoas:
- Escolas no Centro: La Salle, SESI
- Mercados: Zaffari, Big
- Hospitais: Mãe de Deus

REGRAS DE SEGURANÇA (IMPORTANTE):
- NÃO marque visitas (só corretor pode)
- NÃO negocie valores/descontos
- NÃO dê endereço da imobiliária
- Se cliente quiser visitar/comprar: "Vou passar você pro corretor!"

Seja breve e amigável."""
    
    # ═══════════════════════════════════════════════════════════════
    # ⚠️ CRITICAL FIX: ADICIONA MENSAGEM ATUAL AO HISTÓRICO!
    # ═══════════════════════════════════════════════════════════════
    history.append({"role": "user", "content": content})
    
    messages = [{"role": "system", "content": system_prompt}, *history]

    final_response = ""
    tokens_used = 0

    try:
        ai_response = await chat_completion(
            messages=messages,
            temperature=0.7,
            max_tokens=200,
        )
        
        final_response = ai_response["content"]
        tokens_used = ai_response.get("tokens_used", 0)
        
    except Exception as e:
        logger.error(f"❌ Erro chamando IA: {e}")
        logger.error(traceback.format_exc())
        
        if empreendimento_detectado:
            final_response = f"Olá! Interesse no {empreendimento_detectado.nome}! Como posso ajudar?"
        elif imovel_portal:
            final_response = f"Olá! Vi seu interesse no imóvel {imovel_portal.get('codigo')}! Como posso ajudar?"
        else:
            final_response = f"Olá! Sou da {settings['company_name']}. Como posso ajudar?"

    # =========================================================================
    # 21. VERIFICA HANDOFF SUGERIDO PELA IA
    # =========================================================================
    handoff_check = check_ai_handoff(content, final_response)
    should_transfer_by_ai = handoff_check["should_handoff"]
    
    # =========================================================================
    # 22. SALVA RESPOSTA
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
    # 23. HANDOFF FINAL
    # =========================================================================
    should_transfer = lead.qualification in ["quente", "hot"] or should_transfer_by_ai
    
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
    # 24. AVISO DE FORA DO HORÁRIO
    # =========================================================================
    if is_out_of_hours and is_new:
        final_response += out_of_hours_message
        logger.info(f"⏰ Aviso horário adicionado: {lead.id}")
    
    # =========================================================================
    # 25. COMMIT E RETORNO
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