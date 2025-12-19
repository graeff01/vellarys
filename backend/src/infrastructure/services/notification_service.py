"""
NOTIFICATION SERVICE (Z-API)
============================

Serviço centralizado de notificações do Velaris.
ATUALIZADO: Usa Z-API para enviar WhatsApp (não 360Dialog)

Responsabilidades:
- Notificar gestor via WhatsApp quando lead quente
- Notificar gestor via WhatsApp quando lead fora do horário
- Notificar vendedor via WhatsApp quando receber lead atribuído
- Criar notificações no painel (Notification entity)
- Evitar spam (não repetir notificações)

Funciona para TODOS os nichos (imobiliário, saúde, fitness, educação, etc).

MODIFICAÇÃO: Removida qualificação (quente/frio) da mensagem do vendedor
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Tenant, Lead, Notification, Seller, Message, Channel
from src.infrastructure.services.zapi_service import ZAPIService, get_zapi_client

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES
# =============================================================================

NOTIFICATION_TYPES = {
    "lead_new": "Novo Lead",
    "lead_hot": "Lead Quente",
    "lead_empreendimento": "Lead Empreendimento",
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

    # Remove caracteres não numéricos
    digits = ''.join(filter(str.isdigit, phone))

    # Formato brasileiro: (XX) XXXXX-XXXX
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

    # Adiciona 55 se não tiver
    if len(digits) == 11:
        digits = "55" + digits

    return digits


def format_datetime_br(dt: datetime) -> str:
    """Formata datetime para formato brasileiro."""
    if not dt:
        return "Não informado"

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # Converte para horário de Brasília (UTC-3)
    dt_br = dt - timedelta(hours=3)

    return dt_br.strftime("%d/%m/%Y às %H:%M")


def get_qualification_display(qualification: str) -> str:
    """Retorna emoji + label da qualificação."""
    qual = (qualification or "frio").lower()
    emoji = QUALIFICATION_EMOJIS.get(qual, "❓")
    label = QUALIFICATION_LABELS.get(qual, qualification)
    return f"{emoji} {label}"


# =============================================================================
# BUILD LEAD SUMMARY (UNIVERSAL - TODOS OS NICHOS)
# =============================================================================

def build_lead_summary_text(
    lead: Lead,
    include_conversation: bool = False,
    max_summary_length: int = 500,
) -> str:
    """
    Constrói texto resumido do lead para notificações.

    Funciona para qualquer nicho - extrai dados genéricos do custom_data.
    """
    lines = []

    # Dados básicos (universais)
    if lead.name:
        lines.append(f"👤 *Nome:* {lead.name}")

    if lead.phone:
        lines.append(f"📱 *WhatsApp:* {format_phone_display(lead.phone)}")

    if lead.email:
        lines.append(f"📧 *Email:* {lead.email}")

    if lead.city:
        lines.append(f"📍 *Cidade:* {lead.city}")

    # Qualificação
    if lead.qualification:
        lines.append(f"📊 *Qualificação:* {get_qualification_display(lead.qualification)}")

    # Fonte/Campanha
    if lead.source and lead.source != "organico":
        lines.append(f"📢 *Origem:* {lead.source}")

    if lead.campaign:
        lines.append(f"🎯 *Campanha:* {lead.campaign}")

    # Custom data (dados específicos do nicho - extraídos dinamicamente)
    if lead.custom_data:
        custom_lines = []

        # Campos comuns que podem existir em qualquer nicho
        field_mappings = {
            # Imobiliário
            "empreendimento_nome": ("🏢", "Empreendimento"),
            "interesse": ("🏠", "Interesse"),
            "tipologia": ("🛏️", "Tipologia"),
            "budget_range": ("💰", "Orçamento"),
            "urgency_level": ("⏰", "Urgência"),
            "prazo": ("📅", "Prazo"),

            # Saúde
            "procedimento": ("🏥", "Procedimento"),
            "especialidade": ("👨‍⚕️", "Especialidade"),
            "convenio": ("📋", "Convênio"),
            "sintomas": ("🩺", "Sintomas"),

            # Fitness
            "objetivo": ("🎯", "Objetivo"),
            "plano_interesse": ("💪", "Plano"),
            "horario_preferido": ("🕐", "Horário"),
            "experiencia": ("📈", "Experiência"),

            # Educação
            "curso": ("📚", "Curso"),
            "turma": ("👥", "Turma"),
            "nivel": ("🎓", "Nível"),
            "modalidade": ("💻", "Modalidade"),

            # Genéricos
            "servico": ("🔧", "Serviço"),
            "produto": ("📦", "Produto"),
            "observacoes": ("📝", "Observações"),
            "preferencias": ("⭐", "Preferências"),
            "pain_points": ("😟", "Dores"),
            "objections": ("🤔", "Objeções"),
            "buying_signals": ("💡", "Sinais de Compra"),
        }

        for field, (emoji, label) in field_mappings.items():
            value = lead.custom_data.get(field)
            if value:
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                custom_lines.append(f"{emoji} *{label}:* {value}")

        if custom_lines:
            lines.append("")  # Linha em branco
            lines.append("📋 *Informações coletadas:*")
            lines.extend(custom_lines)

    # Summary da IA (se existir)
    if lead.summary and include_conversation:
        summary_text = lead.summary[:max_summary_length]
        if len(lead.summary) > max_summary_length:
            summary_text += "..."
        lines.append("")
        lines.append(f"💬 *Resumo:*")
        lines.append(summary_text)

    return "\n".join(lines)


# =============================================================================
# BUILD WHATSAPP MESSAGES (UNIVERSAL)
# =============================================================================

def build_whatsapp_notification_message(
    lead: Lead,
    notification_type: str,
    tenant: Tenant,
    empreendimento: Any = None,
    extra_context: Dict[str, Any] = None,
) -> str:
    """
    Constrói mensagem de notificação WhatsApp.

    Funciona para qualquer nicho.
    """
    extra_context = extra_context or {}

    # Header baseado no tipo
    headers = {
        "lead_hot": "🔥 *Lead Quente!*",
        "lead_new": "📥 *Novo Lead!*",
        "lead_empreendimento": "🏢 *Lead de Empreendimento!*",
        "lead_out_of_hours": "🌙 *Lead Fora do Horário!*",
        "handoff_requested": "🙋 *Lead Pediu Atendente!*",
        "lead_assigned": "👋 *Você recebeu um novo lead!*",
    }

    header = headers.get(notification_type, "📢 *Notificação*")

    # Nome da empresa
    company_name = tenant.name or "Empresa"

    lines = [
        header,
        f"🏷️ {company_name}",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    # Dados do lead
    lines.append(build_lead_summary_text(lead, include_conversation=True))

    # Info do empreendimento (se tiver - específico imobiliário)
    if empreendimento:
        lines.append("")
        lines.append(f"🏢 *Empreendimento:* {empreendimento.nome}")
        if hasattr(empreendimento, 'bairro') and empreendimento.bairro:
            lines.append(f"📍 *Bairro:* {empreendimento.bairro}")

    # Timestamp
    lines.append("")
    lines.append(f"🕐 *Recebido:* {format_datetime_br(lead.created_at)}")

    # Footer
    lines.append("━━━━━━━━━━━━━━━━━━━━")

    # Call to action baseado no tipo
    if notification_type == "lead_assigned":
        lines.append("_Clique no número acima para iniciar atendimento_")
    else:
        lines.append("_Acesse o painel para mais detalhes_")

    return "\n".join(lines)



def build_seller_notification_message(
    lead: Lead,
    seller: Seller,
    tenant: Tenant,
    assigned_by: str = "Gestor",
    notes: str = None,
) -> str:
    """
    Constrói mensagem de notificação para o VENDEDOR quando recebe um lead.

    ATUALIZADO: Inclui código do imóvel, orçamento e prazo
    
    Funciona para qualquer nicho.
    """
    company_name = tenant.name or "Empresa"

    lines = [
        "👋 *Você recebeu um novo lead!*",
        f"🏷️ {company_name}",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    # Dados principais do lead
    lines.append(f"👤 *Nome:* {lead.name or 'Não informado'}")
    lines.append(f"📱 *WhatsApp:* {format_phone_display(lead.phone)}")

    if lead.email:
        lines.append(f"📧 *Email:* {lead.email}")

    if lead.city:
        lines.append(f"📍 *Cidade:* {lead.city}")

    # ========================================
    # NOVO: INFORMAÇÕES DO IMÓVEL (se tiver)
    # ========================================
    if lead.custom_data and lead.custom_data.get("imovel_portal"):
        imovel = lead.custom_data.get("imovel_portal", {})
        
        lines.append("")
        lines.append("🏠 *IMÓVEL DE INTERESSE:*")
        
        # Código do imóvel (CRÍTICO!)
        codigo = imovel.get("codigo")
        if codigo:
            lines.append(f"   📋 *Código:* [{codigo}]")
        
        # Tipo e características
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
        
        # Endereço
        endereco = imovel.get("endereco")
        bairro = imovel.get("bairro")
        cidade = imovel.get("cidade")
        
        if endereco or bairro:
            loc_parts = []
            if endereco:
                loc_parts.append(endereco)
            if bairro:
                loc_parts.append(bairro)
            if cidade:
                loc_parts.append(cidade)
            lines.append(f"   📍 {', '.join(loc_parts)}")
        
        # Valor
        valor = imovel.get("valor")
        if valor:
            lines.append(f"   💰 *Valor:* R$ {valor:,.2f}".replace(",", "."))
        
        # Metragem
        metragem = imovel.get("metragem")
        if metragem:
            lines.append(f"   📐 {metragem}m²")

    # ========================================
    # NOVO: ORÇAMENTO DO LEAD
    # ========================================
    orcamento = None
    if lead.custom_data:
        # Tenta várias formas de capturar orçamento
        orcamento = (
            lead.custom_data.get("orcamento") or 
            lead.custom_data.get("budget") or
            lead.custom_data.get("budget_range") or
            lead.custom_data.get("valor_disponivel")
        )
    
    if orcamento:
        lines.append("")
        lines.append(f"💰 *Orçamento do Lead:* R$ {orcamento}")

    # ========================================
    # NOVO: PRAZO/URGÊNCIA
    # ========================================
    prazo = None
    if lead.custom_data:
        prazo = (
            lead.custom_data.get("prazo") or
            lead.custom_data.get("urgencia") or
            lead.custom_data.get("urgency_level") or
            lead.custom_data.get("prazo_mudanca")
        )
    
    if prazo:
        lines.append(f"⏰ *Urgência:* {prazo}")

    # ========================================
    # Outras informações coletadas
    # ========================================
    if lead.custom_data:
        collected_info = []

        # Mapeia campos importantes (mas ignora os que já mostramos acima)
        important_fields = {
            # Imobiliário
            "empreendimento_nome": "Empreendimento",
            "interesse": "Interesse",
            "tipologia": "Tipologia",
            "finalidade": "Finalidade",

            # Saúde
            "procedimento": "Procedimento",
            "especialidade": "Especialidade",
            "convenio": "Convênio",

            # Fitness
            "objetivo": "Objetivo",
            "plano_interesse": "Plano",

            # Educação
            "curso": "Curso",

            # Genéricos
            "servico": "Serviço",
            "produto": "Produto",
        }

        for field, label in important_fields.items():
            value = lead.custom_data.get(field)
            if value:
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                collected_info.append(f"• *{label}:* {value}")

        if collected_info:
            lines.append("")
            lines.append("📋 *Outras informações:*")
            lines.extend(collected_info)

    # Resumo da conversa (muito importante pro vendedor!)
    if lead.summary:
        lines.append("")
        lines.append("💬 *Resumo da conversa:*")
        # Limita o tamanho do resumo
        summary = lead.summary[:600]
        if len(lead.summary) > 600:
            summary += "..."
        lines.append(summary)

    # Notas do gestor (se tiver)
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

    # Link direto do WhatsApp do lead
    if lead.phone:
        whatsapp_number = format_phone_whatsapp(lead.phone)
        lines.append("")
        lines.append(f"👉 https://wa.me/{whatsapp_number}")

    return "\n".join(lines)

# =============================================================================
# ENVIO WHATSAPP VIA Z-APIII
# =============================================================================

async def get_zapi_client_for_tenant(
    db: AsyncSession,
    tenant: Tenant,
) -> Optional[ZAPIService]:
    """
    Obtém cliente Z-API configurado para o tenant.
    
    Busca credenciais em:
    1. Canal WhatsApp do tenant (channel.config)
    2. Settings do tenant (tenant.settings)
    3. Variáveis de ambiente (fallback global)
    """
    
    # 1. Tenta buscar do canal WhatsApp do tenant
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
    
    # 2. Tenta buscar dos settings do tenant
    settings = tenant.settings or {}
    zapi_config = settings.get("zapi", {}) or settings.get("whatsapp", {})
    
    instance_id = zapi_config.get("instance_id") or zapi_config.get("zapi_instance_id")
    token = zapi_config.get("token") or zapi_config.get("zapi_token")
    client_token = zapi_config.get("client_token") or zapi_config.get("zapi_client_token")
    
    if instance_id and token:
        logger.info(f"Z-API: Usando credenciais dos settings do tenant {tenant.slug}")
        return ZAPIService(instance_id=instance_id, token=token, client_token=client_token)
    
    # 3. Fallback: usa credenciais globais das variáveis de ambiente
    logger.info(f"Z-API: Usando credenciais globais (env vars)")
    return get_zapi_client()


async def send_whatsapp_zapi(
    db: AsyncSession,
    to_phone: str,
    message: str,
    tenant: Tenant,
) -> Dict[str, Any]:
    """
    Envia mensagem WhatsApp via Z-API.

    Retorna: {"success": bool, "message_id": str, "error": str}
    """
    try:
        # Obtém cliente Z-API configurado
        zapi = await get_zapi_client_for_tenant(db, tenant)
        
        if not zapi or not zapi.is_configured():
            logger.warning(f"Z-API não configurado para tenant {tenant.slug}")
            return {"success": False, "error": "Z-API não configurado"}

        # Formata número destino
        to_number = format_phone_whatsapp(to_phone)
        if not to_number:
            return {"success": False, "error": "Número de destino inválido"}

        # Envia mensagem
        result = await zapi.send_text(
            phone=to_number,
            message=message,
            delay_message=2  # Pequeno delay para parecer mais natural
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
    empreendimento: Any = None,
) -> Notification:
    """Cria notificação no painel (banco de dados)."""

    # Títulos padrão por tipo
    default_titles = {
        "lead_hot": "🔥 Lead Quente!",
        "lead_new": "📥 Novo Lead",
        "lead_empreendimento": f"🏢 Lead do {empreendimento.nome if empreendimento else 'Empreendimento'}",
        "lead_out_of_hours": "🌙 Lead Fora do Horário",
        "handoff_requested": "🙋 Lead Pediu Atendente",
        "handoff_completed": "✅ Lead Transferido",
        "lead_assigned": "👤 Lead Atribuído",
    }

    # Mensagens padrão por tipo
    default_messages = {
        "lead_hot": f"{lead.name or 'Lead'} está muito interessado!",
        "lead_new": f"Novo lead: {lead.name or lead.phone or 'Não identificado'}",
        "lead_empreendimento": f"Lead interessado no {empreendimento.nome if empreendimento else 'empreendimento'}",
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
    empreendimento: Any = None,
    extra_context: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Envia notificação WhatsApp para o gestor via Z-API.

    Busca WhatsApp do gestor em:
    1. empreendimento.whatsapp_notificacao (se tiver empreendimento)
    2. tenant.settings.handoff.manager_whatsapp
    """

    # Determina número do gestor
    manager_whatsapp = None

    # Prioridade 1: WhatsApp específico do empreendimento
    if empreendimento and hasattr(empreendimento, 'whatsapp_notificacao'):
        manager_whatsapp = empreendimento.whatsapp_notificacao

    # Prioridade 2: WhatsApp do gestor no settings
    if not manager_whatsapp:
        settings = tenant.settings or {}
        handoff_config = settings.get("handoff", {})
        manager_whatsapp = handoff_config.get("manager_whatsapp")

    if not manager_whatsapp:
        logger.warning(f"WhatsApp do gestor não configurado para tenant {tenant.slug}")
        return {"success": False, "error": "WhatsApp do gestor não configurado"}

    # Monta mensagem
    message = build_whatsapp_notification_message(
        lead=lead,
        notification_type=notification_type,
        tenant=tenant,
        empreendimento=empreendimento,
        extra_context=extra_context,
    )

    # Envia via Z-API
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
    """
    Envia notificação WhatsApp para o VENDEDOR quando recebe um lead via Z-API.

    Args:
        db: Sessão do banco
        tenant: Tenant do lead
        lead: Lead atribuído
        seller: Vendedor que vai receber
        assigned_by: Nome de quem atribuiu
        notes: Observações do gestor

    Returns:
        {"success": bool, "message_id": str, "error": str}
    """

    # Verifica se vendedor tem WhatsApp
    seller_phone = None
    if hasattr(seller, 'whatsapp') and seller.whatsapp:
        seller_phone = seller.whatsapp
    elif hasattr(seller, 'phone') and seller.phone:
        seller_phone = seller.phone

    if not seller_phone:
        logger.warning(f"Vendedor {seller.name} (ID: {seller.id}) não tem WhatsApp cadastrado")
        return {"success": False, "error": "Vendedor sem WhatsApp cadastrado"}

    # Monta mensagem personalizada para o vendedor
    message = build_seller_notification_message(
        lead=lead,
        seller=seller,
        tenant=tenant,
        assigned_by=assigned_by,
        notes=notes,
    )

    # Envia via Z-API
    result = await send_whatsapp_zapi(db, seller_phone, message, tenant)

    if result["success"]:
        logger.info(f"📲 WhatsApp enviado para vendedor {seller.name}: {seller_phone[:8]}***")
    else:
        logger.error(f"❌ Falha ao enviar WhatsApp para vendedor {seller.name}: {result.get('error')}")

    return result


