"""
CASO DE USO: PROCESSAR MENSAGEM (VERSÃO REFATORADA)
====================================================
Versão otimizada com correções de bugs e melhor organização.
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
    extrair_codigo_imovel,
)

from src.domain.entities import (
    Tenant, Lead, Message, Channel, LeadEvent, Notification, Empreendimento
)
from src.domain.services.lead_qualifier import qualify_lead
from src.domain.services.lead_intelligence import analyze_lead_conversation
from src.domain.entities.enums import LeadStatus, EventType
from src.domain.prompts import build_system_prompt, get_niche_config
from src.infrastructure.services import (
    extract_lead_data,
    execute_handoff,
    run_ai_guards_async,
    mark_lead_activity,
    check_handoff_triggers,
    check_business_hours,
    notify_lead_empreendimento,
    notify_out_of_hours,
    notify_handoff_requested,
    notify_gestor,
    chat_completion,
)

from src.infrastructure.services.openai_service import (
    detect_sentiment,
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


async def detect_property_context(
    content: str,
    lead: Lead,
    history: list[dict],
    niche_id: str,
) -> Optional[Dict]:
    """
    Detecta contexto de imóvel (portal) para nichos imobiliários.
    Retorna dados do imóvel ou None.
    """
    if niche_id.lower() not in NICHOS_IMOBILIARIOS:
        return None
    
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
            # Código DIFERENTE - busca novo
            logger.info(f"🆕 Novo código: {codigo_na_mensagem}")
            imovel_portal = buscar_imovel_na_mensagem(content)
        else:
            # MESMO código - reutiliza
            logger.info(f"🔄 Reutilizando código: {codigo_salvo}")
            imovel_portal = lead.custom_data.get("imovel_portal")
    
    elif codigo_salvo:
        # Reutiliza salvo
        logger.info(f"🔄 Usando salvo: {codigo_salvo}")
        imovel_portal = lead.custom_data.get("imovel_portal")
    
    else:
        # Busca no histórico
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


def build_property_prompt_context(imovel: Dict, content: str) -> str:
    """Constrói contexto do imóvel para o prompt."""
    cod = imovel.get('codigo', 'N/A')
    quartos = imovel.get('quartos', 'N/A')
    banheiros = imovel.get('banheiros', 'N/A')
    vagas = imovel.get('vagas', 'N/A')
    metragem = imovel.get('metragem', 'N/A')
    preco = imovel.get('preco', 'Consulte')
    regiao = imovel.get('regiao', 'N/A')
    tipo = imovel.get('tipo', 'Imóvel')
    descricao = imovel.get('descricao', '')
    
    return f"""

═══════════════════════════════════════════════════════════
🏠 CONTEXTO DO IMÓVEL (código {cod})
═══════════════════════════════════════════════════════════

DADOS DISPONÍVEIS:
Tipo: {tipo}
Localização: {regiao}
Quartos: {quartos}
Banheiros: {banheiros}
Vagas: {vagas}
Área: {metragem} m²
Preço: {preco}
Descrição: {descricao[:300] if descricao else 'N/A'}

═══════════════════════════════════════════════════════════
⚠️ ESTILO DE CONVERSA - WHATSAPP CASUAL
═══════════════════════════════════════════════════════════

