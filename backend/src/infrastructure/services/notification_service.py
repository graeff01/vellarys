"""
NOTIFICATION SERVICE (Z-API + PUSH)
===================================

Serviço centralizado de notificações do Velaris.
✅ ATUALIZADO: Agora inclui Push Notifications!

Canais de notificação:
1. Painel (banco de dados)
2. WhatsApp (Z-API)
3. Push Notification (Web Push) ← NOVO!

"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Tenant, Lead, Notification, Seller, Message, Channel

# ✅ NOVO: Import do push_service
from src.infrastructure.services.push_service import (
    send_push_to_tenant,
    send_push_to_user,
    PushNotificationPayload,
)

from src.infrastructure.services.zapi_service import ZAPIService, get_zapi_client

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES
# =============================================================================

NOTIFICATION_TYPES = {
    "lead_new": "Novo Lead",
    "lead_hot": "Lead Quente",
    "lead_product": "Novo Produto/Serviço",
    "lead_out_of_hours": "Lead Fora do Horário",
    "handoff_requested": "Handoff Solicitado",
    "handoff_completed": "Handoff Concluído",
    "lead_assigned": "Lead Atribuído",
}

QUALIFICATION_EMOJIS = {
    "novo": "🆕",
    "frio": "❄️",
    "morno": "🌤️",
    "quente": "🔥",
    "hot": "🔥",
}

QUALIFICATION_LABELS = {
    "novo": "Novo",
    "frio": "Frio",
    "morno": "Morno",
    "quente": "QUENTE",
    "hot": "QUENTE",
}


# =============================================================================
# FUNÇÕES DE FORMATAÇÃO (UNIVERSAL - TODOS OS NICHOS)
# =============================================================================

def format_phone_display(phone: str) -> str:
    """Formata telefone para exibição amigável."""
    if not phone:
        return "Não informado"

    digits = ''.join(filter(str.isdigit, phone))

    if len(digits) == 11:
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    elif len(digits) == 13 and digits.startswith("55"):
        return f"({digits[2:4]}) {digits[4:9]}-{digits[9:]}"

    return phone


def format_phone_whatsapp(phone: str) -> str:
    """Formata telefone para link WhatsApp (só números com código país)."""
    if not phone:
        return ""

    digits = ''.join(filter(str.isdigit, phone))

    if len(digits) == 11:
        digits = "55" + digits

    return digits


def format_datetime_br(dt: datetime) -> str:
    """Formata datetime para formato brasileiro."""
    if not dt:
        return "Não informado"

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    dt_br = dt - timedelta(hours=3)

    return dt_br.strftime("%d/%m/%Y às %H:%M")


def get_qualification_display(qualification: str) -> str:
    """Retorna emoji + label da qualificação."""
    qual = (qualification or "frio").lower()
    emoji = QUALIFICATION_EMOJIS.get(qual, "❓")
    label = QUALIFICATION_LABELS.get(qual, qualification)
    return f"{emoji} {label}"


# =============================================================================
# TRECHOS REAIS DA CONVERSA
# =============================================================================

async def build_conversation_excerpt(
    db: AsyncSession,
    lead_id: int,
    max_messages: int = 6,
    max_length_per_message: int = 200,
) -> str:
    """Busca e formata trechos REAIS da conversa."""
    try:
        result = await db.execute(
            select(Message)
            .where(Message.lead_id == lead_id)
            .order_by(Message.created_at.desc())
            .limit(max_messages)
        )
        messages = list(reversed(result.scalars().all()))
        
        if not messages:
            return "_Sem mensagens ainda_"
        
        lines = []
        
        for msg in messages:
            content = msg.content or ""
            if len(content) > max_length_per_message:
                content = content[:max_length_per_message] + "..."
            
            if msg.role == "user":
                lines.append(f"👤 *Cliente:* \"{content}\"")
            elif msg.role == "assistant":
                lines.append(f"🤖 *IA:* \"{content}\"")
            else:
                lines.append(f"💬 *{msg.role}:* \"{content}\"")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Erro ao buscar trechos da conversa: {e}")
        return "_Erro ao carregar conversa_"


# =============================================================================
# BUILD LEAD SUMMARY (UNIVERSAL)
# =============================================================================

def build_lead_summary_text(
    lead: Lead,
    include_conversation: bool = False,
    max_summary_length: int = 500,
) -> str:
    """Constrói texto resumido do lead para notificações."""
    lines = []

    if lead.name:
        lines.append(f"👤 *Nome:* {lead.name}")

    if lead.phone:
        lines.append(f"📱 *WhatsApp:* {format_phone_display(lead.phone)}")

    if lead.email:
        lines.append(f"📧 *Email:* {lead.email}")

    if lead.city:
        lines.append(f"📍 *Cidade:* {lead.city}")

    if lead.qualification:
        lines.append(f"📊 *Qualificação:* {get_qualification_display(lead.qualification)}")

    if lead.source and lead.source != "organico":
        lines.append(f"📢 *Origem:* {lead.source}")

    if lead.campaign:
        lines.append(f"🎯 *Campanha:* {lead.campaign}")

    if lead.custom_data:
        custom_lines = []

        field_mappings = {
            "product_name": ("📦", "Produto/Serviço"),
            "product_name": ("📦", "Produto/Serviço"),
            "interesse": ("🏠", "Interesse"),
            "tipologia": ("🛏️", "Tipologia"),
            "budget_range": ("💰", "Orçamento"),
            "urgency_level": ("⏰", "Urgência"),
            "prazo": ("📅", "Prazo"),
            "procedimento": ("🏥", "Procedimento"),
            "especialidade": ("👨‍⚕️", "Especialidade"),
            "convenio": ("📋", "Convênio"),
            "objetivo": ("🎯", "Objetivo"),
            "plano_interesse": ("💪", "Plano"),
            "curso": ("📚", "Curso"),
            "servico": ("🔧", "Serviço"),
            "produto": ("📦", "Produto"),
        }

        for field, (emoji, label) in field_mappings.items():
            value = lead.custom_data.get(field)
            if value:
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                custom_lines.append(f"{emoji} *{label}:* {value}")

        if custom_lines:
            lines.append("")
            lines.append("📋 *Informações coletadas:*")
            lines.extend(custom_lines)

    if lead.summary and include_conversation:
        summary_text = lead.summary[:max_summary_length]
        if len(lead.summary) > max_summary_length:
            summary_text += "..."
        lines.append("")
        lines.append(f"🤖 *Resumo da IA:*")
        lines.append(summary_text)

    return "\n".join(lines)


# =============================================================================
# BUILD WHATSAPP MESSAGES
# =============================================================================

async def build_whatsapp_notification_message(
    db: AsyncSession,
    lead: Lead,
    notification_type: str,
    tenant: Tenant,
    product: Any = None,
    extra_context: Dict[str, Any] = None,
) -> str:
    """Constrói mensagem de notificação WhatsApp."""
    extra_context = extra_context or {}

    headers = {
        "lead_hot": "🔥 *Lead Quente!*",
        "lead_new": "🔥 *Novo Lead!*",
        "lead_product": "📦 *Novo Interesse em Produto!*",
        "lead_out_of_hours": "🌙 *Lead Fora do Horário!*",
        "handoff_requested": "🙋 *Lead Pediu Atendente!*",
        "lead_assigned": "👋 *Você recebeu um novo lead!*",
    }

    header = headers.get(notification_type, "📢 *Notificação*")
    company_name = tenant.name or "Empresa"

    lines = [
        header,
        f"🏷️ {company_name}",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    lines.append(build_lead_summary_text(lead, include_conversation=False))

    if product:
        lines.append("")
        lines.append(f"📦 *Produto/Serviço:* {product.name}")
        if hasattr(product, 'attributes') and product.attributes:
             # Se for imobiliário, pode ter bairro nos atributos
             bairro = product.attributes.get('bairro')
             if bairro:
                 lines.append(f"📍 *Bairro:* {bairro}")

    lines.append("")
    lines.append("💬 *O QUE O CLIENTE DISSE:*")
    lines.append("─────────────────")
    
    conversation_excerpt = await build_conversation_excerpt(db, lead.id, max_messages=4)
    lines.append(conversation_excerpt)
    
    lines.append("─────────────────")

    lines.append("")
    lines.append(f"🕐 *Recebido:* {format_datetime_br(lead.created_at)}")

    lines.append("━━━━━━━━━━━━━━━━━━━━")

    if notification_type == "lead_assigned":
        lines.append("_Clique no número acima para iniciar atendimento_")
    else:
        lines.append("_Acesse o painel para mais detalhes_")

    return "\n".join(lines)


async def build_seller_notification_message(
    db: AsyncSession,
    lead: Lead,
    seller: Seller,
    tenant: Tenant,
    assigned_by: str = "Gestor",
    notes: str = None,
) -> str:
    """Constrói mensagem de notificação para o VENDEDOR."""
    company_name = tenant.name or "Empresa"

    lines = [
        "👋 *Você recebeu um novo lead!*",
        f"🏷️ {company_name}",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    lines.append(f"👤 *Nome:* {lead.name or 'Não informado'}")
    lines.append(f"📱 *WhatsApp:* {format_phone_display(lead.phone)}")

    if lead.email:
        lines.append(f"📧 *Email:* {lead.email}")

    if lead.city:
        lines.append(f"📍 *Cidade:* {lead.city}")

    # Imóvel de interesse
    if lead.custom_data and lead.custom_data.get("imovel_portal"):
        imovel = lead.custom_data.get("imovel_portal", {})

        lines.append("")
        lines.append("🏠 *IMÓVEL DE INTERESSE:*")

        codigo = imovel.get("codigo")
        if codigo:
            lines.append(f"   📋 *Código:* [{codigo}]")

        tipo = imovel.get("tipo", "Imóvel")
        quartos = imovel.get("quartos")
        banheiros = imovel.get("banheiros")

        caracteristicas = []
        if quartos:
            caracteristicas.append(f"{quartos} quartos")
        if banheiros:
            caracteristicas.append(f"{banheiros} banheiros")

        if caracteristicas:
            lines.append(f"   🏘️ {tipo} - {', '.join(caracteristicas)}")
        else:
            lines.append(f"   🏘️ {tipo}")

        valor = imovel.get("valor")
        if valor:
            lines.append(f"   💰 *Valor:* R$ {valor:,.2f}".replace(",", "."))

    # Orçamento
    if lead.custom_data:
        orcamento = (
            lead.custom_data.get("orcamento") or
            lead.custom_data.get("budget") or
            lead.custom_data.get("budget_range")
        )
        if orcamento:
            lines.append("")
            lines.append(f"💰 *Orçamento do Lead:* R$ {orcamento}")

        prazo = (
            lead.custom_data.get("prazo") or
            lead.custom_data.get("urgencia") or
            lead.custom_data.get("urgency_level")
        )
        if prazo:
            lines.append(f"⏰ *Urgência:* {prazo}")

    # Conversa
    lines.append("")
    lines.append("💬 *CONVERSA COM O CLIENTE:*")
    lines.append("─────────────────")
    
    conversation_excerpt = await build_conversation_excerpt(db, lead.id, max_messages=6)
    lines.append(conversation_excerpt)
    
    lines.append("─────────────────")

    if notes:
        lines.append("")
        lines.append(f"📌 *Observação do gestor:*")
        lines.append(notes)

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"✅ *Atribuído por:* {assigned_by}")
    lines.append(f"🕐 *Data:* {format_datetime_br(datetime.now(timezone.utc))}")
    lines.append("")
    lines.append("_Clique no link abaixo para iniciar o atendimento!_")

    if lead.phone:
        whatsapp_number = format_phone_whatsapp(lead.phone)
        lines.append("")
        lines.append(f"👉 https://wa.me/{whatsapp_number}")

    return "\n".join(lines)


# =============================================================================
# ENVIO WHATSAPP VIA Z-API
# =============================================================================

async def get_zapi_client_for_tenant(
    db: AsyncSession,
    tenant: Tenant,
) -> Optional[ZAPIService]:
    """Obtém cliente Z-API configurado para o tenant."""

    result = await db.execute(
        select(Channel)
        .where(Channel.tenant_id == tenant.id)
        .where(Channel.type == "whatsapp")
        .where(Channel.active == True)
    )
    channel = result.scalar_one_or_none()

    if channel and channel.config:
        instance_id = channel.config.get("instance_id") or channel.config.get("zapi_instance_id")
        token = channel.config.get("token") or channel.config.get("zapi_token")
        client_token = channel.config.get("client_token") or channel.config.get("zapi_client_token")

        if instance_id and token:
            logger.info(f"Z-API: Usando credenciais do canal {channel.id}")
            return ZAPIService(instance_id=instance_id, token=token, client_token=client_token)

    settings = tenant.settings or {}
    zapi_config = settings.get("zapi", {}) or settings.get("whatsapp", {})

    instance_id = zapi_config.get("instance_id") or zapi_config.get("zapi_instance_id")
    token = zapi_config.get("token") or zapi_config.get("zapi_token")
    client_token = zapi_config.get("client_token") or zapi_config.get("zapi_client_token")

    if instance_id and token:
        logger.info(f"Z-API: Usando credenciais dos settings do tenant {tenant.slug}")
        return ZAPIService(instance_id=instance_id, token=token, client_token=client_token)

    logger.info(f"Z-API: Usando credenciais globais (env vars)")
    return get_zapi_client()


async def send_whatsapp_zapi(
    db: AsyncSession,
    to_phone: str,
    message: str,
    tenant: Tenant,
) -> Dict[str, Any]:
    """Envia mensagem WhatsApp via Z-API."""
    try:
        zapi = await get_zapi_client_for_tenant(db, tenant)

        if not zapi or not zapi.is_configured():
            logger.warning(f"Z-API não configurado para tenant {tenant.slug}")
            return {"success": False, "error": "Z-API não configurado"}

        to_number = format_phone_whatsapp(to_phone)
        if not to_number:
            return {"success": False, "error": "Número de destino inválido"}

        result = await zapi.send_text(
            phone=to_number,
            message=message,
            delay_message=2
        )

        if result.get("success"):
            message_id = result.get("data", {}).get("messageId", "")
            logger.info(f"✅ WhatsApp enviado para {to_number[:8]}***: {message_id}")
            return {"success": True, "message_id": message_id}
        else:
            error = result.get("error", "Erro desconhecido")
            logger.error(f"❌ Erro Z-API: {error}")
            return {"success": False, "error": error}

    except Exception as e:
        logger.error(f"❌ Erro enviando WhatsApp: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# FUNÇÕES PRINCIPAIS DE NOTIFICAÇÃO
# =============================================================================

async def create_panel_notification(
    db: AsyncSession,
    tenant_id: int,
    notification_type: str,
    lead: Lead,
    title: str = None,
    message: str = None,
    product: Any = None,
) -> Notification:
    """Cria notificação no painel (banco de dados)."""

    default_titles = {
        "lead_hot": "🔥 Lead Quente!",
        "lead_new": "🔥 Novo Lead",
        "lead_product": f"📦 Interesse no {product.name if product else 'Produto'}",
        "lead_out_of_hours": "🌙 Lead Fora do Horário",
        "handoff_requested": "🙋 Lead Pediu Atendente",
        "handoff_completed": "✅ Lead Transferido",
        "lead_assigned": "👤 Lead Atribuído",
    }

    default_messages = {
        "lead_hot": f"{lead.name or 'Lead'} está muito interessado!",
        "lead_new": f"Novo lead: {lead.name or lead.phone or 'Não identificado'}",
        "lead_product": f"Lead interessado no {product.name if product else 'produto'}",
        "lead_out_of_hours": f"{lead.name or 'Lead'} entrou em contato fora do horário",
        "handoff_requested": f"{lead.name or 'Lead'} quer falar com atendente",
        "handoff_completed": f"{lead.name or 'Lead'} foi transferido",
        "lead_assigned": f"{lead.name or 'Lead'} foi atribuído a um vendedor",
    }

    notification = Notification(
        tenant_id=tenant_id,
        type=notification_type,
        title=title or default_titles.get(notification_type, "📢 Notificação"),
        message=message or default_messages.get(notification_type, "Nova notificação"),
        reference_type="lead",
        reference_id=lead.id,
        read=False,
    )

    db.add(notification)
    logger.info(f"📢 Notificação criada no painel: {notification_type} - Lead {lead.id}")

    return notification


async def notify_gestor_whatsapp(
    db: AsyncSession,
    tenant: Tenant,
    lead: Lead,
    notification_type: str,
    product: Any = None,
    extra_context: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Envia notificação WhatsApp para o gestor via Z-API."""

    manager_whatsapp = None

    if product and hasattr(product, 'whatsapp_notification'):
        manager_whatsapp = product.whatsapp_notification

    if not manager_whatsapp:
        settings = tenant.settings or {}
        handoff_config = settings.get("handoff", {})
        manager_whatsapp = handoff_config.get("manager_whatsapp")

    if not manager_whatsapp:
        logger.warning(f"WhatsApp do gestor não configurado para tenant {tenant.slug}")
        return {"success": False, "error": "WhatsApp do gestor não configurado"}

    message = await build_whatsapp_notification_message(
        db=db,
        lead=lead,
        notification_type=notification_type,
        tenant=tenant,
        product=product,
        extra_context=extra_context,
    )

    result = await send_whatsapp_zapi(db, manager_whatsapp, message, tenant)

    if result["success"]:
        logger.info(f"📲 WhatsApp enviado para gestor: {manager_whatsapp[:8]}***")

    return result


