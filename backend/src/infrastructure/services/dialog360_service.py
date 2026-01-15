import logging
import httpx
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.entities import Lead, Product

logger = logging.getLogger(__name__)

DIALOG360_API_URL = "https://waba.360dialog.io/v1/messages"

class Dialog360Service:
    """Serviço para envio de mensagens via 360Dialog."""
    
    @staticmethod
    async def send_text_message(
        api_key: str,
        to: str,
        text: str,
        preview_url: bool = False,
    ) -> Dict[str, Any]:
        """
        Envia mensagem de texto via 360Dialog.
        """
        headers = {
            "D360-API-KEY": api_key,
            "Content-Type": "application/json",
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "body": text,
                "preview_url": preview_url,
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    DIALOG360_API_URL,
                    json=payload,
                    headers=headers
                )
                
                if response.status_code in [200, 201, 202]:
                    return {"success": True, "data": response.json()}
                else:
                    logger.error(f"Erro 360Dialog ({response.status_code}): {response.text}")
                    return {"success": False, "error": response.text}
                    
        except Exception as e:
            logger.error(f"Exceção ao enviar 360Dialog: {e}")
            return {"success": False, "error": str(e)}

class GestorNotificationService:
    """Serviço de notificações específico para o fluxo 360Dialog (Imobiliário)."""
    
    @staticmethod
    def format_phone(phone: str) -> str:
        """Formata o telefone para exibição."""
        digits = "".join(filter(str.isdigit, phone))
        if len(digits) == 11:
            return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
        return phone

    @staticmethod
    def build_notification_message(
        lead: Lead,
        product: Optional[Product] = None,
        conversation_summary: str = None,
        is_for_broker: bool = False,
    ) -> str:
        """
        Constrói mensagem de notificação para o gestor ou corretor.
        """
        phone_formatted = GestorNotificationService.format_phone(lead.phone or "")
        
        qual_map = {
            "hot": "🔥 QUENTE",
            "quente": "🔥 QUENTE",
            "warm": "🟡 MORNO",
            "morno": "🟡 MORNO",
            "cold": "🔵 FRIO",
            "frio": "🔵 FRIO",
        }
        qualification = qual_map.get((lead.qualification or "").lower(), "📋 Em qualificação")
        
        created_at = lead.created_at or datetime.now(timezone.utc)
        date_str = created_at.strftime("%d/%m/%Y às %H:%M") if hasattr(created_at, 'strftime') else "Agora"
        
        summary = conversation_summary or lead.summary or "Conversa em andamento..."
        
        extras = []
        if lead.custom_data:
            product_name = lead.custom_data.get("product_name") or lead.custom_data.get("empreendimento_nome")
            if product_name: extras.append(f"• Produto: {product_name}")
            if lead.custom_data.get("tipologia"): extras.append(f"• Interesse: {lead.custom_data['tipologia']}")
            orcamento = lead.custom_data.get("orcamento") or lead.custom_data.get("budget_range")
            if orcamento: extras.append(f"• Orçamento: {orcamento}")
            if lead.custom_data.get("forma_pagamento"): extras.append(f"• Pagamento: {lead.custom_data['forma_pagamento']}")

        corretor_info = ""
        if not is_for_broker and product.attributes:
            corretor_nome = product.attributes.get("corretor_nome")
            if corretor_nome:
                corretor_info = f"\n👔 *Corretor Responsável:* {corretor_nome}"

        extras_text = "\n".join(extras) if extras else "• Dados sendo coletados..."
        product_name = product.name if product else (lead.custom_data.get("product_name") or lead.custom_data.get("empreendimento_nome") or "Imóvel")
        header = "🚀 *NOVO LEAD (ENCAMINHADO)*" if is_for_broker else f"📦 *Novo Lead - {product_name}*"
        
        return f"""{header}

👤 *Nome:* {lead.name or 'Não informado'}
📱 *WhatsApp:* {phone_formatted}
{qualification}{corretor_info}

📝 *Informações coletadas:*
{extras_text}

💬 *Resumo da conversa:*
{summary[:800]}{'...' if len(summary) > 800 else ''}

🕐 *Recebido:* {date_str}
📍 *Origem:* WhatsApp

_Para atender, clique no número acima ou responda agora._"""

    @staticmethod
    async def notify_gestor(
        db: AsyncSession,
        api_key: str,
        lead: Lead,
        tenant: Any,  # Passamos o tenant para fallback de manager
        product: Optional[Product] = None,
    ) -> bool:
        """
        Envia notificação para o gestor e para o corretor responsável.
        """
        try:
            manager_phone = None
            if product and product.attributes:
                manager_phone = product.attributes.get("whatsapp_notification")
            
            # Fallback para o gestor do tenant se não tem no produto
            if not manager_phone:
                settings = tenant.settings or {}
                manager_phone = settings.get("handoff", {}).get("manager_whatsapp")
            
            corretor_phone = product.attributes.get("corretor_whatsapp") if product and product.attributes else None
            corretor_nome = product.attributes.get("corretor_nome") if product and product.attributes else None
            
            if not manager_phone and not corretor_phone:
                logger.warning(f"⚠️ Sem telefone de destino para notificação Raio-X (Lead {lead.id})")
                return False
            
            if lead.custom_data and lead.custom_data.get("gestor_notificado"):
                if not (corretor_phone and not lead.custom_data.get("corretor_notificado")):
                    return False

            if manager_phone and not lead.custom_data.get("gestor_notificado"):
                gestor_phone = str(manager_phone).replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
                if not gestor_phone.startswith("55") and len(gestor_phone) <= 11:
                    gestor_phone = "55" + gestor_phone
                
                msg_gestor = GestorNotificationService.build_notification_message(lead=lead, product=product, is_for_broker=False)
                await Dialog360Service.send_text_message(api_key=api_key, to=gestor_phone, text=msg_gestor)
                
                if not lead.custom_data: lead.custom_data = {}
                lead.custom_data["gestor_notificado"] = True
                lead.custom_data["gestor_notificado_em"] = datetime.now(timezone.utc).isoformat()

            if corretor_phone and lead.name and not lead.custom_data.get("corretor_notificado"):
                broker_phone = str(corretor_phone).replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
                if not broker_phone.startswith("55") and len(broker_phone) <= 11:
                    broker_phone = "55" + broker_phone
                
                msg_corretor = GestorNotificationService.build_notification_message(lead=lead, product=product, is_for_broker=True)
                res = await Dialog360Service.send_text_message(api_key=api_key, to=broker_phone, text=msg_corretor)
                
                if res.get("success"):
                    if not lead.custom_data: lead.custom_data = {}
                    lead.custom_data["corretor_notificado"] = True
                    lead.custom_data["corretor_notificado_em"] = datetime.now(timezone.utc).isoformat()
                    lead.custom_data["corretor_nome"] = corretor_nome
                
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"Erro ao notificar: {e}")
            return False
