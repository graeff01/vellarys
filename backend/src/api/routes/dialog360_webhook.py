"""
WEBHOOK 360DIALOG WHATSAPP - VERSÃO COMPLETA
=============================================

Integração completa com Dialog360 para:
- Receber mensagens de leads via WhatsApp
- Processar com IA (usando process_message completo)
- Detectar empreendimentos automaticamente
- Notificar gestor quando lead estiver qualificado
- Enviar respostas de volta para o lead

Fluxo:
1. Lead envia mensagem → Webhook recebe
2. process_message() processa (com detecção de empreendimento)
3. IA responde → Envia de volta pro lead
4. Se lead tem nome + empreendimento → Notifica gestor
5. Gestor recebe resumo no WhatsApp → Encaminha pro corretor

Configuração necessária no Tenant:
- settings.whatsapp_number: Número do WhatsApp Business
- settings.dialog360_api_key: API Key do 360dialog

Configuração no Empreendimento:
- whatsapp_notificacao: Número do gestor para receber notificações
"""

import logging
import json
import httpx
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, Request, Response, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.infrastructure.database import get_db
from src.domain.entities import Lead, Message, Tenant, Product
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/webhook", tags=["Webhook 360dialog"])


# =============================================================================
# CONSTANTES
# =============================================================================

DIALOG360_API_URL = "https://waba.360dialog.io/v1/messages"

# Tipos de mensagem suportados
SUPPORTED_MESSAGE_TYPES = ["text", "button", "interactive"]

# Tempo máximo para responder (segundos)
RESPONSE_TIMEOUT = 30.0


# =============================================================================
# SERVIÇO DE ENVIO - 360DIALOG
# =============================================================================

from src.infrastructure.services.dialog360_service import Dialog360Service, GestorNotificationService


# =============================================================================
# HELPERS
# =============================================================================

def extract_message_content(message: dict) -> Optional[str]:
    """Extrai conteúdo da mensagem independente do tipo."""
    msg_type = message.get("type")
    
    if msg_type == "text":
        return message.get("text", {}).get("body")
    
    elif msg_type == "button":
        return message.get("button", {}).get("text")
    
    elif msg_type == "interactive":
        interactive = message.get("interactive", {})
        # Resposta de lista
        if "list_reply" in interactive:
            return interactive["list_reply"].get("title")
        # Resposta de botão
        if "button_reply" in interactive:
            return interactive["button_reply"].get("title")
    
    # ✨ NOVO: Retorna None para áudio (será processado separadamente)
    elif msg_type == "audio":
        return None  # Sinal para processar áudio
    
    return None


def normalize_phone(phone: str) -> str:
    """Normaliza número de telefone removendo caracteres especiais."""
    return phone.replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")


async def get_tenant_by_phone(db: AsyncSession, business_phone: str) -> Optional[Tenant]:
    """Busca tenant pelo número do WhatsApp Business."""
    # Tenta com o número exato
    result = await db.execute(
        select(Tenant).where(
            Tenant.settings["whatsapp_number"].astext == business_phone,
            Tenant.active == True
        )
    )
    tenant = result.scalar_one_or_none()
    
    if tenant:
        return tenant
    
    # Tenta sem código do país
    if business_phone.startswith("55"):
        phone_without_country = business_phone[2:]
        result = await db.execute(
            select(Tenant).where(
                Tenant.settings["whatsapp_number"].astext == phone_without_country,
                Tenant.active == True
            )
        )
        tenant = result.scalar_one_or_none()
    
    return tenant


async def get_product_for_lead(
    db: AsyncSession,
    lead: Lead,
) -> Optional[Product]:
    """Busca produto associado ao lead."""
    if not lead.custom_data:
        return None
    
    prod_id = lead.custom_data.get("product_id") or lead.custom_data.get("empreendimento_id")
    if not prod_id:
        return None
    
    result = await db.execute(
        select(Product).where(Product.id == prod_id)
    )
    return result.scalar_one_or_none()


# =============================================================================
# WEBHOOK ENDPOINTS
# =============================================================================

@router.get("/360dialog")
async def verify_webhook(
    request: Request,
):
    """
    Verificação do webhook (requisito do Meta/360Dialog).
    
    Quando você configura o webhook no 360Dialog, eles enviam um GET
    com hub.mode, hub.challenge e hub.verify_token para verificar.
    """
    params = request.query_params
    
    hub_mode = params.get("hub.mode")
    hub_challenge = params.get("hub.challenge")
    hub_verify_token = params.get("hub.verify_token")
    
    # Token de verificação (configure no .env ou use padrão)
    verify_token = getattr(settings, "webhook_verify_token", None) or "velaris_webhook"
    
    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        logger.info("✅ Webhook verificado com sucesso")
        return Response(content=hub_challenge, media_type="text/plain")
    
    logger.warning(f"❌ Verificação falhou - Token: {hub_verify_token}")
    raise HTTPException(status_code=403, detail="Verificação falhou")