async def notify_seller_whatsapp(
    db: AsyncSession,
    tenant: Tenant,
    lead: Lead,
    seller: Seller,
    assigned_by: str = "Gestor",
    notes: str = None,
) -> Dict[str, Any]:
    """Envia notificação WhatsApp para o VENDEDOR."""

    seller_phone = None
    if hasattr(seller, 'whatsapp') and seller.whatsapp:
        seller_phone = seller.whatsapp
    elif hasattr(seller, 'phone') and seller.phone:
        seller_phone = seller.phone

    if not seller_phone:
        logger.warning(f"Vendedor {seller.name} (ID: {seller.id}) não tem WhatsApp cadastrado")
        return {"success": False, "error": "Vendedor sem WhatsApp cadastrado"}

    # ✨ NOVO: Suporta formato conciso OU formato completo
    settings = tenant.settings or {}
    use_concise_format = settings.get("notifications", {}).get("use_concise_format", True)  # Default = True (novo formato)
    
    if use_concise_format:
        message = await build_concise_seller_notification(
            db=db,
            lead=lead,
            seller=seller,
            tenant=tenant,
            assigned_by=assigned_by,
            notes=notes,
        )
    else:
        message = await build_seller_notification_message(
            db=db,
            lead=lead,
            seller=seller,
            tenant=tenant,
            assigned_by=assigned_by,
            notes=notes,
        )

    result = await send_whatsapp_zapi(db, seller_phone, message, tenant)

    if result["success"]:
        logger.info(f"📲 WhatsApp enviado para vendedor {seller.name}: {seller_phone[:8]}***")
    else:
        logger.error(f"❌ Falha ao enviar WhatsApp para vendedor {seller.name}: {result.get('error')}")

    return result


