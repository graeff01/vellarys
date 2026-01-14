"""
SERVIÇO DE HANDOFF (TRANSFERÊNCIA)
===================================

Responsável por:
1. Detectar quando transferir para humano
2. Distribuir lead para vendedor apropriado
3. Notificar vendedor/gestor via WhatsApp
4. Registrar a transferência

✅ CORREÇÃO: Suporta tenant como objeto, slug ou ID
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Lead, Tenant, Notification, Seller
from .distribution_service import distribute_lead, assign_lead_to_seller

logger = logging.getLogger(__name__)


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
⏰ {datetime.now(timezone.utc).strftime("%d/%m/%Y às %H:%M")}

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
    
    message += f"⏰ {datetime.now(timezone.utc).strftime('%d/%m/%Y às %H:%M')}"

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
# HELPER: GARANTE OBJETO TENANT
# ==========================================

async def _ensure_tenant_object(
    tenant,
    db: AsyncSession,
) -> Optional[Tenant]:
    """
    Garante que tenant seja um objeto Tenant, não string ou int.
    
    Args:
        tenant: Objeto Tenant, slug (str) ou ID (int)
        db: Sessão do banco
    
    Returns:
        Objeto Tenant ou None se não encontrado
    """
    # Já é objeto Tenant
    if isinstance(tenant, Tenant):
        return tenant
    
    # É slug (string)
    if isinstance(tenant, str):
        logger.info(f"🔄 Convertendo tenant slug '{tenant}' em objeto")
        result = await db.execute(
            select(Tenant)
            .where(Tenant.slug == tenant)
            .where(Tenant.active == True)
        )
        tenant_obj = result.scalar_one_or_none()
        
        if not tenant_obj:
            logger.error(f"❌ Tenant não encontrado: {tenant}")
        
        return tenant_obj
    
    # É ID (int)
    if isinstance(tenant, int):
        logger.info(f"🔄 Convertendo tenant ID {tenant} em objeto")
        result = await db.execute(
            select(Tenant)
            .where(Tenant.id == tenant)
            .where(Tenant.active == True)
        )
        tenant_obj = result.scalar_one_or_none()
        
        if not tenant_obj:
            logger.error(f"❌ Tenant não encontrado: {tenant}")
        
        return tenant_obj
    
    # Tipo desconhecido
    logger.error(f"❌ Tipo de tenant inválido: {type(tenant)}")
    return None


# ==========================================
# EXECUÇÃO DO HANDOFF
# ==========================================

async def execute_handoff(
    lead: Lead,
    tenant,  # Pode ser Tenant, slug (str) ou ID (int)
    reason: str,
    db: AsyncSession,
) -> dict:
    """
    Executa o processo completo de handoff:
    1. Distribui o lead para um vendedor (ou gestor)
    2. Envia notificações via WhatsApp
    3. Atualiza o status do lead
    4. Registra a transferência
    
    Args:
        lead: Objeto Lead
        tenant: Objeto Tenant, slug (str) ou ID (int)
        reason: Motivo do handoff
        db: Sessão do banco
    
    Returns:
        {
            "success": bool,
            "seller": Seller ou None,
            "method": str,
            "message_for_lead": str,
            "notifications_sent": list,
            "error": str (se falhar)
        }
    """
    from .whatsapp_service import send_whatsapp_message
    
    # ════════════════════════════════════════════════════════════
    # BUG FIX: Garante que tenant seja objeto, não string/int
    # ════════════════════════════════════════════════════════════
    tenant_obj = await _ensure_tenant_object(tenant, db)
    
    if not tenant_obj:
        logger.error(f"❌ Handoff falhou: Tenant não encontrado")
        return {
            "success": False,
            "error": "Tenant não encontrado",
            "message_for_lead": "Ops! Houve um erro. Tente novamente em instantes.",
        }
    
    # Agora tenant_obj é SEMPRE um objeto Tenant
    settings = tenant_obj.settings or {}
    notifications_sent = []
    
    try:
        # 1. Marca o lead como transferido
        lead.handed_off_at = datetime.now(timezone.utc)
        lead.status = "contacted"  # Muda status para "em contato"
        
        logger.info(f"🔄 Executando handoff para lead {lead.id} (razão: {reason})")
        
        # 2. Distribui o lead
        distribution_result = await distribute_lead(db, lead, tenant_obj)
        
        seller = distribution_result.get("seller")
        method = distribution_result.get("method", "unknown")
        
        logger.info(f"✅ Lead distribuído: método={method}, seller={seller.name if seller else 'None'}")
        
        # 3. Prepara mensagem para o lead
        message_for_lead = build_handoff_message_for_lead(lead, tenant_obj, seller)

        # 3.1 Gera Raio-X (Resumo Inteligente) do Lead
        logger.info(f"🧠 Gerando Raio-X para lead {lead.id}...")
        try:
            from .openai_service import generate_lead_raiox
            # Converte histórico de mensagens para formato lista de dicts
            history = []
            if lead.messages:
                # Pega as últimas 15 mensagens para o resumo
                for msg in lead.messages[-15:]:
                    history.append({"role": msg.role, "content": msg.content})
            
            lead_raiox = await generate_lead_raiox(lead.name or "Novo", history)
        except Exception as e:
            logger.error(f"❌ Erro gerando Raio-X: {e}")
            lead_raiox = None
        
        # 4. Notifica vendedor (se houver)
        if seller and seller.whatsapp:
            seller_message = build_handoff_message_for_seller(lead, seller, tenant_obj)
            
            # Anexa o Raio-X se disponível
            if lead_raiox:
                seller_message += f"\n---\n{lead_raiox}"
            
            try:
                await send_whatsapp_message(seller.whatsapp, seller_message)
                notifications_sent.append({
                    "type": "seller",
                    "name": seller.name,
                    "phone": seller.whatsapp,
                    "status": "sent",
                })
                
                logger.info(f"📱 Notificação enviada para vendedor: {seller.name}")
                
                # Atualiza assignment como notificado
                if lead.assignments:
                    latest_assignment = lead.assignments[-1]
                    latest_assignment.notified_at = datetime.now(timezone.utc)
                    latest_assignment.status = "notified"
            except Exception as e:
                logger.error(f"❌ Erro notificando vendedor: {e}")
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
                lead, tenant_obj, manager_reason, seller
            )
            
            try:
                await send_whatsapp_message(manager_whatsapp, manager_message)
                notifications_sent.append({
                    "type": "manager",
                    "phone": manager_whatsapp,
                    "status": "sent",
                })
                logger.info(f"📱 Notificação enviada para gestor")
            except Exception as e:
                logger.error(f"❌ Erro notificando gestor: {e}")
                notifications_sent.append({
                    "type": "manager",
                    "phone": manager_whatsapp,
                    "status": "failed",
                    "error": str(e),
                })
        
        # 6. Cria notificação no dashboard
        notification = Notification(
            tenant_id=tenant_obj.id,
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
        
        logger.info(f"✅ Handoff concluído para lead {lead.id}")
        
        return {
            "success": True,
            "seller": seller,
            "method": method,
            "fallback_used": distribution_result.get("fallback_used", False),
            "message_for_lead": message_for_lead,
            "notifications_sent": notifications_sent,
        }
        
    except Exception as e:
        logger.error(f"❌ Erro no handoff: {e}", exc_info=True)
        await db.rollback()
        
        return {
            "success": False,
            "error": str(e),
            "message_for_lead": "Perfeito! Nossa equipe vai entrar em contato em breve. 😊",
        }


async def manual_assign_lead(
    db: AsyncSession,
    lead: Lead,
    seller: Seller,
    tenant,  # Pode ser Tenant, slug (str) ou ID (int)
    assigned_by: str = "manager",
) -> dict:
    """
    Atribui manualmente um lead a um vendedor.
    Usado quando o gestor decide para quem enviar.
    """
    from .whatsapp_service import send_whatsapp_message
    
    # ════════════════════════════════════════════════════════════
    # BUG FIX: Garante que tenant seja objeto
    # ════════════════════════════════════════════════════════════
    tenant_obj = await _ensure_tenant_object(tenant, db)
    
    if not tenant_obj:
        logger.error(f"❌ Atribuição manual falhou: Tenant não encontrado")
        return {
            "success": False,
            "error": "Tenant não encontrado",
        }
    
    try:
        # Atribui o lead
        assignment = await assign_lead_to_seller(
            db=db,
            lead=lead,
            seller=seller,
            tenant=tenant_obj,
            method="manual",
            reason=f"Atribuído manualmente por {assigned_by}",
        )
        
        # Notifica o vendedor
        notifications_sent = []
        
        if seller.whatsapp:
            seller_message = build_handoff_message_for_seller(lead, seller, tenant_obj)
            
            try:
                await send_whatsapp_message(seller.whatsapp, seller_message)
                notifications_sent.append({
                    "type": "seller",
                    "name": seller.name,
                    "status": "sent",
                })
                
                assignment.notified_at = datetime.now(timezone.utc)
                assignment.status = "notified"
                
                logger.info(f"✅ Lead {lead.id} atribuído manualmente para {seller.name}")
            except Exception as e:
                logger.error(f"❌ Erro notificando vendedor: {e}")
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
        
    except Exception as e:
        logger.error(f"❌ Erro na atribuição manual: {e}", exc_info=True)
        await db.rollback()
        
        return {
            "success": False,
            "error": str(e),
        }