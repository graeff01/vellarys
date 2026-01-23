"""
CASO DE USO: PROCESSAR MENSAGEM - VERSÃO IMOBILIÁRIA V2.0
==================================================================
Versão MINIMALISTA + SEGURANÇA + INTELIGÊNCIA

MELHORIAS V2.0:
✅ Validação de preços (anti-injection)
✅ Proteção anti-spam (repetição)
✅ Validação de código segura
✅ Retry logic OpenAI (3 tentativas)
✅ Timeout de 30s
✅ Extração automática de nome
✅ Formatação de preço BR
✅ Logging estruturado
✅ Métricas de performance
"""

import logging
logging.warning("PROCESS_MESSAGE V2.0 CARREGADO - COM MELHORIAS!")
import traceback
import asyncio
import time
import re
import json

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from src.infrastructure.services.property_lookup_service import (
    buscar_imovel_na_mensagem,
    buscar_imoveis_por_criterios,
    buscar_imoveis_semantico,
    extrair_codigo_imovel,
)

from src.domain.entities import (
    Tenant, Lead, Message, Channel, LeadEvent, Notification, Product, Niche
)
from src.domain.entities.enums import LeadStatus, EventType

from src.infrastructure.services import (
    extract_lead_data,
    execute_handoff,
    mark_lead_activity,
    check_handoff_triggers,
    check_business_hours,
    notify_lead_product,
    notify_gestor,
    chat_completion,
)

from src.infrastructure.services.openai_service import (
    detect_sentiment,
    calculate_typing_delay,
    validate_ai_response,
)

from src.application.services.ai_context_builder import (
    extract_ai_context,
    build_complete_prompt,
    lead_to_context,
    product_to_context,
    imovel_dict_to_context,
)

from src.domain.services.lead_profile_extractor import extract_lead_profile

