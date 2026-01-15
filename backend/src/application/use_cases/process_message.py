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
    Tenant, Lead, Message, Channel, LeadEvent, Notification, Product
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
            imovel_portal = buscar_imovel_na_mensagem(content)
            
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
                imovel_portal = buscar_imovel_na_mensagem(msg.get("content", ""))
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
                Product.slug == codigo  # No portal, o slug costuma ser o código
            )
        )
        product_obj = res_prod.scalar_one_or_none()
        
        # Se não achou pelo slug, tenta nos atributos
        if not product_obj:
            res_prod = await db.execute(
                select(Product).where(
                    Product.tenant_id == lead.tenant_id,
                    Product.attributes["codigo"].astext == codigo
                )
            )
            product_obj = res_prod.scalar_one_or_none()

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


def detect_hot_lead_signals(content: str) -> bool:
    """Detecta sinais de lead QUENTE na mensagem."""
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
# FUNÇÕES DE IA COM RETRY E TIMEOUT
# =============================================================================

async def chat_completion_com_retry(
    messages: list,
    temperature: float,
    max_tokens: int,
    max_retries: int = settings.openai_max_retries,
    timeout: float = settings.openai_timeout_seconds,
) -> dict:
    """
    🔄 Chama OpenAI com retry automático e timeout.
    
    - Timeout de 30s por tentativa
    - 3 tentativas com exponential backoff (2s, 4s)
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
        db=db,
        content=content,
        lead=lead,
        history=history,
    )
    
    if imovel_portal:
        logger.info(f"🏠 Imóvel portal: {imovel_portal.get('codigo')}")
    else:
        # 1. Tenta por critérios (bairro, preço, quartos)
        imoveis_sugeridos = buscar_imoveis_por_criterios(content)
        
        # 2. SE não achou por critérios, TENTA BUSCA SEMÂNTICA (RAG)
        if not imoveis_sugeridos and len(content.strip()) > 10:
            logger.info("🧠 Critérios não retornaram nada. Iniciando busca semântica...")
            imoveis_sugeridos = await buscar_imoveis_semantico(content)
            
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
    # 18.7. NOTIFICAÇÃO DE INTERESSE EM IMÓVEL (RAIO-X)
    # =========================================================================
    # Dispara quando temos: Nome do Lead + (Imóvel Portal ou Produto)
    if lead.name and (imovel_portal or product_detected):
        # Evita duplicar notificação para o MESMO imóvel nesta conversa
        codigo_atual = str(imovel_portal.get("codigo") if imovel_portal else product_detected.slug)
        ja_notificado = lead.custom_data.get("notificado_imovel_codigo") == codigo_atual
        
        if not ja_notificado:
            from src.infrastructure.services.dialog360_service import GestorNotificationService
            api_key = (tenant.settings or {}).get("dialog360_api_key")
            
            if api_key:
                target_prod = product_detected
                if not target_prod and lead.custom_data.get("product_id"):
                    res_p = await db.execute(select(Product).where(Product.id == lead.custom_data["product_id"]))
                    target_prod = res_p.scalar_one_or_none()
                
                # Se não temos produto mas temos imóvel portal, precisamos de um Product "dummy" ou genérico
                # Mas aqui o GestorNotificationService.notify_gestor espera um Product object.
                # Se target_prod ainda for None, tentamos buscar um produto genérico ou o que estiver associado ao tenant
                if target_prod:
                    logger.info(f"📲 Disparando Raio-X para {lead.name} no produto {target_prod.name}")
                    success = await GestorNotificationService.notify_gestor(
                        db=db, api_key=api_key, lead=lead, product=target_prod
                    )
                    if success:
                        if not lead.custom_data: lead.custom_data = {}
                        lead.custom_data["notificado_imovel_codigo"] = codigo_atual
                        flag_modified(lead, "custom_data")
    
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
    
    from src.application.services.ai_context_builder import extract_ai_context, build_complete_prompt
    
    # Prepara os contextos
    ai_context = extract_ai_context(tenant.name, tenant.settings)
    lead_ctx = lead_to_context(lead, message_count)
    prod_ctx = product_to_context(product_detected) if product_detected else None
    imovel_ctx = imovel_dict_to_context(imovel_portal) if imovel_portal else None
    
    # Constrói o prompt completo (V2 - Prioriza contextos dinâmicos)
    prompt_result = build_complete_prompt(
        ai_context=ai_context,
        lead_context=lead_ctx,
        product=prod_ctx,
        imovel_portal=imovel_ctx
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

    try:
        # 🔄 CHAMA COM RETRY E TIMEOUT!
        ai_response = await chat_completion_com_retry(
            messages=messages,
            temperature=0.7,
            max_tokens=200,
        )
        
        final_response = ai_response["content"]
        tokens_used = ai_response.get("tokens_used", 0)
        
    except Exception as e:
        logger.error(f"❌ Erro chamando IA (após {settings.openai_max_retries + 1} tentativas): {e}")
        logger.error(traceback.format_exc())
        
        # Fallback responses
        if product_detected:
            final_response = f"Olá! Interesse no {product_detected.name}! Como posso ajudar?"
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