# =============================================================================
# ✨ NOVA VERSÃO CONCISA DE NOTIFICAÇÕES
# =============================================================================

async def extract_conversation_insights(
    db: AsyncSession,
    lead_id: int,
) -> dict:
    """
    Extrai INSIGHTS da conversa ao invés de transcrição completa.
    
    Returns:
        {
            "origem": "Portal de Investimento",
            "pediu": "Mais detalhes sobre o imóvel",
            "pendentes": ["finalidade (morar/investir)", "timing de mudança"],
            "follow_ups_enviados": 1
        }
    """
    try:
        result = await db.execute(
            select(Message)
            .where(Message.lead_id == lead_id)
            .order_by(Message.created_at.asc())
        )
        messages = result.scalars().all()
        
        if not messages:
            return {
                "origem": "Desconhecida",
                "pediu": "Informações não disponíveis",
                "pendentes": [],
                "follow_ups_enviados": 0
            }
        
        # Conta follow-ups automáticos
        follow_ups = sum(1 for m in messages if m.role == "assistant" and "[FOLLOW-UP" in (m.content or ""))
        
        # Primeira mensagem do usuário (origem do contato)
        first_user_msg = next((m.content for m in messages if m.role == "user"), "")
        origem = "Contato direto"
        
        if "portal" in first_user_msg.lower():
            origem = "Portal de Investimento"
        elif "site" in first_user_msg.lower() or "website" in first_user_msg.lower():
            origem = "Website"
        elif "instagram" in first_user_msg.lower() or "insta" in first_user_msg.lower():
            origem = "Instagram"
        elif "facebook" in first_user_msg.lower():
            origem = "Facebook"
        elif "indicação" in first_user_msg.lower():
            origem = "Indicação"
        
        # O que o lead pediu/quis (primeira mensagem resumida)
        pediu = "Informações gerais"
        if len(first_user_msg) > 0:
            # Extrai intent principal
            if "detalhes" in first_user_msg.lower() or "informações" in first_user_msg.lower():
                pediu = "Mais detalhes sobre o imóvel"
            elif "visita" in first_user_msg.lower():
                pediu = "Agendar visita"
            elif "disponível" in first_user_msg.lower() or "disponibilidade" in first_user_msg.lower():
                pediu = "Verificar disponibilidade"
            elif "valor" in first_user_msg.lower() or "preço" in first_user_msg.lower():
                pediu = "Informações sobre valor"
            elif "financiamento" in first_user_msg.lower():
                pediu = "Informações sobre financiamento"
            else:
                # Pega primeiras palavras relevantes
                palavras = first_user_msg.split()[:15]
                pediu = " ".join(palavras)
                if len(first_user_msg.split()) > 15:
                    pediu += "..."
        
        # Identifica informações pendentes (perguntas da IA não respondidas)
        pendentes = []
        
        # Analisa últimas mensagens da IA buscando perguntas não respondidas
        ia_messages = [m for m in messages if m.role == "assistant"]
        if ia_messages:
            last_ia_msg = ia_messages[-1].content.lower()
            
            # Detecta perguntas comuns não respondidas
            if "?" in last_ia_msg:
                if "morar" in last_ia_msg or "investir" in last_ia_msg:
                    pendentes.append("finalidade (morar/investir)")
                if "mudar" in last_ia_msg or "quando" in last_ia_msg:
                    pendentes.append("timing de mudança")
                if "orçamento" in last_ia_msg or "quanto" in last_ia_msg:
                    pendentes.append("orçamento disponível")
                if "financiamento" in last_ia_msg:
                    pendentes.append("necessidade de financiamento")
                if "visita" in last_ia_msg:
                    pendentes.append("interesse em visitar")
        
        return {
            "origem": origem,
            "pediu": pediu,
            "pendentes": pendentes,
            "follow_ups_enviados": follow_ups
        }
        
    except Exception as e:
        logger.error(f"Erro ao extrair insights da conversa: {e}")
        return {
            "origem": "Erro ao processar",
            "pediu": "Informações não disponíveis",
            "pendentes": [],
            "follow_ups_enviados": 0
        }