from src.application.services.message_security import (
    check_jailbreak_attempt,
    check_spam_repetition,
    sanitize_message_content,
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
from src.config import FALLBACK_RESPONSES, get_settings
from src.infrastructure.services.lgpd_service import (
    detect_lgpd_request,
    get_lgpd_response,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# =============================================================================
# HELPERS DE SEGURANÇA (Refatorado para message_security.py)
# =============================================================================


def sanitize_imovel_data(imovel: Dict) -> Dict:
    """
    🛡️ SEGURANÇA: Sanitiza dados do imóvel do portal (anti-injection).
    Valida preços, remove caracteres perigosos, valida números.
    """
    if not imovel:
        return imovel
    
    # Valida preço
    if imovel.get("preco"):
        preco_str = str(imovel["preco"])
        apenas_numeros = re.sub(r'[^\d]', '', preco_str)
        
        if apenas_numeros:
            try:
                preco_int = int(apenas_numeros)
                
                # Preços razoáveis: R$ 50.000 até R$ 50.000.000
                if 50_000 <= preco_int <= 50_000_000:
                    imovel["preco"] = preco_int
                else:
                    logger.warning(f"⚠️ Preço suspeito: {preco_str}")
                    imovel["preco"] = "Consulte"
            except:
                imovel["preco"] = "Consulte"
        else:
            imovel["preco"] = "Consulte"
    
    # Sanitiza campos de texto (remove caracteres perigosos)
    text_fields = ["titulo", "tipo", "regiao", "descricao"]
    for field in text_fields:
        if imovel.get(field):
            # Remove caracteres especiais perigosos
            sanitized = re.sub(r'[<>{}[\]\\]', '', str(imovel[field]))
            imovel[field] = sanitized[:500]  # Limita tamanho
    
    # Valida números (quartos, banheiros, vagas)
    for field in ["quartos", "banheiros", "vagas"]:
        if imovel.get(field):
            try:
                num = int(imovel[field])
                if 0 <= num <= 50:  # Valores razoáveis
                    imovel[field] = num
                else:
                    imovel[field] = 0
            except:
                imovel[field] = 0
    
    # Valida metragem
    if imovel.get("metragem"):
        try:
            metragem = int(imovel["metragem"])
            if 10 <= metragem <= 10000:  # 10m² até 10.000m²
                imovel["metragem"] = metragem
            else:
                imovel["metragem"] = 0
        except:
            imovel["metragem"] = 0
    
    return imovel


def formatar_preco_br(preco: Any) -> str:
    """
    💰 Formata preço no padrão brasileiro.
    Entrada: 680000 ou "680000" ou "R$ 680000"
    Saída: "R$ 680.000"
    """
    if not preco:
        return "Consulte"
    
    # Remove tudo exceto números
    apenas_numeros = re.sub(r'[^\d]', '', str(preco))
    
    if not apenas_numeros:
        return "Consulte"
    
    try:
        valor = int(apenas_numeros)
        
        if valor < 10_000:  # Muito baixo
            return "Consulte"
        
        # Formata: R$ 680.000
        return f"R$ {valor:,.0f}".replace(",", ".")
    except:
        return "Consulte"


def extrair_nome_simples(mensagem: str) -> Optional[str]:
    """
    📝 Extrai nome do cliente usando padrões simples.
    Retorna None se não encontrar ou se for palavra inválida.
    """
    if not mensagem or len(mensagem) < 2:
        return None
    
    msg_lower = mensagem.lower().strip()
    
    # Padrões comuns
    patterns = [
        r'meu nome (?:é|eh) (\w+)',
        r'me chamo (\w+)',
        r'sou (?:o|a) (\w+)',
        r'^(\w+)$',  # Mensagem de 1 palavra = nome
    ]
    
    for pattern in patterns:
        match = re.search(pattern, msg_lower)
        if match:
            nome = match.group(1).strip().capitalize()
            
            # Valida: mínimo 2 letras, máximo 30, só letras
            if not (2 <= len(nome) <= 30 and nome.isalpha()):
                continue
            
            # Palavras inválidas (não são nomes)
            palavras_invalidas = {
                'oi', 'olá', 'ola', 'sim', 'nao', 'não', 'ok', 'obrigado', 'obrigada',
                'bom', 'dia', 'tarde', 'noite', 'tchau', 'legal', 'boa', 'tudo', 'bem',
                'opa', 'eai', 'fala', 'salve', 'valeu', 'entendi', 'certo', 'blz'
            }
            
            if nome.lower() not in palavras_invalidas:
                return nome
    
    return None


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

async def detect_product(
    db: AsyncSession,
    tenant_id: int,
    message: str,
) -> Optional[Product]:
    """Detecta se a mensagem contém gatilhos de algum produto."""
    try:
        result = await db.execute(
            select(Product)
            .where(Product.tenant_id == tenant_id)
            .where(Product.active == True)
            .order_by(Product.priority.desc())
        )
        products = result.scalars().all()
        
        if not products:
            return None
        
        message_lower = message.lower()
        
        for prod in products:
            if prod.triggers:
                for trigger in prod.triggers:
                    if trigger.lower() in message_lower:
                        logger.info(f"📦 Produto detectado: {prod.name} (gatilho: {trigger})")
                        return prod
        
        return None
        
    except Exception as e:
        logger.error(f"Erro detectando produto: {e}")
        return None


async def get_product_from_lead(
    db: AsyncSession,
    lead: Lead,
) -> Optional[Product]:
    """Recupera o produto associado ao lead (se houver)."""
    try:
        if not lead.custom_data:
            return None
        
        prod_id = lead.custom_data.get("product_id")
        if not prod_id:
            return None
        
        result = await db.execute(
            select(Product)
            .where(Product.id == prod_id)
            .where(Product.active == True)
        )
        return result.scalar_one_or_none()
        
    except Exception as e:
        logger.error(f"Erro recuperando produto: {e}")
        return None


async def update_product_stats(
    db: AsyncSession,
    product: Product,
    is_new_lead: bool = False,
):
    """Atualiza estatísticas do produto."""
    try:
        if is_new_lead:
            product.total_leads = (product.total_leads or 0) + 1
    except Exception as e:
        logger.error(f"Erro atualizando stats do produto: {e}")


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
    limit: int = settings.max_conversation_history,
) -> list[dict]:
    """
    Busca histórico de mensagens do lead.
    
    ✨ NOVO: Agora usa resumo automático para conversas longas!
    - Se <50 mensagens: retorna todas
    - Se >=50: retorna resumo + últimas 30
    """
    try:
        # Busca lead para verificar se tem resumo
        from src.domain.entities import Lead
        lead_result = await db.execute(
            select(Lead).where(Lead.id == lead_id)
        )
        lead = lead_result.scalar_one_or_none()
        
        if not lead:
            return []
        
        # Usa novo serviço de histórico efetivo
        from src.infrastructure.services.conversation_summary_service import get_effective_history
        return await get_effective_history(db, lead, max_recent_messages=limit)
        
    except Exception as e:
        logger.error(f"Erro ao buscar histórico: {e}")
        # Fallback: busca últimas N mensagens
        result = await db.execute(
            select(Message)
            .where(Message.lead_id == lead_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        return [{"role": msg.role, "content": msg.content} for msg in reversed(messages)]


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
    db: AsyncSession,
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
            imovel_portal = await buscar_imovel_na_mensagem(content, db=db, tenant_id=lead.tenant_id)
            
            # 🛡️ SANITIZA DADOS DO PORTAL!
            if imovel_portal:
                imovel_portal = sanitize_imovel_data(imovel_portal)
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
                imovel_portal = await buscar_imovel_na_mensagem(msg.get("content", ""), db=db, tenant_id=lead.tenant_id)
                if imovel_portal:
                    # 🛡️ SANITIZA DADOS DO PORTAL!
                    imovel_portal = sanitize_imovel_data(imovel_portal)
                    logger.info(f"✅ Encontrado no histórico: {imovel_portal.get('codigo')}")
                    break
    
    if imovel_portal:
        logger.info(f"💾 Salvando imóvel: {imovel_portal.get('codigo')}")
        
        if not lead.custom_data:
            lead.custom_data = {}
        
        # --- NOVO: BUSCA PRODUTO CORRESPONDENTE NO BANCO ---
        # Busca se existe um produto cadastrado com esse código para pegar o corretor
        codigo = str(imovel_portal.get("codigo"))
        res_prod = await db.execute(
            select(Product).where(
                Product.tenant_id == lead.tenant_id,
                Product.slug == codigo
            )
        )
        product_obj = res_prod.scalar_one_or_none()
        if product_obj:
            logger.info(f"✅ Produto encontrado pelo slug: {product_obj.name}")
        
        # Se não achou pelo slug, tenta nos atributos
        if not product_obj:
            res_prod = await db.execute(
                select(Product).where(
                    Product.tenant_id == lead.tenant_id,
                    Product.attributes["codigo"].astext == codigo
                )
            )
            product_obj = res_prod.scalar_one_or_none()
            if product_obj:
                logger.info(f"✅ Produto encontrado pelos atributos: {product_obj.name}")
            else:
                logger.warning(f"⚠️ Nenhum produto local encontrado para o código {codigo}")

        # Armazena dados do imóvel
        lead.custom_data["imovel_portal"] = {
            "codigo": codigo,
            "titulo": imovel_portal.get("titulo"),
            "tipo": imovel_portal.get("tipo"),
            "regiao": imovel_portal.get("regiao"),
            "quartos": imovel_portal.get("quartos"),
            "banheiros": imovel_portal.get("banheiros"),
            "vagas": imovel_portal.get("vagas"),
            "metragem": imovel_portal.get("metragem"),
            "preco": imovel_portal.get("preco"),
            "descricao": imovel_portal.get("descricao", ""),
            "corretor_nome": imovel_portal.get("corretor_nome"),
            "corretor_whatsapp": imovel_portal.get("corretor_whatsapp"),
        }
        
        # Se encontrou o produto, associa ao lead e pega dados do corretor
        if product_obj:
            lead.custom_data["product_id"] = product_obj.id
            lead.custom_data["product_name"] = product_obj.name
            
            # Se o produto tem corretor nos atributos, salva no lead para facilitar
            if product_obj.attributes:
                lead.custom_data["corretor_nome"] = product_obj.attributes.get("corretor_nome")
                lead.custom_data["corretor_whatsapp"] = product_obj.attributes.get("corretor_whatsapp")
                lead.custom_data["whatsapp_notification"] = product_obj.attributes.get("whatsapp_notification")

        lead.custom_data["contexto_ativo"] = "imovel_portal"
        flag_modified(lead, "custom_data")
    
    return imovel_portal


def detect_warm_lead_signals(content: str, history_len: int = 0) -> bool:
    """Detecta sinais de lead MORNO (engajamento/interesse)."""
    content_lower = content.lower()
    
    warm_signals = [
        r"quanto\s+custa", r"valor", r"preço", r"visita", r"agendar",
        r"fotos", r"vídeo", r"v[íi]deo", r"mais\s+info", r"detalhes",
        r"onde\s+fica", r"bairro", r"localização", r"mapa",
        r"entrada", r"parcela", r"financiamento", r"fgts",
        r"permuta", r"troca", r"aceita\s+carro"
    ]
    
    # 1. Busca por palavras-chave de interesse
    for signal in warm_signals:
        if re.search(signal, content_lower):
            return True
            
    # 2. Engajamento por volume (mais de 4 mensagens)
    if history_len >= 4:
        return True
        
    return False


def detect_hot_lead_signals(content: str) -> bool:
    """Detecta sinais de lead QUENTE (intenção clara de compra)."""
    content_lower = content.lower()
    
    hot_signals = [
        r"\bquero\s+comprar\b",
        r"\bvou\s+comprar\b",
        r"\bquero\s+fechar\b",
        r"\bvou\s+fechar\b",
        r"\bquero\s+visitar\b",
        r"\bmarcar\s+visita\b",
        r"\btenho.*\bdinheiro\b",
        r"\bdinheiro.*\bvista\b",
        r"\btenho.*\baprovado\b",
        r"\bfinanciamento.*\baprovado\b",
        r"\burgente\b",
        r"\bquando.*\bposso.*\bvisitar\b",
        r"\bquero\s+ir\s+a[ií]\b",
        r"\bandamento\s+no\s+cr[eé]dito\b",
        r"\bsimulacao\s+aprovada\b",
        r"\bquero\s+falar\s+com\s+corretor\b"
    ]
    
    for pattern in hot_signals:
        if re.search(pattern, content_lower):
            logger.info(f"🔥 Sinal quente detectado: '{pattern}'")
            return True
    
    return False


# =============================================================================
# FUNÇÕES DE IA COM RETRY E TIMEOUT
# =============================================================================

async def chat_completion_com_retry(
    messages: list,
    temperature: float,
    max_tokens: int,
    max_retries: int = settings.openai_max_retries,
    timeout: float = settings.openai_timeout_seconds,
    tools: list = None,
    tool_choice: str = None,
) -> dict:
    """
    🔄 Chama OpenAI com retry automático e timeout.

    - Timeout de 30s por tentativa
    - 3 tentativas com exponential backoff (2s, 4s)
    - Suporte a function calling (tools)
    - Lança exceção se todas falharem
    """
    for tentativa in range(max_retries + 1):
        try:
            # Timeout de 30s
            ai_response = await asyncio.wait_for(
                chat_completion(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=tools,
                    tool_choice=tool_choice,
                ),
                timeout=timeout
            )

            return ai_response
            
        except asyncio.TimeoutError:
            if tentativa < max_retries:
                wait_time = 2 ** tentativa  # 2s, 4s
                logger.warning(f"⏱️ OpenAI timeout (tentativa {tentativa + 1}/{max_retries + 1}), aguardando {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"❌ OpenAI timeout após {max_retries + 1} tentativas!")
                raise
                
        except Exception as e:
            if tentativa < max_retries:
                wait_time = 2 ** tentativa  # 2s, 4s
                logger.warning(f"⚠️ OpenAI erro (tentativa {tentativa + 1}/{max_retries + 1}): {e}, aguardando {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"❌ OpenAI falhou após {max_retries + 1} tentativas: {e}")
                raise


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
    external_message_id: str = None, # ✨ NOVO: Idempotência
) -> dict:
    """Processa uma mensagem recebida de um lead."""
    
    # ⏱️ MÉTRICA: Marca início
    start_time = time.time()
    
    # =========================================================================
    # INICIALIZAÇÃO DE VARIÁVEIS
    # =========================================================================
    product_detected: Optional[Product] = None
    imovel_portal: Optional[Dict] = None
    gestor_ja_notificado = False
    history: list[dict] = []
    message_count: int = 0
    should_transfer = False
    imoveis_sugeridos: List[Dict] = []
    
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
    # 🕵️ CHECK IDEMPOTÊNCIA (Evita responder 2x a mesma msg do WhatsApp)
    if external_message_id:
        result = await db.execute(
            select(Message).where(Message.lead_id == lead.id, Message.external_id == external_message_id)
        )
        if result.scalar_one_or_none():
            logger.warning(f"♻️ Mensagem duplicada ignorada: {external_message_id}")
            return {
                "success": True,
                "reply": None,
                "idempotency_skip": True
            }

    history = await get_conversation_history(db, lead.id)
    message_count = await count_lead_messages(db, lead.id)
    
    # 📊 LOGGING ESTRUTURADO
    logger.info(f"""
╔═══════════════════════════════════════════════════════════════
║ 📊 CONTEXTO - Lead {lead.id}
╠═══════════════════════════════════════════════════════════════
║ Mensagem: {content[:70]}...
║ Histórico: {len(history)} mensagens
║ Total msgs: {message_count}
║ Nome: {lead.name or 'N/A'}
║ Qualif.: {lead.qualification or 'N/A'}
╚═══════════════════════════════════════════════════════════════
""")
        
    # =========================================================================
    # 9. DETECÇÃO DE PRODUTO
    # =========================================================================
    product_detected = await detect_product(
        db=db,
        tenant_id=tenant.id,
        message=content,
    )
    
    if not product_detected and not is_new:
        product_detected = await get_product_from_lead(db, lead)
    
    if product_detected:
        logger.info(f"📦 Produto: {product_detected.name}")
        
        if not lead.custom_data:
            lead.custom_data = {}
        
        old_prod_id = lead.custom_data.get("product_id")
        if old_prod_id != product_detected.id:
            lead.custom_data["product_id"] = product_detected.id
            lead.custom_data["product_name"] = product_detected.name
            flag_modified(lead, "custom_data")
        
        if is_new:
            await update_product_stats(db, product_detected, is_new_lead=True)
            
            if product_detected.seller_id:
                lead.assigned_seller_id = product_detected.seller_id
                lead.assignment_method = "product"
                lead.assigned_at = datetime.now(timezone.utc)
    
    # =========================================================================
    # 10. NOTIFICAÇÃO ESPECÍFICA DE PRODUTO
    # =========================================================================
    if (product_detected and 
        product_detected.notify_manager and 
        is_new and 
        not gestor_ja_notificado):
        await notify_lead_product(db, tenant, lead, product_detected)
        gestor_ja_notificado = True
        logger.info(f"📲 Notificação produto: {product_detected.name}")
    
    # =========================================================================
    # 11. LGPD CHECK
    # =========================================================================
    lgpd_request = detect_lgpd_request(content)
    if lgpd_request:
        logger.info(f"🔒 LGPD request: {lgpd_request}")
        
        user_message = Message(
            lead_id=lead.id, 
            role="user", 
            content=content, 
            tokens_used=0,
            external_id=external_message_id
        )
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
        
        user_message = Message(
            lead_id=lead.id, 
            role="user", 
            content=content, 
            tokens_used=0,
            external_id=external_message_id
        )
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
        db=db,
        content=content,
        lead=lead,
        history=history,
    )
    
    if imovel_portal:
        logger.info(f"🏠 Imóvel portal: {imovel_portal.get('codigo')}")
    else:
        # 1. Tira por critérios (bairro, preço, quartos)
        imoveis_sugeridos = await buscar_imoveis_por_criterios(content, db=db, tenant_id=tenant.id)
        
        # 2. SE não achou por critérios, TENTA BUSCA SEMÂNTICA (RAG)
        if not imoveis_sugeridos and len(content.strip()) > 10:
            logger.info("🧠 Critérios não retornaram nada. Iniciando busca semântica...")
            imoveis_sugeridos = await buscar_imoveis_semantico(content, db=db, tenant_id=tenant.id)
            
        if imoveis_sugeridos:
            logger.info(f"🔎 Encontrados {len(imoveis_sugeridos)} imóveis para sugestão")
    
    # =========================================================================
    # 14. HANDOFF TRIGGERS
    # =========================================================================
    trigger_found, trigger_matched = check_handoff_triggers(
        message=content,
        custom_triggers=settings["handoff_triggers"],
    )
    
    if trigger_found:
        logger.info(f"🔔 Handoff trigger: {trigger_matched}")
        
        user_message = Message(
            lead_id=lead.id, 
            role="user", 
            content=content, 
            tokens_used=0,
            external_id=external_message_id
        )
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
    user_message = Message(
        lead_id=lead.id, 
        role="user", 
        content=content, 
        tokens_used=0,
        external_id=external_message_id
    )
    db.add(user_message)
    await db.flush()

    await mark_lead_activity(db, lead)

    # =========================================================================
    # 16.5. ATUALIZA PERFIL PROGRESSIVO DO LEAD (MEMÓRIA DE LONGO PRAZO)
    # =========================================================================
    try:
        current_profile = lead.custom_data.get("lead_profile", {}) if lead.custom_data else {}
        updated_profile = extract_lead_profile(content, current_profile)

        # Só atualiza se houver mudanças
        if updated_profile != current_profile:
            if not lead.custom_data:
                lead.custom_data = {}
            lead.custom_data["lead_profile"] = updated_profile
            flag_modified(lead, "custom_data")
            logger.info(f"📊 Perfil progressivo atualizado para lead {lead.id}")
    except Exception as e:
        logger.warning(f"⚠️ Erro extraindo perfil (não crítico): {e}")

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
    # 18.7. NOTIFICAÇÃO DE INTERESSE EM IMÓVEL (RAIO-X)
    # =========================================================================
    # Dispara quando temos: Nome do Lead + (Imóvel Portal ou Produto)
    if lead.name and (imovel_portal or product_detected):
        # Evita duplicar notificação para o MESMO imóvel nesta conversa
        codigo_atual = str(imovel_portal.get("codigo") if imovel_portal else product_detected.slug)
        ja_notificado = lead.custom_data.get("notificado_imovel_codigo") == codigo_atual
        
        if not ja_notificado:
            # Buscamos as configurações de distribuição/notificação
            settings_dist = tenant.settings.get("distribution", {}) if tenant.settings else {}
            notify_broker_raiox = settings_dist.get("notify_broker_raiox", True)
            min_messages_broker = settings_dist.get("min_messages_broker_raiox", 3) # Default 3 mensagens
            
            # 1. Fluxo do GESTOR (Sempre imediato se não notificado)
            ja_notificado_gestor = lead.custom_data.get("notificado_gestor_codigo") == codigo_atual
            if not ja_notificado_gestor:
                logger.info(f"📲 [RAIO-X] Notificando GESTOR imediatamente: {codigo_atual}")
                await notify_gestor(
                    db=db,
                    tenant=tenant,
                    lead=lead,
                    notification_type="lead_hot",
                    product=product_detected,
                    extra_context={
                        "is_raiox": True,
                        "target_broker": False # Forçamos para o gestor neste primeiro envio
                    }
                )
                lead.custom_data["notificado_gestor_codigo"] = codigo_atual
                flag_modified(lead, "custom_data")
            
            # 2. Fluxo do CORRETOR (Delayed baseado no número de mensagens)
            if notify_broker_raiox:
                ja_notificado_corretor = lead.custom_data.get("notificado_corretor_codigo") == codigo_atual
                if not ja_notificado_corretor:
                    # Contamos mensagens do lead no histórico (user messages)
                    user_msgs_count = sum(1 for m in history if m.get("role") == "user") + 1 # +1 pela mensagem atual
                    
                    if user_msgs_count >= min_messages_broker:
                        logger.info(f"📲 [RAIO-X] Threshold atingido ({user_msgs_count}/{min_messages_broker}). Notificando CORRETOR: {codigo_atual}")
                        await notify_gestor(
                            db=db,
                            tenant=tenant,
                            lead=lead,
                            notification_type="lead_hot",
                            product=product_detected,
                            extra_context={
                                "is_raiox": True,
                                "target_broker": True # Aqui tentamos o corretor
                            }
                        )
                        lead.custom_data["notificado_corretor_codigo"] = codigo_atual
                        flag_modified(lead, "custom_data")
                    else:
                        logger.info(f"⏳ [RAIO-X] Aguardando mais mensagens para Broker ({user_msgs_count}/{min_messages_broker})")
            
            # Marca flag legado para compatibilidade se ambos estiverem ok ou se broker desativado
            gestor_ok = lead.custom_data.get("notificado_gestor_codigo") == codigo_atual
            broker_ok = not notify_broker_raiox or lead.custom_data.get("notificado_corretor_codigo") == codigo_atual
            
            if gestor_ok and broker_ok:
                lead.custom_data["notificado_imovel_codigo"] = codigo_atual
                flag_modified(lead, "custom_data")
            
            await db.commit()
    
    # =========================================================================
    # 18.6. PROTEÇÃO ANTI-SPAM (REPETIÇÃO)
    # =========================================================================
    spam_response = check_spam_repetition(history, message_count)
    if spam_response:
        assistant_message = Message(
            lead_id=lead.id,
            role="assistant",
            content=spam_response,
            tokens_used=0
        )
        db.add(assistant_message)
        await db.commit()
        
        return {
            "success": True,
            "reply": spam_response,
            "lead_id": lead.id,
            "is_new_lead": False,
            "spam_detected": True,
        }
    
    # =========================================================================
    # 19. QUALIFICAÇÃO AUTOMÁTICA (INTELIGÊNCIA DE VENDAS)
    # =========================================================================
    qualification_changed = False
    old_qualification = lead.qualification
    
    # 1. Verifica sinais QUENTES (Hot Lead)
    is_hot_lead = detect_hot_lead_signals(content)
    
    # 2. Verifica sinais MORNOS (Warm Lead)
    is_warm_lead = False
    if not is_hot_lead:
        is_warm_lead = detect_warm_lead_signals(content, len(history))
        # Se temos imóvel portal, ele é no mínimo MORNO
        if imovel_portal or product_detected:
            is_warm_lead = True

    # Aplica mudanças de qualificação (apenas para cima)
    if is_hot_lead and lead.qualification != "quente":
        logger.warning(f"🔥 PROMOÇÃO: Lead {lead.id} -> QUENTE")
        lead.qualification = "quente"
        qualification_changed = True
    elif is_warm_lead and lead.qualification not in ["quente", "morno"]:
        logger.info(f"☀️ PROMOÇÃO: Lead {lead.id} -> MORNO")
        lead.qualification = "morno"
        qualification_changed = True
    elif not lead.qualification:
        # Padrão para qualquer lead que começou a falar
        lead.qualification = "frio"
        qualification_changed = True

    # Registra evento de mudança de qualificação
    if qualification_changed:
        event = LeadEvent(
            lead_id=lead.id,
            event_type=EventType.QUALIFICATION_CHANGE.value,
            old_value=old_qualification,
            new_value=lead.qualification,
            description="Qualificação atualizada automaticamente por IA"
        )
        db.add(event)
        flag_modified(lead, "qualification")

    # 3. Lógica de Handoff para Leads Quentes
    if is_hot_lead and old_qualification != "quente":
        if lead.name:
            first_name = lead.name.split()[0]
            hot_response = f"Perfeito, {first_name}! Vou te passar pro corretor agora mesmo!"
        else:
            hot_response = "Entendi perfeitamente! Vou te passar agora para um de nossos especialistas. Qual seu nome para eu avisar ele?"
        
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
        
        logger.info(f"🔥 Lead {lead.id} transferido por sinal quente (Auto-Qualify)")
        
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
    # 19.5 VERIFICA SEGURANÇA DO PROMPT (ANTI-JAILBREAK)
    # =========================================================================
    jailbreak_reply = check_jailbreak_attempt(content, settings["company_name"])
    if jailbreak_reply:
        # Salva histórico básico e breca
        user_message = Message(lead_id=lead.id, role="user", content=content, tokens_used=0)
        db.add(user_message)
        assistant_message = Message(lead_id=lead.id, role="assistant", content=jailbreak_reply, tokens_used=0)
        db.add(assistant_message)
        await db.commit()
        
        return {
            "success": True, 
            "reply": jailbreak_reply,
            "lead_id": lead.id,
            "security": "blocked_jailbreak"
        }

    # =========================================================================
    # 20. MONTA PROMPT CENTRALIZADO (FAXINA DE SENIORIDADE)
    # =========================================================================
    logger.info(f"🤖 Preparando contexto centralizado...")
    
    # --- NOVO: Busca o Template do Nicho no Banco ---
    niche_template = None
    niche_slug = tenant.settings.get("basic", {}).get("niche") or tenant.settings.get("niche") or "services"
    
    try:
        from src.domain.entities import Niche
        res_niche = await db.execute(select(Niche).where(Niche.slug == niche_slug))
        niche_obj = res_niche.scalar_one_or_none()
        if niche_obj:
            niche_template = niche_obj.prompt_template
            logger.info(f"✨ Template do nicho '{niche_slug}' carregado com sucesso.")
        else:
            logger.warning(f"⚠️ Nicho '{niche_slug}' não encontrado no banco. Usando fallback.")
    except Exception as e:
        logger.error(f"❌ Erro ao buscar nicho: {e}")

    # Prepara os contextos
    ai_context = extract_ai_context(tenant.name, tenant.settings, niche_template=niche_template)
    lead_ctx = lead_to_context(lead, message_count)
    prod_ctx = product_to_context(product_detected) if product_detected else None
    imovel_ctx = imovel_dict_to_context(imovel_portal) if imovel_portal else None

    # Obtém perfil progressivo do lead (memória de longo prazo)
    lead_profile = lead.custom_data.get("lead_profile") if lead.custom_data else None

    # =========================================================================
    # 20.5. BUSCA RAG NA BASE DE CONHECIMENTO
    # =========================================================================
    rag_context = None

    # Busca RAG apenas se NÃO tem imóvel específico ou produto (evita poluir contexto)
    if not imovel_portal and not product_detected:
        try:
            from src.infrastructure.services.knowledge_rag_service import (
                search_knowledge,
                build_rag_context,
            )

            rag_results = await search_knowledge(
                db=db,
                tenant_id=tenant.id,
                query=content,
                top_k=3,
                min_similarity=0.6,
                source_types=["faq", "document", "rule"],
            )

            if rag_results:
                rag_context = build_rag_context(rag_results)
                logger.info(f"📚 RAG: {len(rag_results)} resultados relevantes encontrados")

        except Exception as e:
            logger.warning(f"⚠️ Erro na busca RAG (não crítico): {e}")

    # Constrói o prompt completo (V2 - Prioriza contextos dinâmicos)
    prompt_result = build_complete_prompt(
        ai_context=ai_context,
        lead_context=lead_ctx,
        product=prod_ctx,
        imovel_portal=imovel_ctx,
        lead_profile=lead_profile,
        rag_context=rag_context,
    )
    
    system_prompt = prompt_result.system_prompt
    logger.info(f"✅ Prompt centralizado gerado ({len(system_prompt)} chars)")
    
    # ═══════════════════════════════════════════════════════════════
    # ⚠️ CRITICAL FIX: ADICIONA MENSAGEM ATUAL AO HISTÓRICO!
    # (NÃO MEXER NISSO - CORREÇÃO DO BUG DE ATRASO!)
    # ═══════════════════════════════════════════════════════════════
    history.append({"role": "user", "content": content})
    
    messages = [{"role": "system", "content": system_prompt}, *history]

    final_response = ""
    tokens_used = 0

    # =========================================================================
    # 20.7. PREPARA FUNCTION CALLING (TOOLS)
    # =========================================================================
    from src.infrastructure.services.ai_tools import (
        get_tools_for_niche,
        should_use_tools,
        execute_tool,
        format_tool_result_for_ai,
    )

    available_tools = None
    use_tools = should_use_tools(
        niche_slug=niche_slug,
        has_product=bool(product_detected),
        has_imovel=bool(imovel_portal)
    )

    if use_tools:
        available_tools = get_tools_for_niche(niche_slug)
        if available_tools:
            logger.info(f"🔧 Function calling habilitado: {len(available_tools)} tools disponíveis")

    # =========================================================================
    # 20.8. LOOP DE CHAMADA DA IA COM FUNCTION CALLING
    # =========================================================================
    MAX_TOOL_ITERATIONS = 3  # Evita loops infinitos

    try:
        for iteration in range(MAX_TOOL_ITERATIONS + 1):
            # 🔄 CHAMA COM RETRY E TIMEOUT!
            ai_response = await chat_completion_com_retry(
                messages=messages,
                temperature=0.7,
                max_tokens=200,
                tools=available_tools,
                tool_choice="auto" if available_tools else None,
            )

            tokens_used += ai_response.get("tokens_used", 0)
            tool_calls = ai_response.get("tool_calls")

            # Se não tem tool_calls, é resposta final
            if not tool_calls:
                final_response = ai_response.get("content", "")
                break

            # Processa cada tool_call
            logger.info(f"🔧 Iteração {iteration + 1}: {len(tool_calls)} tool(s) solicitada(s)")

            for tc in tool_calls:
                func_name = tc["function"]["name"]
                try:
                    func_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    func_args = {}

                # Executa a tool
                result = await execute_tool(
                    tool_name=func_name,
                    arguments=func_args,
                    db=db,
                    tenant_id=tenant.id,
                    lead_id=lead.id,
                )

                # Formata resultado para contexto da IA
                result_text = format_tool_result_for_ai(func_name, result)

                # Adiciona ao histórico de mensagens para próxima iteração
                # 1. Adiciona a resposta da IA com tool_calls
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [tc],
                })

                # 2. Adiciona resultado da tool
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result_text,
                })

            # Se chegou na última iteração sem resposta, força uma resposta
            if iteration == MAX_TOOL_ITERATIONS:
                logger.warning(f"⚠️ Máximo de iterações de tools atingido ({MAX_TOOL_ITERATIONS})")
                final_response = ai_response.get("content") or "Desculpe, não consegui processar sua solicitação. Pode tentar de novo?"
                break

    except Exception as e:
        logger.error(f"❌ Erro chamando IA (após {settings.openai_max_retries + 1} tentativas): {e}")
        logger.error(traceback.format_exc())

        # Fallback responses
        if product_detected:
            final_response = f"Olá! Interesse no {product_detected.name}! Como posso ajudar?"
        elif imovel_portal:
            final_response = f"Olá! Vi seu interesse no imóvel {imovel_portal.get('codigo')}! Como posso ajudar?"
        else:
            final_response = "Olá! Como posso ajudar?"

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
    
    # ✨ NOVO: Atualiza resumo automático (em background, não bloqueia)
    try:
        from src.infrastructure.services.conversation_summary_service import update_lead_summary
        await update_lead_summary(db, lead)
    except Exception as e:
        logger.warning(f"⚠️ Erro ao atualizar resumo (não crítico): {e}")
    
    await log_ai_action(
        db=db, tenant_id=tenant.id, lead_id=lead.id,
        action_type="response",
        details={
            "tokens_used": tokens_used,
            "sentiment": sentiment.get("sentiment"),
            "product_id": product_detected.id if product_detected else None,
            "imovel_portal_codigo": imovel_portal.get("codigo") if imovel_portal else None,
        },
    )

    # =========================================================================
    # 22.5. AUTO-CRIAÇÃO DE OPORTUNIDADE (IA)
    # =========================================================================
    # Quando a IA detecta interesse em um imóvel específico, cria oportunidade automaticamente
    try:
        from src.domain.entities.opportunity import Opportunity

        # Só cria se lead estiver no mínimo "morno" (showing interest)
        if lead.qualification in ["quente", "hot", "morno", "warm"]:
            should_create_opportunity = False
            opportunity_title = None
            opportunity_value = 0
            opportunity_product_id = None
            opportunity_data = {}

            # Detecta interesse em produto interno
            if product_detected:
                opportunity_title = product_detected.name  # Nome direto, sem "Interesse:"
                opportunity_product_id = product_detected.id
                opportunity_seller_id = product_detected.seller_id  # Corretor do imóvel

                # Extrai valor do produto
                if product_detected.attributes and product_detected.attributes.get("preco"):
                    try:
                        preco = product_detected.attributes["preco"]
                        if isinstance(preco, int):
                            opportunity_value = preco * 100  # Converte para centavos
                        else:
                            opportunity_value = int(re.sub(r'[^\d]', '', str(preco)))
                    except:
                        pass

                # Dados extras do produto (COMPLETO - para popular formulário)
                if product_detected.attributes:
                    attrs = product_detected.attributes
                    opportunity_data = {
                        "property_address": attrs.get("regiao") or attrs.get("bairro") or attrs.get("endereco") or "",
                        "property_type": attrs.get("tipo") or "",
                        "bedrooms": attrs.get("quartos") or 0,
                        "bathrooms": attrs.get("banheiros") or 0,
                        "area": attrs.get("metragem") or attrs.get("area") or 0,
                        "garage_spaces": attrs.get("vagas") or 0,
                        "commission_percent": attrs.get("comissao") or attrs.get("comissao_percent") or 0,
                        "payment_type": attrs.get("tipo_pagamento") or attrs.get("forma_pagamento") or "a_vista",
                    }

                # Atribui corretor automaticamente (do imóvel)
                if opportunity_seller_id:
                    # Se o lead ainda não tem vendedor, atribui automaticamente
                    if not lead.assigned_seller_id:
                        lead.assigned_seller_id = opportunity_seller_id
                        lead.assigned_at = datetime.now(timezone.utc)
                        lead.assignment_method = "auto_by_property"
                        logger.info(f"✅ Lead {lead.id} atribuído ao vendedor {opportunity_seller_id} (imóvel {product_detected.name})")

                should_create_opportunity = True

            # Detecta interesse em imóvel do portal
            elif imovel_portal:
                codigo = imovel_portal.get("codigo") or "sem código"
                titulo = imovel_portal.get("titulo") or "Imóvel"
                opportunity_title = f"{titulo} (Cód: {codigo})"
                opportunity_seller_id = None  # Portal não tem seller direto

                # Extrai valor
                if imovel_portal.get("preco"):
                    try:
                        preco = imovel_portal["preco"]
                        if isinstance(preco, int):
                            opportunity_value = preco * 100  # Converte para centavos
                        else:
                            opportunity_value = int(re.sub(r'[^\d]', '', str(preco)))
                    except:
                        pass

                # Dados extras do imóvel (COMPLETO)
                opportunity_data = {
                    "property_address": imovel_portal.get("regiao") or imovel_portal.get("endereco") or "",
                    "property_type": imovel_portal.get("tipo") or "",
                    "property_code": codigo,
                    "bedrooms": imovel_portal.get("quartos") or 0,
                    "bathrooms": imovel_portal.get("banheiros") or 0,
                    "area": imovel_portal.get("metragem") or imovel_portal.get("area") or 0,
                    "garage_spaces": imovel_portal.get("vagas") or 0,
                    "commission_percent": imovel_portal.get("comissao") or 0,
                    "payment_type": imovel_portal.get("tipo_pagamento") or "a_vista",
                }

                should_create_opportunity = True

            # Cria oportunidade se detectou interesse
            if should_create_opportunity and opportunity_title:
                # Verifica se já existe oportunidade similar
                existing_opp_result = await db.execute(
                    select(Opportunity)
                    .where(Opportunity.lead_id == lead.id)
                    .where(Opportunity.title == opportunity_title)
                    .where(Opportunity.status.in_(["novo", "negociacao", "proposta"]))  # Não conta perdidos/ganhos
                )
                existing_opp = existing_opp_result.scalar_one_or_none()

                if not existing_opp:
                    # Calcula probabilidade baseada na qualificação
                    probability = 80 if lead.qualification in ["quente", "hot"] else 50
                    opportunity_data["probability"] = probability

                    # Define seller_id (prioriza seller do imóvel, senão usa do lead)
                    final_seller_id = opportunity_seller_id if 'opportunity_seller_id' in locals() else lead.assigned_seller_id

                    # Data de fechamento estimada (30 dias para quente, 60 para morno)
                    from datetime import timedelta
                    days_to_close = 30 if lead.qualification in ["quente", "hot"] else 60
                    expected_close = datetime.now(timezone.utc) + timedelta(days=days_to_close)

                    # Nota automática com contexto
                    auto_notes = f"Oportunidade criada automaticamente pela IA ao detectar interesse.\nQualificação inicial: {lead.qualification}"
                    if lead.ai_sentiment:
                        auto_notes += f"\nSentimento: {lead.ai_sentiment}"

                    # Cria nova oportunidade com TODOS os dados preenchidos
                    new_opportunity = Opportunity(
                        tenant_id=tenant.id,
                        lead_id=lead.id,
                        product_id=opportunity_product_id,
                        seller_id=final_seller_id,
                        title=opportunity_title,
                        value=opportunity_value,
                        status="novo",
                        expected_close_date=expected_close,
                        notes=auto_notes,
                        custom_data=opportunity_data,
                    )
                    db.add(new_opportunity)

                    logger.info(f"🎯 Oportunidade criada automaticamente: {opportunity_title} (R$ {opportunity_value/100:.2f} | Vendedor: {final_seller_id}) para lead {lead.id}")
                else:
                    logger.info(f"ℹ️ Oportunidade similar já existe para lead {lead.id}")

    except Exception as e:
        logger.warning(f"⚠️ Erro ao criar oportunidade automaticamente (não crítico): {e}")
        # Não bloqueia o fluxo se falhar

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
        
        # ⏱️ MÉTRICA: Calcula tempo total
        elapsed = time.time() - start_time
        logger.info(f"⏱️ Processamento concluído em {elapsed:.2f}s (com handoff)")
        
        reply_data = {
            "success": True,
            "reply": reply_with_handoff,
            "lead_id": lead.id,
            "is_new_lead": is_new,
            "qualification": lead.qualification,
            "status": "transferido",
            "typing_delay": calculate_typing_delay(len(final_response)),
            "out_of_hours": is_out_of_hours,
            "processing_time_seconds": f"{elapsed:.2f}",
        }

        # 🚀 EXTRA: Verifica se o cliente pediu localização
        asked_location = any(word in final_response.lower() for word in ["localização", "endereço", "onde fica", "gps", "mapa"])
        
        if asked_location:
            endereco = ""
            if imovel_portal and imovel_portal.get("regiao"):
                endereco = imovel_portal.get("regiao")
            elif product_detected:
                attrs = product_detected.attributes or {}
                endereco = attrs.get("regiao") or attrs.get("bairro") or ""
            
            if endereco:
                addr_text = f"📍 Localização: {endereco}"
                if addr_text not in reply_data["reply"]:
                    reply_data["reply"] += f"\n\n{addr_text}"

        return reply_data
    
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
        
        # ⏱️ MÉTRICA: Calcula tempo total
        elapsed = time.time() - start_time
        logger.info(f"⏱️ Processamento concluído em {elapsed:.2f}s")
        
        reply_data = {
            "success": True,
            "reply": final_response,
            "lead_id": lead.id,
            "is_new_lead": is_new,
            "qualification": lead.qualification,
            "typing_delay": calculate_typing_delay(len(final_response)),
            "sentiment": sentiment.get("sentiment"),
            "out_of_hours": is_out_of_hours,
            "imovel_portal_codigo": imovel_portal.get("codigo") if imovel_portal else None,
            "processing_time_seconds": f"{elapsed:.2f}",
        }

        # 🚀 EXTRA: Verifica se o cliente pediu localização
        asked_location = any(word in final_response.lower() for word in ["localização", "endereço", "onde fica", "gps", "mapa"])
        
        if asked_location:
            endereco = ""
            if imovel_portal and imovel_portal.get("regiao"):
                endereco = imovel_portal.get("regiao")
            elif product_detected:
                attrs = product_detected.attributes or {}
                endereco = attrs.get("regiao") or attrs.get("bairro") or ""
            
            if endereco:
                addr_text = f"📍 Localização: {endereco}"
                if addr_text not in reply_data["reply"]:
                    reply_data["reply"] += f"\n\n{addr_text}"

        return reply_data
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