@router.post("/360dialog")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Recebe mensagens do WhatsApp via 360Dialog.
    
    Payload exemplo:
    {
        "object": "whatsapp_business_account",
        "entry": [{
            "changes": [{
                "field": "messages",
                "value": {
                    "metadata": {"display_phone_number": "5511999999999"},
                    "messages": [{
                        "from": "5511888888888",
                        "type": "text",
                        "text": {"body": "Olá!"}
                    }]
                }
            }]
        }]
    }
    """
    try:
        data = await request.json()
        
        # Log resumido (não loga mensagem completa por privacidade)
        logger.info(f"📥 Webhook recebido - Object: {data.get('object')}")
        
        # Ignora se não for do WhatsApp Business
        if data.get("object") != "whatsapp_business_account":
            return {"status": "ignored", "reason": "not_whatsapp"}
        
        # Processa cada entry
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") != "messages":
                    continue
                
                value = change.get("value", {})
                
                # ============================================
                # 1. IDENTIFICA O TENANT PELO NÚMERO
                # ============================================
                metadata = value.get("metadata", {})
                business_phone = normalize_phone(
                    metadata.get("display_phone_number", "")
                )
                
                if not business_phone:
                    logger.warning("⚠️ Webhook sem número de telefone")
                    continue
                
                tenant = await get_tenant_by_phone(db, business_phone)
                
                if not tenant:
                    logger.error(f"❌ Nenhum tenant para o número {business_phone}")
                    continue
                
                # Pega API Key do tenant
                api_key = (tenant.settings or {}).get("dialog360_api_key")
                if not api_key:
                    logger.error(f"❌ Tenant {tenant.slug} sem dialog360_api_key")
                    continue
                
                logger.info(f"📱 Tenant identificado: {tenant.slug}")
                
                # ============================================
                # 2. PROCESSA CADA MENSAGEM
                # ============================================
                for message in value.get("messages", []):
                    msg_type = message.get("type")
                    msg_id = message.get("id")
                    from_phone = normalize_phone(message.get("from", ""))
                    
                    # ============================================
                    # ✨ NOVO: TRANSCRIÇÃO DE ÁUDIO
                    # ============================================
                    content = None
                    
                    if msg_type == "audio":
                        logger.info(f"🎙️ Áudio recebido de {from_phone[-4:]}")
                        
                        try:
                            from src.infrastructure.services.transcription_service import transcribe_audio_url
                            
                            # Pega URL do áudio
                            audio_data = message.get("audio", {})
                            audio_id = audio_data.get("id")
                            
                            if not audio_id:
                                logger.error("❌ Áudio sem ID")
                                continue
                            
                            # Baixa URL do áudio via API 360Dialog
                            media_url_endpoint = f"https://waba.360dialog.io/v1/media/{audio_id}"
                            async with httpx.AsyncClient(timeout=30.0) as client:
                                media_response = await client.get(
                                    media_url_endpoint,
                                    headers={"D360-API-KEY": api_key}
                                )
                                
                                if media_response.status_code == 200:
                                    media_data = media_response.json()
                                    audio_url = media_data.get("url")
                                    
                                    if audio_url:
                                        # Transcreve
                                        logger.info(f"🎙️ Transcrevendo áudio: {audio_url[:50]}...")
                                        content = await transcribe_audio_url(
                                            url=audio_url,
                                            prompt="Transcrição de mensagem de WhatsApp em português brasileiro sobre imóveis."
                                        )
                                        
                                        if content:
                                            logger.info(f"✅ Áudio transcrito: \"{content[:50]}...\"")
                                        else:
                                            logger.error("❌ Falha na transcrição")
                                            content = "[Áudio não compreendido. Pode enviar como texto?]"
                                    else:
                                        logger.error("❌ URL do áudio não encontrada")
                                        continue
                                else:
                                    logger.error(f"❌ Erro ao buscar mídia: {media_response.status_code}")
                                    continue
                        
                        except Exception as e:
                            logger.error(f"❌ Erro ao processar áudio: {e}")
                            # Envia mensagem educativa
                            await Dialog360Service.send_text_message(
                                api_key=api_key,
                                to=from_phone,
                                text="Desculpe, não consegui processar seu áudio. Pode enviar sua mensagem como texto? 😊"
                            )
                            continue
                    
                    else:
                        # Extrai conteúdo de mensagens de texto/botões
                        content = extract_message_content(message)
                    
                    if not content:
                        logger.debug(f"⚠️ Mensagem tipo {msg_type} sem conteúdo extraível")
                        continue
                    
                    logger.info(f"💬 Mensagem de {from_phone[-4:]}: {content[:50]}...")
                    
                    # Marca como lida (em background)
                    if msg_id:
                        background_tasks.add_task(
                            Dialog360Service.mark_as_read,
                            api_key,
                            msg_id,
                        )
                    
                    # ============================================
                    # 3. PROCESSA COM A IA (process_message)
                    # ============================================
                    try:
                        from src.application.use_cases.process_message import process_message
                        
                        result = await process_message(
                            db=db,
                            tenant_slug=tenant.slug,
                            channel_type="whatsapp",
                            external_id=from_phone,
                            content=content,
                            sender_phone=from_phone,
                            source="whatsapp_360dialog",
                            external_message_id=msg_id,
                        )
                        
                        ai_reply = result.get("reply")
                        lead_id = result.get("lead_id")
                        product_id = result.get("product_id") or result.get("empreendimento_id")
                        
                        logger.info(f"🤖 Resposta gerada - Lead: {lead_id}, Produto: {product_id}")
                        
                    except Exception as e:
                        logger.error(f"❌ Erro no process_message: {e}")
                        ai_reply = "Desculpe, estou com uma instabilidade momentânea. Pode repetir sua mensagem?"
                        lead_id = None
                        empreendimento_id = None
                    
                    # ============================================
                    # 4. ENVIA RESPOSTA PARA O LEAD
                    # ============================================
                    if ai_reply:
                        send_result = await Dialog360Service.send_text_message(
                            api_key=api_key,
                            to=from_phone,
                            text=ai_reply,
                        )
                        
                        if not send_result.get("success"):
                            logger.error(f"❌ Falha ao enviar resposta para {from_phone}")
                    
                    # ============================================
                    # 5. NOTIFICA GESTOR (se aplicável)
                    # ============================================
                    if lead_id and product_id:
                        # Busca lead atualizado
                        lead_result = await db.execute(
                            select(Lead).where(Lead.id == lead_id)
                        )
                        lead = lead_result.scalar_one_or_none()
                        
                        # Busca produto
                        prod_result = await db.execute(
                            select(Product).where(Product.id == product_id)
                        )
                        product = prod_result.scalar_one_or_none()
                        
                        if lead and product:
                            # Notifica em background para não atrasar resposta
                            background_tasks.add_task(
                                GestorNotificationService.notify_gestor,
                                db,
                                api_key,
                                lead,
                                product,
                            )
        
        return {"status": "ok"}
        
    except json.JSONDecodeError:
        logger.error("❌ Payload inválido (não é JSON)")
        return {"status": "error", "message": "Invalid JSON"}
    except Exception as e:
        logger.error(f"❌ Erro no webhook: {e}")
        return {"status": "error", "message": str(e)}


# =============================================================================
# ENDPOINTS DE TESTE/DEBUG
# =============================================================================

@router.get("/360dialog/health")
async def health_check():
    """Verifica se o webhook está rodando."""
    return {
        "status": "healthy",
        "service": "360dialog_webhook",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/360dialog/test-send")
async def test_send_message(
    to: str,
    message: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Endpoint de teste para enviar mensagem.
    Requer que o tenant esteja configurado.
    
    Uso: POST /webhook/360dialog/test-send?to=5511999999999&message=Teste
    """
    # Busca primeiro tenant com API key configurada
    result = await db.execute(
        select(Tenant).where(
            Tenant.settings["dialog360_api_key"].isnot(None),
            Tenant.active == True
        ).limit(1)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=400, detail="Nenhum tenant com Dialog360 configurado")
    
    api_key = tenant.settings.get("dialog360_api_key")
    
    send_result = await Dialog360Service.send_text_message(
        api_key=api_key,
        to=normalize_phone(to),
        text=message,
    )
    
    return send_result


