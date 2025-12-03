"""
SERVIÇO DE HANDOFF (TRANSFERÊNCIA)
===================================

Responsável por:
1. Detectar quando transferir para humano
2. Distribuir lead para vendedor apropriado
3. Notificar vendedor/gestor via WhatsApp
4. Registrar a transferência
"""

from datetime import datetime
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Lead, Tenant, Notification, Seller
from .distribution_service import distribute_lead, assign_lead_to_seller


# ==========================================
# TRIGGERS DE HANDOFF
# ==========================================

DEFAULT_HANDOFF_TRIGGERS = [
    "quero falar com humano",
    "falar com atendente",
    "atendente humano",
    "pessoa real",
    "falar com alguém",
    "falar com vendedor",
    "quero um corretor",
    "passar para atendente",
    "não quero falar com robô",
]


def check_handoff_triggers(
    message: str,
    custom_triggers: list[str] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Verifica se a mensagem contém trigger de handoff.
    
    Returns:
        (should_handoff, trigger_matched)
    """
    message_lower = message.lower().strip()
    
    triggers = DEFAULT_HANDOFF_TRIGGERS + (custom_triggers or [])
    
    for trigger in triggers:
        if trigger.lower() in message_lower:
            return True, trigger
    
    return False, None


def should_handoff(
    lead: Lead,
    qualification: str,
    message_count: int,
    settings: dict,
) -> Tuple[bool, str]:
    """
    Decide se deve fazer handoff baseado em múltiplos critérios.
    
    Returns:
        (should_handoff, reason)
    """
    # 1. Lead ficou HOT
    if qualification == "hot":
        return True, "lead_hot"
    
    # 2. Limite de mensagens atingido
    max_messages = settings.get("max_messages_before_handoff", 15)
    if message_count >= max_messages:
        return True, "message_limit"
    
    # 3. Handoff desabilitado
    if not settings.get("handoff_enabled", True):
        return False, "disabled"
    
    return False, "no_trigger"


# ==========================================
# CONSTRUÇÃO DE MENSAGENS
# ==========================================

def build_handoff_message_for_seller(
    lead: Lead,
    seller: Seller,
    tenant: Tenant,
) -> str:
    """
    Constrói mensagem de notificação para o vendedor.
    """
    settings = tenant.settings or {}
    company_name = settings.get("company_name", tenant.name)
    
    # Dados do lead
    lead_name = lead.name or "Não informado"
    lead_phone = lead.phone or "Não informado"
    lead_city = lead.city or "Não informada"
    lead_summary = lead.summary or "Sem resumo disponível"
    
    # Interesse/especialidade do lead
    interest = ""
    if lead.custom_data:
        interest = (
            lead.custom_data.get("interest_type") or
            lead.custom_data.get("tipo_interesse") or
            lead.custom_data.get("specialty") or
            ""
        )
    
    message = f"""🔥 *NOVO LEAD - {company_name}*

👤 *Nome:* {lead_name}
📱 *Telefone:* {lead_phone}
📍 *Cidade:* {lead_city}
"""

    if interest:
        message += f"🎯 *Interesse:* {interest}\n"
    
    message += f"""
📝 *Resumo da conversa:*
{lead_summary}

---
✅ Atribuído para: *{seller.name}*
⏰ {datetime.now().strftime("%d/%m/%Y às %H:%M")}

💡 Entre em contato o mais rápido possível!"""

    return message


def build_handoff_message_for_manager(
    lead: Lead,
    tenant: Tenant,
    reason: str = "manual",
    seller: Seller = None,
) -> str:
    """
    Constrói mensagem de notificação para o gestor.
    """
    settings = tenant.settings or {}
    company_name = settings.get("company_name", tenant.name)
    
    # Dados do lead
    lead_name = lead.name or "Não informado"
    lead_phone = lead.phone or "Não informado"
    lead_city = lead.city or "Não informada"
    lead_summary = lead.summary or "Sem resumo disponível"
    
    # Motivo do envio para gestor
    reason_text = {
        "manual": "Distribuição manual configurada",
        "no_seller": "Nenhum vendedor disponível",
        "fallback": "Nenhum vendedor compatível encontrado",
        "lead_hot": "Lead qualificado como HOT",
        "message_limit": "Limite de mensagens atingido",
        "copy": "Cópia de notificação",
    }.get(reason, reason)
    
    message = f"""📊 *LEAD PARA ANÁLISE - {company_name}*

👤 *Nome:* {lead_name}
📱 *Telefone:* {lead_phone}
📍 *Cidade:* {lead_city}

📝 *Resumo da conversa:*
{lead_summary}

---
📌 *Motivo:* {reason_text}
"""

    if seller:
        message += f"✅ *Atribuído para:* {seller.name}\n"
    else:
        message += "⚠️ *Aguardando atribuição manual*\n"
    
    message += f"⏰ {datetime.now().strftime('%d/%m/%Y às %H:%M')}"

    return message


def build_handoff_message_for_lead(
    lead: Lead,
    tenant: Tenant,
    seller: Seller = None,
) -> str:
    """
    Constrói mensagem de despedida para o lead.
    """
    settings = tenant.settings or {}
    
    if seller:
        seller_name = seller.name.split()[0]  # Primeiro nome
        return f"""Perfeito! 🎉

Vou transferir você para o *{seller_name}*, nosso especialista.

Ele vai entrar em contato com você em instantes pelo WhatsApp.

Foi um prazer atendê-lo! 😊"""
    else:
        manager_name = settings.get("manager_name", "nossa equipe")
        return f"""Perfeito! 🎉

Vou transferir você para *{manager_name}*.

Em instantes alguém da nossa equipe vai entrar em contato com você.

Foi um prazer atendê-lo! 😊"""


# ==========================================
# EXECUÇÃO DO HANDOFF
# ==========================================

async def execute_handoff(
    db: AsyncSession,
    lead: Lead,
    tenant: Tenant,
    reason: str = "lead_hot",
) -> dict:
    """
    Executa o processo completo de handoff:
    1. Distribui o lead para um vendedor (ou gestor)
    2. Envia notificações via WhatsApp
    3. Atualiza o status do lead
    4. Registra a transferência
    
    Returns:
        {
            "success": bool,
            "seller": Seller ou None,
            "method": str,
            "message_for_lead": str,
            "notifications_sent": list,
        }
    """
    from .whatsapp_service import send_whatsapp_message
    
    settings = tenant.settings or {}
    notifications_sent = []
    
    # 1. Marca o lead como transferido
    lead.handed_off_at = datetime.utcnow()
    lead.status = "contacted"  # Muda status para "em contato"
    
    # 2. Distribui o lead
    distribution_result = await distribute_lead(db, lead, tenant)
    
    seller = distribution_result.get("seller")
    method = distribution_result.get("method", "unknown")
    
    # 3. Prepara mensagem para o lead
    message_for_lead = build_handoff_message_for_lead(lead, tenant, seller)
    
    # 4. Notifica vendedor (se houver)
    if seller and seller.whatsapp:
        seller_message = build_handoff_message_for_seller(lead, seller, tenant)
        
        try:
            await send_whatsapp_message(seller.whatsapp, seller_message)
            notifications_sent.append({
                "type": "seller",
                "name": seller.name,
                "phone": seller.whatsapp,
                "status": "sent",
            })
            
            # Atualiza assignment como notificado
            if lead.assignments:
                latest_assignment = lead.assignments[-1]
                latest_assignment.notified_at = datetime.utcnow()
                latest_assignment.status = "notified"
        except Exception as e:
            notifications_sent.append({
                "type": "seller",
                "name": seller.name,
                "phone": seller.whatsapp,
                "status": "failed",
                "error": str(e),
            })
    
    # 5. Notifica gestor (se necessário)
    manager_whatsapp = settings.get("manager_whatsapp")
    notify_manager = (
        not seller or  # Nenhum vendedor atribuído
        method == "manual" or  # Distribuição manual
        settings.get("distribution", {}).get("notify_manager_copy", False)  # Cópia habilitada
    )
    
    if manager_whatsapp and notify_manager:
        manager_reason = "copy" if seller else (
            "manual" if method == "manual" else "no_seller"
        )
        manager_message = build_handoff_message_for_manager(
            lead, tenant, manager_reason, seller
        )
        
        try:
            await send_whatsapp_message(manager_whatsapp, manager_message)
            notifications_sent.append({
                "type": "manager",
                "phone": manager_whatsapp,
                "status": "sent",
            })
        except Exception as e:
            notifications_sent.append({
                "type": "manager",
                "phone": manager_whatsapp,
                "status": "failed",
                "error": str(e),
            })
    
    # 6. Cria notificação no dashboard
    notification = Notification(
        tenant_id=tenant.id,
        type="handoff",
        title="🔥 Lead Transferido" if seller else "📊 Lead Aguardando Atribuição",
        message=f"Lead {lead.name or 'Novo'} foi {'atribuído para ' + seller.name if seller else 'enviado para análise'}",
        reference_type="lead",
        reference_id=lead.id,
        read=False,
    )
    db.add(notification)
    
    # 7. Commit das alterações
    await db.commit()
    
    return {
        "success": True,
        "seller": seller,
        "method": method,
        "fallback_used": distribution_result.get("fallback_used", False),
        "message_for_lead": message_for_lead,
        "notifications_sent": notifications_sent,
    }


async def manual_assign_lead(
    db: AsyncSession,
    lead: Lead,
    seller: Seller,
    tenant: Tenant,
    assigned_by: str = "manager",
) -> dict:
    """
    Atribui manualmente um lead a um vendedor.
    Usado quando o gestor decide para quem enviar.
    """
    from .whatsapp_service import send_whatsapp_message
    
    # Atribui o lead
    assignment = await assign_lead_to_seller(
        db=db,
        lead=lead,
        seller=seller,
        tenant=tenant,
        method="manual",
        reason=f"Atribuído manualmente por {assigned_by}",
    )
    
    # Notifica o vendedor
    notifications_sent = []
    
    if seller.whatsapp:
        seller_message = build_handoff_message_for_seller(lead, seller, tenant)
        
        try:
            await send_whatsapp_message(seller.whatsapp, seller_message)
            notifications_sent.append({
                "type": "seller",
                "name": seller.name,
                "status": "sent",
            })
            
            assignment.notified_at = datetime.utcnow()
            assignment.status = "notified"
        except Exception as e:
            notifications_sent.append({
                "type": "seller",
                "name": seller.name,
                "status": "failed",
                "error": str(e),
            })
    
    await db.commit()
    
    return {
        "success": True,
        "seller": seller,
        "assignment": assignment,
        "notifications_sent": notifications_sent,
    }