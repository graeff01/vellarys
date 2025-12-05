"""
WEBHOOK 360DIALOG WHATSAPP
==========================

Recebe mensagens do WhatsApp via 360dialog e processa com a IA.
Documentação: https://docs.360dialog.com/whatsapp-api/whatsapp-api/webhook
"""

from fastapi import APIRouter, Request, Response, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import httpx
import json
from typing import Optional

from src.infrastructure.database import get_db
from src.domain.entities import Lead, Message, Tenant, Channel
from src.infrastructure.services import chat_completion
from src.domain.prompts import get_niche_config
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/webhook", tags=["Webhook 360dialog"])


async def send_360dialog_message(api_key: str, to: str, message: str):
    """Envia mensagem via 360dialog API."""
    url = "https://waba.360dialog.io/v1/messages"
    
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
            "preview_url": False,
            "body": message
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            logger.info(f"✅ Mensagem enviada para {to}")
            return True
        else:
            logger.error(f"❌ Erro ao enviar mensagem: {response.text}")
            return False


@router.get("/360dialog")
async def verify_webhook(
    hub_mode: Optional[str] = None,
    hub_challenge: Optional[str] = None,
    hub_verify_token: Optional[str] = None,
):
    """
    Verificação do webhook pelo 360dialog/Meta.
    Chamado uma vez durante a configuração do webhook.
    """
    # O 360dialog usa o padrão do Meta para verificação
    verify_token = settings.webhook_verify_token or "velaris_webhook_token"
    
    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        logger.info("✅ Webhook verificado com sucesso!")
        return Response(content=hub_challenge, media_type="text/plain")
    
    logger.warning(f"⚠️ Verificação falhou: mode={hub_mode}, token={hub_verify_token}")
    raise HTTPException(status_code=403, detail="Verificação falhou")