@router.post("/360dialog/test-notify-gestor")
async def test_notify_gestor(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Testa notificação do gestor para um lead específico.
    
    Uso: POST /webhook/360dialog/test-notify-gestor?lead_id=123
    """
    # Busca lead
    lead_result = await db.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = lead_result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    
    # Busca tenant
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == lead.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    
    api_key = (tenant.settings or {}).get("dialog360_api_key")
    if not api_key:
        raise HTTPException(status_code=400, detail="Tenant sem dialog360_api_key")
    
    # Busca produto
    product = await get_product_for_lead(db, lead)
    
    if not product:
        raise HTTPException(status_code=400, detail="Lead não tem produto associado")
    
    # Força reset do flag para testar
    if lead.custom_data:
        lead.custom_data["gestor_notificado"] = False
        await db.commit()
    
    # Notifica
    success = await GestorNotificationService.notify_gestor(
        db=db,
        api_key=api_key,
        lead=lead,
        product=product,
    )
    
    return {
        "success": success,
        "lead_id": lead.id,
        "lead_name": lead.name,
        "product": product.name,
        "gestor_phone": product.attributes.get("whatsapp_notification") if product.attributes else None,
    }


@router.get("/360dialog/debug-config/{tenant_slug}")
async def debug_tenant_config(
    tenant_slug: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Debug: Mostra configuração do tenant para 360Dialog.
    """
    result = await db.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    
    settings_dict = tenant.settings or {}
    
    return {
        "tenant": tenant.slug,
        "whatsapp_number": settings_dict.get("whatsapp_number"),
        "has_api_key": bool(settings_dict.get("dialog360_api_key")),
        "api_key_preview": settings_dict.get("dialog360_api_key", "")[:10] + "..." if settings_dict.get("dialog360_api_key") else None,
    }