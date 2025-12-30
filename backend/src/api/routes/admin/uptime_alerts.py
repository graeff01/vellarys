"""
UPTIME ALERTS
=============
Recebe alertas do UptimeRobot e notifica via WhatsApp.
"""

import logging
from fastapi import APIRouter, Request
from src.infrastructure.services.whatsapp_service import send_whatsapp_message
from src.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/uptime-alert", tags=["Admin"])


@router.post("")
async def receive_uptime_alert(request: Request):
    """
    Recebe alerta do UptimeRobot e envia para seu WhatsApp.
    
    Configure no UptimeRobot:
    - Alert Contact Type: Webhook
    - URL: https://seu-dominio.com/api/admin/uptime-alert
    - POST data: *monitorFriendlyName*-*alertTypeFriendlyName*-*alertDetails*
    """
    try:
        # Pega dados do UptimeRobot
        form_data = await request.form()
        body = await request.body()
        
        logger.info(f"Uptime alert received: {form_data}")
        
        # Extrai informações
        alert_text = body.decode('utf-8') if body else str(dict(form_data))
        
        # Monta mensagem
        message = f"""🚨 ALERTA DO SISTEMA

{alert_text}

⏰ Verifique imediatamente!
🔗 https://uptimerobot.com
"""
        
        # Envia para seu WhatsApp (configure no .env)
        admin_whatsapp = settings.ADMIN_WHATSAPP  # Adicionar no .env
        
        if admin_whatsapp:
            result = await send_whatsapp_message(
                to=admin_whatsapp,
                message=message
            )
            
            logger.info(f"Alerta enviado para {admin_whatsapp}: {result}")
        
        return {"status": "ok", "alert_sent": bool(admin_whatsapp)}
        
    except Exception as e:
        logger.error(f"Erro processando alerta: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}