@router.post("/360dialog")
async def handle_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Recebe mensagens do WhatsApp via 360dialog.
    
    Formato do payload:
    {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "PHONE_NUMBER",
                        "phone_number_id": "PHONE_NUMBER_ID"
                    },
                    "messages": [{
                        "from": "SENDER_PHONE",
                        "id": "MESSAGE_ID",
                        "timestamp": "TIMESTAMP",
                        "type": "text",
                        "text": {"body": "MESSAGE_BODY"}
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    """
    try:
        payload = await request.json()
        logger.info(f"📨 Webhook 360dialog recebido: {json.dumps(payload)[:500]}")
        print(f"📨 Webhook 360dialog recebido")
        
        # Extrair mensagens do payload
        if payload.get("object") != "whatsapp_business_account":
            return {"status": "ignored"}
        
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                
                # Ignorar se não for mensagem
                if change.get("field") != "messages":
                    continue
                
                # Pegar metadados do número que recebeu
                metadata = value.get("metadata", {})
                business_phone = metadata.get("display_phone_number", "").replace("+", "")
                
                # Processar cada mensagem
                for msg in value.get("messages", []):
                    # Ignorar mensagens que não são de texto
                    if msg.get("type") != "text":
                        logger.info(f"Ignorando mensagem tipo: {msg.get('type')}")
                        continue
                    
                    from_number = msg.get("from", "")
                    message_text = msg.get("text", {}).get("body", "")
                    message_id = msg.get("id", "")
                    
                    logger.info(f"📱 Mensagem: {from_number} -> {business_phone}: {message_text}")
                    print(f"📱 Mensagem: {from_number} -> {business_phone}: {message_text}")
                    
                    # Buscar canal pelo número do business
                    channel_result = await db.execute(
                        select(Channel).where(
                            Channel.phone_number == business_phone,
                            Channel.active == True
                        )
                    )
                    channel = channel_result.scalar_one_or_none()
                    
                    if not channel:
                        # Tentar buscar primeiro tenant ativo para teste
                        logger.warning(f"Canal não encontrado para {business_phone}, usando primeiro tenant")
                        tenant_result = await db.execute(
                            select(Tenant).where(Tenant.active == True).limit(1)
                        )
                        tenant = tenant_result.scalar_one_or_none()
                        api_key = settings.dialog360_api_key
                    else:
                        # Buscar tenant do canal
                        tenant_result = await db.execute(
                            select(Tenant).where(Tenant.id == channel.tenant_id)
                        )
                        tenant = tenant_result.scalar_one_or_none()
                        # API key pode estar nas credenciais do canal ou nas settings
                        credentials = channel.credentials or {}
                        api_key = credentials.get("api_key") or settings.dialog360_api_key
                    
                    if not tenant:
                        logger.error("Nenhum tenant encontrado")
                        continue
                    
                    if not api_key:
                        logger.error("API key do 360dialog não configurada")
                        continue
                    
                    # Buscar ou criar lead
                    lead_result = await db.execute(
                        select(Lead).where(
                            Lead.tenant_id == tenant.id,
                            Lead.phone == from_number
                        )
                    )
                    lead = lead_result.scalar_one_or_none()
                    
                    if not lead:
                        lead = Lead(
                            tenant_id=tenant.id,
                            phone=from_number,
                            name=f"WhatsApp {from_number[-4:]}",
                            source="whatsapp_360dialog",
                            status="new",
                        )
                        db.add(lead)
                        await db.flush()
                        logger.info(f"✨ Novo lead criado: {lead.id}")
                    
                    # Salvar mensagem recebida
                    message_in = Message(
                        tenant_id=tenant.id,
                        lead_id=lead.id,
                        direction="inbound",
                        content=message_text,
                        channel="whatsapp",
                        external_id=message_id,
                    )
                    db.add(message_in)
                    
                    # Buscar histórico
                    messages_result = await db.execute(
                        select(Message)
                        .where(Message.lead_id == lead.id)
                        .order_by(Message.created_at.desc())
                        .limit(10)
                    )
                    history = messages_result.scalars().all()
                    
                    # Montar histórico para IA
                    messages_for_ai = []
                    for hist_msg in reversed(list(history)):
                        role = "user" if hist_msg.direction == "inbound" else "assistant"
                        messages_for_ai.append({"role": role, "content": hist_msg.content})
                    
                    messages_for_ai.append({"role": "user", "content": message_text})
                    
                    # Configurar prompt
                    tenant_settings = tenant.settings or {}
                    niche = tenant_settings.get("niche", "services")
                    tone = tenant_settings.get("tone", "cordial")
                    company_name = tenant_settings.get("company_name", tenant.name)
                    niche_config = get_niche_config(niche)
                    
                    system_prompt = f"""Você é um assistente de atendimento da empresa {company_name}.

{niche_config.prompt_template if niche_config else "Atenda o cliente de forma profissional."}

Tom de voz: {tone}

IMPORTANTE:
- Seja natural e humano na conversa
- Faça perguntas para qualificar o lead
- Use emojis moderadamente se o tom for cordial
"""
                    
                    # Gerar resposta da IA
                    ai_messages = [{"role": "system", "content": system_prompt}] + messages_for_ai
                    
                    result = await chat_completion(
                        messages=ai_messages,
                        max_tokens=500,
                    )
                    
                    ai_response = result["content"]
                    logger.info(f"🤖 Resposta IA: {ai_response[:100]}...")
                    
                    # Salvar resposta
                    message_out = Message(
                        tenant_id=tenant.id,
                        lead_id=lead.id,
                        direction="outbound",
                        content=ai_response,
                        channel="whatsapp",
                    )
                    db.add(message_out)
                    
                    # Atualizar status do lead
                    if lead.status == "new":
                        lead.status = "contacted"
                    
                    await db.commit()
                    
                    # Enviar resposta via 360dialog
                    await send_360dialog_message(api_key, from_number, ai_response)
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"❌ Erro no webhook 360dialog: {str(e)}")
        print(f"❌ Erro no webhook 360dialog: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


@router.get("/360dialog/test")
async def test_webhook():
    """Endpoint de teste para verificar se a rota está funcionando."""
    return {
        "status": "ok", 
        "message": "360dialog webhook está ativo!",
        "webhook_url": "/api/v1/webhook/360dialog"
    }