# =============================================================================
# FUNÇÕES DE CONVENIÊNCIA (ATALHOS)
# =============================================================================

async def notify_gestor(
    db: AsyncSession,
    tenant: Tenant,
    lead: Lead,
    notification_type: str,
    empreendimento: Any = None,
    extra_context: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Notifica o gestor via painel + WhatsApp.

    Esta é a função principal que deve ser usada.
    """
    results = {"panel": False, "whatsapp": False}

    try:
        # 1. Cria notificação no painel
        await create_panel_notification(
            db=db,
            tenant_id=tenant.id,
            notification_type=notification_type,
            lead=lead,
            empreendimento=empreendimento,
        )
        results["panel"] = True

        # 2. Envia WhatsApp para gestor via Z-API
        whatsapp_result = await notify_gestor_whatsapp(
            db=db,
            tenant=tenant,
            lead=lead,
            notification_type=notification_type,
            empreendimento=empreendimento,
            extra_context=extra_context,
        )
        results["whatsapp"] = whatsapp_result.get("success", False)

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
    Notifica o vendedor via painel + WhatsApp quando recebe um lead.

    Args:
        db: Sessão do banco
        tenant: Tenant
        lead: Lead atribuído
        seller: Vendedor que vai receber
        assigned_by: Nome de quem atribuiu
        notes: Observações do gestor

    Returns:
        {"panel": bool, "whatsapp": bool, "whatsapp_error": str}
    """
    results = {"panel": False, "whatsapp": False, "whatsapp_error": None}

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

    except Exception as e:
        logger.error(f"Erro notificando vendedor: {e}")
        results["whatsapp_error"] = str(e)

    return results


async def notify_lead_hot(
    db: AsyncSession,
    tenant: Tenant,
    lead: Lead,
    empreendimento: Any = None,
) -> Dict[str, Any]:
    """Atalho para notificar lead quente."""
    return await notify_gestor(
        db=db,
        tenant=tenant,
        lead=lead,
        notification_type="lead_hot",
        empreendimento=empreendimento,
    )


async def notify_lead_empreendimento(
    db: AsyncSession,
    tenant: Tenant,
    lead: Lead,
    empreendimento: Any,
) -> Dict[str, Any]:
    """Atalho para notificar lead de empreendimento específico."""
    return await notify_gestor(
        db=db,
        tenant=tenant,
        lead=lead,
        notification_type="lead_empreendimento",
        empreendimento=empreendimento,
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