🚫 PROIBIDO (parece robô):
❌ Listas com bullet points (-, *, •)
❌ Formatação markdown (**, __, ##)
❌ Tom formal/corporativo
❌ Ficha técnica completa
❌ Respostas longas (mais de 4 linhas)

✅ OBRIGATÓRIO (parece humano):
✅ Conversa natural de WhatsApp
✅ Máximo 3-4 linhas
✅ Tom casual e amigável
✅ Dar informação + fazer pergunta
✅ Usar emoji com moderação (1 por mensagem)

EXEMPLO CERTO:
"Opa! Essa casa é show! Tem {quartos} quartos, {banheiros} banheiros, {metragem}m² em {regiao} por {preco}. Você tá buscando pra morar ou investir?"

═══════════════════════════════════════════════════════════
COMO RESPONDER CADA TIPO DE PERGUNTA
═══════════════════════════════════════════════════════════

Cliente: "Me passa mais detalhes"
✅ "Claro! É {tipo} com {quartos} quartos em {regiao} por {preco}. Tem {metragem}m² com {vagas} vaga(s). Esse orçamento funciona pra você?"

Cliente: "Quanto custa?"
✅ "O valor é {preco}! Cabe no seu orçamento?"

Cliente: "Onde fica?"
✅ "Fica em {regiao}! Você conhece a região?"

REGRAS DE OURO:
1. SEMPRE responda em 2-4 LINHAS
2. SEMPRE termine com PERGUNTA de qualificação
3. NUNCA use formatação markdown
4. NUNCA faça listas
5. Seja DIRETO e OBJETIVO
"""


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
    # INICIALIZAÇÃO DE VARIÁVEIS (EVITA UNDEFINED)
    # =========================================================================
    empreendimento_detectado: Optional[Empreendimento] = None
    imovel_portal: Optional[Dict] = None
    gestor_ja_notificado = False
    history: list[dict] = []
    message_count: int = 0
    
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
    # 6. EXTRAI CONTEXTO E SETTINGS
    # =========================================================================
    settings = migrate_settings_if_needed(tenant.settings or {})
    ai_context = extract_ai_context(tenant, settings)
    
    logger.info(f"🔧 Contexto: {ai_context['company_name']} | Nicho: {ai_context['niche_id']}")
    
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
    # 7.5 PRÉ-CARREGA HISTÓRICO E CONTAGEM (ANTES DE USAR)
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
        niche_id=ai_context["niche_id"],
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
        
        if empreendimento_detectado.perguntas_qualificacao:
            ai_context["custom_questions"] = (
                ai_context.get("custom_questions", []) + 
                empreendimento_detectado.perguntas_qualificacao
            )
    
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
    # 13. DETECÇÃO DE CONTEXTO IMOBILIÁRIO (PORTAL)
    # =========================================================================
    imovel_portal = await detect_property_context(
        content=content,
        lead=lead,
        history=history,
        niche_id=ai_context["niche_id"],
    )
    
    if imovel_portal:
        logger.info(f"🏠 Imóvel portal: {imovel_portal.get('codigo')}")
    
    # =========================================================================
    # 14. AI GUARDS
    # =========================================================================
    guards_result = {"can_respond": True}
    
    # Nicho imobiliário bypassa guards
    if ai_context["niche_id"].lower() in NICHOS_IMOBILIARIOS:
        logger.info("🟢 Guards desabilitados (nicho imobiliário)")
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
    
    # =========================================================================
    # 15. HANDOFF TRIGGERS
    # =========================================================================
    handoff_triggers = settings.get("handoff", {}).get("triggers", []) or settings.get("handoff_triggers", [])
    trigger_found, trigger_matched = check_handoff_triggers(
        message=content,
        custom_triggers=handoff_triggers,
    )
    
    if trigger_found:
        logger.info(f"🔔 Handoff trigger: {trigger_matched}")
        
        user_message = Message(lead_id=lead.id, role="user", content=content, tokens_used=0)
        db.add(user_message)
        await db.flush()
        
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
    # 17. SALVA MENSAGEM DO USUÁRIO E ATUALIZA HISTÓRICO
    # =========================================================================
    user_message = Message(lead_id=lead.id, role="user", content=content, tokens_used=0)
    db.add(user_message)
    await db.flush()  # ← CRÍTICO: flush antes de qualificar!

    await mark_lead_activity(db, lead)

    # =========================================================================
    # 17.5 QUALIFICAÇÃO DO LEAD ← MOVER PRA CÁ!
    # =========================================================================
    try:
        logger.info(f"🎯 Qualificando lead {lead.id}...")
        
        # Busca mensagens para qualificação
        result_msgs = await db.execute(
            select(Message)
            .where(Message.lead_id == lead.id)
            .order_by(Message.created_at.asc())
        )
        all_messages = result_msgs.scalars().all()
        
        # Chama qualificador
        qualification_result = qualify_lead(
            lead=lead,
            messages=all_messages,
            conversation_text=None  # Vai construir do messages
        )
        
        # Salva resultado
        old_qualification = lead.qualification
        lead.qualification = qualification_result["qualification"]
        lead.qualification_score = qualification_result["score"]
        lead.qualification_confidence = qualification_result["confidence"]
        
        # Atualiza custom_data com razões
        if not lead.custom_data:
            lead.custom_data = {}
        lead.custom_data["qualification_reasons"] = qualification_result["reasons"]
        lead.custom_data["qualification_signals"] = qualification_result["signals"]
        flag_modified(lead, "custom_data")
        
        logger.info(
            f"✅ Lead {lead.id} qualificado: {qualification_result['qualification'].upper()} "
            f"(score: {qualification_result['score']}, confiança: {qualification_result['confidence']})"
        )
        
        # Log de mudança de qualificação
        if old_qualification != lead.qualification:
            event = LeadEvent(
                lead_id=lead.id,
                event_type=EventType.QUALIFICATION_CHANGE.value,
                old_value=old_qualification,
                new_value=lead.qualification,
                description=f"Qualificação alterada: {old_qualification} → {lead.qualification}"
            )
            db.add(event)
            logger.info(f"📊 Qualificação mudou: {old_qualification} → {lead.qualification}")
        
        # ═════════════════════════════════════════════════════════════
        # GERA RESUMO ESTRUTURADO PARA LEADS QUENTE/MORNO
        # ═════════════════════════════════════════════════════════════
        if lead.qualification in ["hot", "quente", "warm", "morno"]:
            try:
                logger.info(f"📋 Gerando resumo estruturado para lead {lead.qualification}...")
                
                # Monta conversação para o resumo
                conversation_text = "\n".join([
                    f"{'Cliente' if msg.role == 'user' else 'IA'}: {msg.content}"
                    for msg in all_messages[-20:]  # Últimas 20 mensagens
                ])
                
                # Informações extras do lead
                lead_info = []
                if lead.name:
                    lead_info.append(f"Nome: {lead.name}")
                if lead.phone:
                    lead_info.append(f"Telefone: {lead.phone}")
                if lead.custom_data:
                    if lead.custom_data.get("empreendimento_nome"):
                        lead_info.append(f"Empreendimento: {lead.custom_data['empreendimento_nome']}")
                
                lead_info_text = "\n".join(lead_info) if lead_info else "Sem informações adicionais"
                
                # Prompt para gerar resumo
                summary_prompt = f"""Analise esta conversa e crie um RESUMO ESTRUTURADO para o corretor.

INFORMAÇÕES DO LEAD:
{lead_info_text}

CONVERSAÇÃO:
{conversation_text}

CRIE UM RESUMO NO FORMATO ABAIXO (seja direto e conciso):

👤 PERFIL:
- Nome: [nome do lead ou "Não informado"]
- Contato: [telefone]
- Finalidade: [morar/investir/alugar ou "A definir"]

🎯 O QUE BUSCA:
- Tipo: [casa/apto/terreno/comercial ou "A definir"]
- Região: [onde procura ou "A definir"]
- Características: [quartos, tamanho, etc se mencionou]

⏰ URGÊNCIA:
- Prazo: [quando precisa ou "Não especificado"]
- Motivo: [por que tem urgência, se mencionou]

💰 SITUAÇÃO:
- Financiamento: [aprovado/em análise/não tem/não mencionou]
- Observações: [qualquer info sobre orçamento SE o cliente mencionou]

🔥 POR QUE É {lead.qualification.upper()}:
[1-2 frases explicando os principais sinais]

❗ OBSERVAÇÕES:
[Dúvidas, objeções ou preferências importantes]

REGRAS:
- Máximo 15 linhas no total
- Use "A definir" ou "Não informado" se não tiver a info
- Seja direto e objetivo
- Foque no que é RELEVANTE para o corretor
"""
                
                # Chama IA para gerar resumo
                summary_response = await chat_completion(
                    messages=[{"role": "user", "content": summary_prompt}],
                    temperature=0.3,
                    max_tokens=600
                )
                
                structured_summary = summary_response["content"]
                lead.summary = structured_summary
                
                logger.info(f"✅ Resumo estruturado gerado para lead {lead.id}")
                
            except Exception as e:
                logger.error(f"❌ Erro gerando resumo estruturado: {e}")
                # Fallback: usa qualificação como resumo básico
                lead.summary = f"Lead {lead.qualification} - {len(all_messages)} mensagens trocadas"
        
        # Notifica gestor se virou QUENTE
        if (lead.qualification in ["hot", "quente"] and 
            old_qualification not in ["hot", "quente"] and 
            not gestor_ja_notificado):
            
            await notify_gestor(
                db=db,
                tenant=tenant,
                lead=lead,
                notification_type="lead_hot",
                empreendimento=empreendimento_detectado,
            )
            gestor_ja_notificado = True
            logger.info(f"🔥 Gestor notificado: lead virou QUENTE!")
        
    except Exception as e:
        logger.error(f"❌ Erro na qualificação: {e}")
        logger.error(traceback.format_exc())
        # Não falha o processo se qualificação der erro

    
    
    # =========================================================================
    # 17.6 NOTIFICAÇÃO DE LEAD NOVO
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
    # 18. DETECÇÃO DE SENTIMENTO E CONTEXTO
    # ========================================================================= # =========================================================================
    sentiment = {"sentiment": "neutral", "confidence": 0.5}  # ← SEM duplicação!
    is_returning_lead = False
    hours_since_last = 0
    
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
    
    # =========================================================================
    # 20. MONTA PROMPT
    # =========================================================================
    logger.info(f"🔨 Montando prompt | Emp: {bool(empreendimento_detectado)} | Imóvel: {bool(imovel_portal)}")
    
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
    
    # Instrução global para nicho imobiliário
    if ai_context["niche_id"].lower() in NICHOS_IMOBILIARIOS:
        system_prompt += """

🚨 VOCÊ É UM CORRETOR HUMANO no WhatsApp, NÃO UM ROBÔ!

REGRAS:
✅ SEMPRE responda perguntas sobre imóveis, preços, financiamento
✅ SEMPRE colete: orçamento, urgência, preferências
✅ Máximo 3-4 linhas por resposta
✅ Tom casual e amigável
✅ Dar informação + fazer pergunta

🚫 PROIBIDO:
❌ Formatação markdown (**, -, *)
❌ Listas numeradas
❌ Tom formal
❌ Respostas longas
❌ Dizer "não tenho informações"
"""
    
    # Adiciona contexto específico
    if empreendimento_detectado:
        logger.info(f"🏢 Injetando: {empreendimento_detectado.nome}")
        empreendimento_context = build_empreendimento_context(empreendimento_detectado)
        system_prompt += f"\n\n{empreendimento_context}"
        system_prompt += f"\n\nCliente interessado no {empreendimento_detectado.nome}. Responda como corretor amigo!"
    
    elif imovel_portal:
        logger.info(f"🏠 Injetando: código {imovel_portal.get('codigo')}")
        property_context = build_property_prompt_context(imovel_portal, content)
        system_prompt += property_context
    
    elif ai_context["niche_id"].lower() in NICHOS_IMOBILIARIOS:
        codigo_mencionado = extrair_codigo_imovel(content)
        
        if codigo_mencionado:
            logger.warning(f"⚠️ Código {codigo_mencionado} não encontrado")
            system_prompt += f"""

Cliente mencionou código {codigo_mencionado} mas não temos dados.

RESPONDA (sem formatação):
"Oi! Vi seu interesse no imóvel {codigo_mencionado}! Vou verificar os detalhes. Me conta: você tá buscando pra morar ou investir?"

🚫 NUNCA DIGA: "Não tenho informações", "Código não encontrado"
"""
        else:
            system_prompt += f"""

Você é corretor da {ai_context['company_name']}.
Cliente ainda não mencionou imóvel específico.

OBJETIVO: Entender o que procura, fazer perguntas (uma por vez).

EXEMPLOS:
- "Você tá buscando pra morar ou investir?"
- "Qual região você prefere?"
- "Quantos quartos você precisa?"

Respostas curtas (3-4 linhas), sem listas, sem formatação!
"""
    
    logger.info(f"✅ Prompt montado")
    
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
    
    final_response = ""
    was_blocked = False
    tokens_used = 0
    
    try:
        ai_response = await chat_completion(
            messages=messages,
            temperature=0.7,
            max_tokens=500,
        )
        
        # Nicho imobiliário: sem sanitização
        if ai_context["niche_id"].lower() in NICHOS_IMOBILIARIOS:
            final_response = ai_response["content"]
            was_blocked = False
            logger.info("🏠 Sanitização desabilitada")
        else:
            final_response, was_blocked = sanitize_response(
                ai_response["content"],
                ai_context["ai_out_of_scope_message"]
            )
            
            if was_blocked:
                logger.warning(f"⚠️ Resposta bloqueada: {lead.id}")
        
        tokens_used = ai_response.get("tokens_used", 0)
        
    except Exception as e:
        logger.error(f"❌ Erro chamando IA: {e}")
        
        if empreendimento_detectado:
            final_response = f"Olá! Que bom seu interesse no {empreendimento_detectado.nome}! Como posso ajudar?"
        elif imovel_portal:
            final_response = f"Olá! Vi seu interesse no imóvel {imovel_portal.get('codigo')}! Como posso ajudar?"
        else:
            final_response = f"Olá! Sou da {ai_context['company_name']}. Como posso ajudar?"
    
    # =========================================================================
    # 22. VERIFICA HANDOFF SUGERIDO PELA IA
    # =========================================================================
    should_transfer_by_ai = False
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
            "was_blocked": was_blocked,
            "identity_loaded": bool(ai_context.get("identity")),
            "empreendimento_id": empreendimento_detectado.id if empreendimento_detectado else None,
            "imovel_portal_codigo": imovel_portal.get("codigo") if imovel_portal else None,
        },
    )

    # =========================================================================
    # 24. HANDOFF FINAL
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
            "is_returning_lead": is_returning_lead,
            "was_blocked": was_blocked,
            "out_of_hours": is_out_of_hours,
            "imovel_portal_codigo": imovel_portal.get("codigo") if imovel_portal else None,
        }
    except Exception as e:
        logger.error(f"❌ Erro no commit: {e}")
        await db.rollback()
        return {
            "success": False,
            "error": "Erro interno",
            "reply": FALLBACK_RESPONSES["error"],
            "lead_id": lead.id,
        }