"""
WEBHOOK 360DIALOG WHATSAPP
==========================

Recebe mensagens do WhatsApp via 360dialog e processa com a IA.
Documentação: https://docs.360dialog.com/whatsapp-api/whatsapp-api/webhook
"""

from fastapi import APIRouter, Request, Response, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import httpx
import json
from typing import Optional

from src.infrastructure.database import get_db
from src.domain.entities import Lead, Message, Tenant
from src.infrastructure.services import chat_completion
from src.domain.prompts import get_niche_config
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/webhook", tags=["Webhook 360dialog"])


# ======================================================
# ENVIO DE MENSAGEM VIA 360DIALOG
# ======================================================
async def send_360dialog_message(api_key: str, to: str, message: str):
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
        
        logger.error(f"❌ Erro ao enviar mensagem: {response.text}")
        return False


# ======================================================
# VERIFICAÇÃO DO WEBHOOK
# ======================================================
@router.get("/360dialog")
async def verify_webhook(
    hub_mode: Optional[str] = None,
    hub_challenge: Optional[str] = None,
    hub_verify_token: Optional[str] = None,
):
    verify_token = settings.webhook_verify_token or "velaris_webhook_token"
    
    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        logger.info("✅ Webhook verificado com sucesso!")
        return Response(content=hub_challenge, media_type="text/plain")
    
    logger.warning(f"⚠️ Verificação falhou: mode={hub_mode}, token={hub_verify_token}")
    raise HTTPException(status_code=403, detail="Verificação falhou")


# ======================================================
# RECEBIMENTO DO WEBHOOK DE MENSAGENS
# ======================================================
@router.post("/360dialog")
async def handle_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = await request.json()
        logger.info(f"📨 Webhook 360dialog recebido: {json.dumps(payload)[:500]}")

        if payload.get("object") != "whatsapp_business_account":
            return {"status": "ignored"}

        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                
                if change.get("field") != "messages":
                    continue

                value = change.get("value", {})
                metadata = value.get("metadata", {})
                business_phone = metadata.get("display_phone_number", "").replace("+", "")

                for msg in value.get("messages", []):
                    
                    if msg.get("type") != "text":
                        logger.info(f"Ignorando mensagem tipo: {msg.get('type')}")
                        continue
                    
                    from_number = msg.get("from")
                    message_text = msg.get("text", {}).get("body", "")
                    message_id = msg.get("id")

                    logger.info(f"📱 {from_number} -> {business_phone}: {message_text}")

                    # ===============================
                    # BUSCAR TENANT PELO NÚMERO
                    # ===============================
                    tenant_result = await db.execute(
                        select(Tenant).where(
                            Tenant.settings["whatsapp_number"].astext == business_phone,
                            Tenant.active == True
                        )
                    )
                    tenant = tenant_result.scalar_one_or_none()

                    if tenant:
                        api_key = tenant.settings.get("dialog360_api_key")
                    else:
                        logger.warning(f"Tenant não encontrado para {business_phone}")
                        tenant_result = await db.execute(
                            select(Tenant).where(Tenant.active == True).limit(1)
                        )
                        tenant = tenant_result.scalar_one_or_none()
                        api_key = settings.dialog360_api_key

                    if not tenant:
                        logger.error("Nenhum tenant encontrado")
                        continue

                    if not api_key:
                        logger.error("API key do 360dialog não configurada")
                        continue

                    # ===============================
                    # LEAD
                    # ===============================
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

                    # ===============================
                    # SALVAR MENSAGEM RECEBIDA
                    # ===============================
                    message_in = Message(
                        lead_id=lead.id,
                        direction="inbound",
                        content=message_text,
                        channel="whatsapp",
                        external_id=message_id,
                    )
                    db.add(message_in)

                    # ===============================
                    # HISTÓRICO PARA A IA
                    # ===============================
                    messages_result = await db.execute(
                        select(Message)
                        .where(Message.lead_id == lead.id)
                        .order_by(Message.created_at.desc())
                        .limit(10)
                    )
                    history = messages_result.scalars().all()

                    messages_for_ai = []
                    for hist_msg in reversed(history):
                        role = "user" if hist_msg.direction == "inbound" else "assistant"
                        messages_for_ai.append({"role": role, "content": hist_msg.content})

                    messages_for_ai.append({"role": "user", "content": message_text})

                    # ===============================
                    # CONFIGURAR PROMPT
                    # ===============================
                    tenant_settings = tenant.settings or {}
                    niche = tenant_settings.get("niche", "services")
                    tone = tenant_settings.get("tone", "cordial")
                    company_name = tenant_settings.get("company_name", tenant.name)
                    niche_config = get_niche_config(niche)

                    system_prompt = f"""
Você é um assistente de atendimento da empresa {company_name}.

{niche_config.prompt_template if niche_config else "Atenda o cliente de forma profissional."}

Tom de voz: {tone}

IMPORTANTE:
- Seja natural e humano na conversa
- Faça perguntas para qualificar o lead
- Use emojis moderadamente se o tom for cordial
"""

                    # ===============================
                    # GERAR RESPOSTA DA IA
                    # ===============================
                    ai_messages = [{"role": "system", "content": system_prompt}] + messages_for_ai

                    result = await chat_completion(
                        messages=ai_messages,
                        max_tokens=500,
                    )

                    ai_response = result["content"]
                    logger.info(f"🤖 IA: {ai_response[:120]}")

                    # ===============================
                    # SALVAR RESPOSTA
                    # ===============================
                    message_out = Message(
                        lead_id=lead.id,
                        direction="outbound",
                        content=ai_response,
                        channel="whatsapp",
                    )
                    db.add(message_out)

                    if lead.status == "new":
                        lead.status = "contacted"

                    await db.commit()

                    # ===============================
                    # ENVIAR VIA 360DIALOG
                    # ===============================
                    await send_360dialog_message(api_key, from_number, ai_response)

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"❌ Erro no webhook 360dialog: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


# ======================================================
# TESTE DO WEBHOOK
# ======================================================
@router.get("/360dialog/test")
async def test_webhook():
    return {
        "status": "ok",
        "message": "360dialog webhook está ativo!",
        "webhook_url": "/api/v1/webhook/360dialog"
    }