async def build_concise_seller_notification(
    db: AsyncSession,
    lead: Lead,
    seller: Seller,
    tenant: Tenant,
    assigned_by: str = "Gestor",
    notes: str = None,
) -> str:
    """
    ✨ VERSÃO CONCISA E OTIMIZADA
    
    Formato: Conciso, escaneável, orientado à ação.
    Reduz de ~15 linhas para ~10 linhas, mantendo todas as informações críticas.
    """
    company_name = tenant.name or "Empresa"
    
    # Extrai insights ao invés de transcrição completa
    insights = await extract_conversation_insights(db, lead.id)
    
    # Header
    lines = [
        "🔥 NOVO LEAD - " + company_name,
        "",
    ]
    
    # Dados principais do lead
    lines.append(f"👤 {lead.name or 'Não informado'} | 📱 {format_phone_display(lead.phone)}")
    
    # Seção: INTERESSE (imóvel ou serviço)
    if lead.custom_data and lead.custom_data.get("imovel_portal"):
        imovel = lead.custom_data.get("imovel_portal", {})
        
        lines.append("")
        lines.append("🏠 INTERESSE")
        
        # Monta descrição compacta do imóvel
        tipo = imovel.get("tipo", "Imóvel")
        quartos = imovel.get("quartos")
        banheiros = imovel.get("banheiros")
        codigo = imovel.get("codigo")
        valor = imovel.get("valor")
        
        caracteristicas = []
        if quartos:
            caracteristicas.append(f"{quartos}Q")
        if banheiros:
            caracteristicas.append(f"{banheiros}B")
        
        desc_imovel = tipo
        if caracteristicas:
            desc_imovel += " " + "/".join(caracteristicas)
        
        if codigo:
            lines.append(f"{desc_imovel} | Cód. [{codigo}]")
        else:
            lines.append(desc_imovel)
        
        if valor:
            lines.append(f"💰 R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        
        # Localização
        if imovel.get("endereco"):
            lines.append(f"📍 {imovel.get('endereco')}")
        elif lead.city:
            lines.append(f"📍 {lead.city}")
    
    # Seção: CONTEXTO DO LEAD
    lines.append("")
    lines.append("⚡ CONTEXTO DO LEAD")
    lines.append(f"• Origem: {insights['origem']}")
    lines.append(f"• {insights['pediu']}")
    
    # Informações pendentes
    if insights['pendentes']:
        pendentes_text = ", ".join(insights['pendentes'])
        lines.append(f"• ⚠️ Não informou: {pendentes_text}")
    
    # Follow-ups enviados
    if insights['follow_ups_enviados'] > 0:
        lines.append(f"• 🔁 Follow-ups automáticos enviados: {insights['follow_ups_enviados']}")
    
    # Observações do gestor
    if notes:
        lines.append(f"• 🔴 Observação: {notes}")
    
    # Footer
    lines.append("")
    lines.append(f"📅 Atribuído por {assigned_by} em {format_datetime_br(datetime.now(timezone.utc))}")
    
    # Link WhatsApp
    if lead.phone:
        whatsapp_number = format_phone_whatsapp(lead.phone)
        lines.append(f"👉 https://wa.me/{whatsapp_number}")
    
    return "\n".join(lines)


# =============================================================================
# ✅ FUNÇÕES COM PUSH NOTIFICATION INTEGRADO
# =============================================================================

async def notify_gestor(
    db: AsyncSession,
    tenant: Tenant,
    lead: Lead,
    notification_type: str,
    product: Any = None,
    extra_context: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Notifica o gestor via:
    1. Painel (banco de dados)
    2. WhatsApp (Z-API)
    3. Push Notification (Web Push) ← NOVO!
    """
    results = {"panel": False, "whatsapp": False, "push": False}

    try:
        # 1. Cria notificação no painel
        await create_panel_notification(
            db=db,
            tenant_id=tenant.id,
            notification_type=notification_type,
            lead=lead,
            product=product,
        )
        results["panel"] = True

        # 2. Envia WhatsApp para gestor via Z-API
        whatsapp_result = await notify_gestor_whatsapp(
            db=db,
            tenant=tenant,
            lead=lead,
            notification_type=notification_type,
            product=product,
            extra_context=extra_context,
        )
        results["whatsapp"] = whatsapp_result.get("success", False)

        # 3. ✅ NOVO: Envia Push Notification
        try:
            push_titles = {
                "lead_hot": "🔥 Lead Quente!",
                "lead_new": "🔔 Novo Lead!",
                "lead_product": f"📦 Lead do {product.name if product else 'Produto'}",
                "lead_out_of_hours": "🌙 Lead Fora do Horário!",
                "handoff_requested": "🙋 Lead Pediu Atendente!",
            }

            push_bodies = {
                "lead_hot": f"{lead.name or 'Lead'} está muito interessado!",
                "lead_new": f"Novo lead: {lead.name or lead.phone or 'Não identificado'}",
                "lead_product": f"{lead.name or 'Lead'} interessado no {product.name if product else 'produto'}",
                "lead_out_of_hours": f"{lead.name or 'Lead'} entrou em contato fora do horário",
                "handoff_requested": f"{lead.name or 'Lead'} quer falar com atendente",
            }

            push_payload = PushNotificationPayload(
                title=push_titles.get(notification_type, "🔔 Nova Notificação"),
                body=push_bodies.get(notification_type, f"Lead: {lead.name or lead.phone}"),
                tag=f"{notification_type}-{lead.id}",
                url=f"/dashboard/leads?lead={lead.id}",
                require_interaction=notification_type in ["lead_hot", "handoff_requested"],
                data={
                    "lead_id": lead.id,
                    "type": notification_type,
                    "tenant_id": tenant.id,
                },
            )

            push_result = await send_push_to_tenant(
                db=db,
                tenant_id=tenant.id,
                payload=push_payload,
            )

            results["push"] = push_result.get("sent", 0) > 0
            
            if results["push"]:
                logger.info(f"📲 Push enviado: {push_result.get('sent')} dispositivos")

        except Exception as push_error:
            logger.warning(f"⚠️ Erro ao enviar push (não crítico): {push_error}")
            results["push"] = False

    except Exception as e:
        logger.error(f"Erro notificando gestor: {e}")

    return results


async def notify_seller(
    db: AsyncSession,
    tenant: Tenant,
    lead: Lead,
    seller: Seller,
    assigned_by: str = "Gestor",
    notes: str = None,
) -> Dict[str, Any]:
    """
    Notifica o vendedor via:
    1. Painel (banco de dados)
    2. WhatsApp (Z-API)
    3. Push Notification (Web Push) ← NOVO!
    """
    results = {"panel": False, "whatsapp": False, "push": False, "whatsapp_error": None}

    try:
        # 1. Cria notificação no painel
        await create_panel_notification(
            db=db,
            tenant_id=tenant.id,
            notification_type="lead_assigned",
            lead=lead,
            title=f"👤 Lead atribuído para {seller.name}",
            message=f"{lead.name or 'Lead'} foi atribuído para {seller.name}",
        )
        results["panel"] = True

        # 2. Envia WhatsApp para vendedor via Z-API
        whatsapp_result = await notify_seller_whatsapp(
            db=db,
            tenant=tenant,
            lead=lead,
            seller=seller,
            assigned_by=assigned_by,
            notes=notes,
        )
        results["whatsapp"] = whatsapp_result.get("success", False)
        if not results["whatsapp"]:
            results["whatsapp_error"] = whatsapp_result.get("error")

        # 3. ✅ NOVO: Envia Push Notification para o vendedor
        try:
            if hasattr(seller, 'user_id') and seller.user_id:
                push_payload = PushNotificationPayload(
                    title="👋 Novo Lead para você!",
                    body=f"Você recebeu o lead: {lead.name or lead.phone or 'Não identificado'}",
                    tag=f"lead-assigned-{lead.id}",
                    url=f"/dashboard/leads?lead={lead.id}",
                    require_interaction=True,
                    data={
                        "lead_id": lead.id,
                        "type": "lead_assigned",
                        "seller_id": seller.id,
                    },
                )

                push_result = await send_push_to_user(
                    db=db,
                    user_id=seller.user_id,
                    payload=push_payload,
                )

                results["push"] = push_result.get("sent", 0) > 0
                
                if results["push"]:
                    logger.info(f"📲 Push enviado para vendedor {seller.name}")

        except Exception as push_error:
            logger.warning(f"⚠️ Erro ao enviar push para vendedor (não crítico): {push_error}")
            results["push"] = False

    except Exception as e:
        logger.error(f"Erro notificando vendedor: {e}")
        results["whatsapp_error"] = str(e)

    return results


# =============================================================================
# ATALHOS (MANTIDOS PARA COMPATIBILIDADE)
# =============================================================================

async def notify_lead_hot(
    db: AsyncSession,
    tenant: Tenant,
    lead: Lead,
    product: Any = None,
) -> Dict[str, Any]:
    """Atalho para notificar lead quente."""
    return await notify_gestor(
        db=db,
        tenant=tenant,
        lead=lead,
        notification_type="lead_hot",
        product=product,
    )


async def notify_lead_product(
    db: AsyncSession,
    tenant: Tenant,
    lead: Lead,
    product: Any,
) -> Dict[str, Any]:
    """Atalho para notificar lead de produto específico."""
    return await notify_gestor(
        db=db,
        tenant=tenant,
        lead=lead,
        notification_type="lead_product",
        product=product,
    )


async def notify_out_of_hours(
    db: AsyncSession,
    tenant: Tenant,
    lead: Lead,
) -> Dict[str, Any]:
    """Atalho para notificar lead fora do horário."""
    return await notify_gestor(
        db=db,
        tenant=tenant,
        lead=lead,
        notification_type="lead_out_of_hours",
    )


async def notify_handoff_requested(
    db: AsyncSession,
    tenant: Tenant,
    lead: Lead,
    reason: str = None,
) -> Dict[str, Any]:
    """Atalho para notificar quando lead pede para falar com humano."""
    return await notify_gestor(
        db=db,
        tenant=tenant,
        lead=lead,
        notification_type="handoff_requested",
        extra_context={"reason": reason} if reason else None,
    )