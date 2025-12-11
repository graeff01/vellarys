"""
NOTIFICATION SERVICE
====================

Serviço centralizado de notificações do Velaris.

Responsabilidades:
- Notificar gestor via WhatsApp quando lead quente
- Notificar gestor via WhatsApp quando lead fora do horário
- Notificar vendedor via WhatsApp quando receber lead atribuído
- Criar notificações no painel (Notification entity)
- Evitar spam (não repetir notificações)

Funciona para TODOS os nichos (imobiliário, saúde, fitness, educação, etc).
"""

import logging
import httpx
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Tenant, Lead, Notification, Seller, Message

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
    "frio": "❄️",
    "morno": "🌤️",
    "quente": "🔥",
    "hot": "🔥",
}

QUALIFICATION_LABELS = {
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
    from datetime import timedelta
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
            lines.append("📝 *Informações coletadas:*")
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
        f"📍 {company_name}",
        "────────────────────",
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
    lines.append("────────────────────")
    
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
    
    Funciona para qualquer nicho.
    """
    company_name = tenant.name or "Empresa"
    
    lines = [
        "👋 *Você recebeu um novo lead!*",
        f"📍 {company_name}",
        "────────────────────",
        "",
    ]
    
    # Dados principais do lead (o vendedor precisa ver claramente)
    lines.append(f"👤 *Nome:* {lead.name or 'Não informado'}")
    lines.append(f"📱 *WhatsApp:* {format_phone_display(lead.phone)}")
    
    if lead.email:
        lines.append(f"📧 *Email:* {lead.email}")
    
    if lead.city:
        lines.append(f"📍 *Cidade:* {lead.city}")
    
    lines.append("")
    lines.append(f"📊 *Qualificação:* {get_qualification_display(lead.qualification)}")
    
    # Informações coletadas (custom_data)
    if lead.custom_data:
        collected_info = []
        
        # Mapeia campos comuns de qualquer nicho
        important_fields = {
            # Imobiliário
            "empreendimento_nome": "Empreendimento",
            "interesse": "Interesse",
            "tipologia": "Tipologia",
            "budget_range": "Orçamento",
            "prazo": "Prazo",
            
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
            "urgency_level": "Urgência",
        }
        
        for field, label in important_fields.items():
            value = lead.custom_data.get(field)
            if value:
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                collected_info.append(f"• *{label}:* {value}")
        
        if collected_info:
            lines.append("")
            lines.append("📝 *Informações coletadas:*")
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
    lines.append("────────────────────")
    lines.append(f"✅ *Atribuído por:* {assigned_by}")
    lines.append(f"🕐 *Data:* {format_datetime_br(datetime.now(timezone.utc))}")
    lines.append("")
    lines.append("_Clique no número do cliente para iniciar o atendimento!_")
    
    # Link direto do WhatsApp do lead
    if lead.phone:
        whatsapp_number = format_phone_whatsapp(lead.phone)
        lines.append("")
        lines.append(f"👉 wa.me/{whatsapp_number}")
    
    return "\n".join(lines)


# =============================================================================
# ENVIO WHATSAPP VIA 360DIALOG
# =============================================================================

async def send_whatsapp_360dialog(
    to_phone: str,
    message: str,
    tenant: Tenant,
) -> Dict[str, Any]:
    """
    Envia mensagem WhatsApp via 360Dialog API.
    
    Retorna: {"success": bool, "message_id": str, "error": str}
    """
    try:
        # Busca configurações do 360Dialog no tenant
        settings = tenant.settings or {}
        dialog_config = settings.get("dialog360", {}) or settings.get("whatsapp", {})
        
        api_key = dialog_config.get("api_key")
        phone_number_id = dialog_config.get("phone_number_id")
        
        if not api_key:
            logger.warning(f"360Dialog não configurado para tenant {tenant.slug}")
            return {"success": False, "error": "360Dialog não configurado"}
        
        # Formata número destino
        to_number = format_phone_whatsapp(to_phone)
        if not to_number:
            return {"success": False, "error": "Número de destino inválido"}
        
        # Monta payload
        url = "https://waba.360dialog.io/v1/messages"
        
        headers = {
            "D360-API-KEY": api_key,
            "Content-Type": "application/json",
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message
            }
        }
        
        # Envia
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code in [200, 201]:
                data = response.json()
                message_id = data.get("messages", [{}])[0].get("id", "")
                logger.info(f"✅ WhatsApp enviado para {to_number}: {message_id}")
                return {"success": True, "message_id": message_id}
            else:
                error = response.text
                logger.error(f"❌ Erro 360Dialog: {response.status_code} - {error}")
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
    Envia notificação WhatsApp para o gestor.
    
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
    
    # Envia
    result = await send_whatsapp_360dialog(manager_whatsapp, message, tenant)
    
    if result["success"]:
        logger.info(f"📲 WhatsApp enviado para gestor: {manager_whatsapp}")
    
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
    Envia notificação WhatsApp para o VENDEDOR quando recebe um lead.
    
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
    seller_phone = seller.phone
    if hasattr(seller, 'whatsapp') and seller.whatsapp:
        seller_phone = seller.whatsapp
    
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
    
    # Envia
    result = await send_whatsapp_360dialog(seller_phone, message, tenant)
    
    if result["success"]:
        logger.info(f"📲 WhatsApp enviado para vendedor {seller.name}: {seller_phone}")
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
        
        # 2. Envia WhatsApp para gestor
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
        
        # 2. Envia WhatsApp para vendedor
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