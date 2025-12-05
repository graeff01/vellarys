"""
WEBHOOK 360DIALOG WHATSAPP
==========================

Recebe mensagens via 360dialog e integra com o Velaris.
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


# ============================================================
# ENVIO DE MENSAGEM VIA 360DIALOG
# ============================================================
async def send_360dialog_message(api_key: str, to: str, text: str):
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
        "text": {"body": text},
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers)

        if resp.status_code == 200:
            logger.info(f"Mensagem enviada para {to}")
            return True
        
        logger.error(f"Erro ao enviar: {resp.text}")
        return False


# ============================================================
# VERIFICAÇÃO DO WEBHOOK (META/360DIALOG)
# ============================================================
@router.get("/360dialog")
async def verify_webhook(
    hub_mode: Optional[str] = None,
    hub_challenge: Optional[str] = None,
    hub_verify_token: Optional[str] = None,
):
    verify_token = settings.webhook_verify_token or "velaris_webhook"

    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        return Response(content=hub_challenge, media_type="text/plain")

    raise HTTPException(status_code=403, detail="Verificação falhou")


# ============================================================
# RECEBIMENTO DE MENSAGENS
# ============================================================
@router.post("/360dialog")
async def webhook_360dialog(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        data = await request.json()
        logger.info(f"Webhook recebido: {json.dumps(data)[:500]}")

        if data.get("object") != "whatsapp_business_account":
            return {"status": "ignored"}

        # Percorrer estrutura do payload
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") != "messages":
                    continue

                value = change.get("value", {})
                metadata = value.get("metadata", {})

                business_number = metadata.get("display_phone_number", "").replace("+", "")

                # ================================
                # Encontrar tenant pelo número
                # ================================
                q = await db.execute(
                    select(Tenant).where(
                        Tenant.settings["whatsapp_number"].astext == business_number,
                        Tenant.active == True
                    )
                )
                tenant = q.scalar_one_or_none()

                if not tenant:
                    logger.error(f"Nenhum tenant usa o número {business_number}")
                    continue

                api_key = tenant.settings.get("dialog360_api_key")
                if not api_key:
                    logger.error(f"Tenant {tenant.slug} sem API KEY do 360dialog configurada.")
                    continue

                # ================================
                # Processar mensagens
                # ================================
                for msg in value.get("messages", []):
                    if msg.get("type") != "text":
                        continue

                    from_number = msg.get("from")
                    text = msg.get("text", {}).get("body")

                    # ================================
                    # Buscar ou criar lead
                    # ================================
                    q = await db.execute(
                        select(Lead).where(
                            Lead.tenant_id == tenant.id,
                            Lead.phone == from_number,
                        )
                    )
                    lead = q.scalar_one_or_none()

                    if not lead:
                        lead = Lead(
                            tenant_id=tenant.id,
                            phone=from_number,
                            name=f"WhatsApp {from_number[-4:]}"
                        )
                        db.add(lead)
                        await db.flush()

                    # ================================
                    # Salvar mensagem recebida
                    # ================================
                    msg_in = Message(
                        lead_id=lead.id,
                        role="user",
                        content=text,
                    )
                    db.add(msg_in)

                    # ================================
                    # Construir histórico para IA
                    # ================================
                    hist_q = await db.execute(
                        select(Message)
                        .where(Message.lead_id == lead.id)
                        .order_by(Message.created_at.asc())
                    )
                    history = hist_q.scalars().all()

                    messages_ai = []
                    for m in history:
                        role = "user" if m.role == "user" else "assistant"
                        messages_ai.append({"role": role, "content": m.content})

                    # ================================
                    # Prompt da empresa
                    # ================================
                    cfg = tenant.settings or {}
                    company = cfg.get("company_name", tenant.name)
                    niche = cfg.get("niche", "services")
                    tone = cfg.get("tone", "cordial")

                    niche_prompt = get_niche_config(niche).prompt_template if get_niche_config(niche) else ""

                    system_prompt = f"""
Você é o assistente oficial da empresa {company}.
Atenda como humano, natural e profissional.

{niche_prompt}

Tom de voz: {tone}
"""

                    ai_messages = [{"role": "system", "content": system_prompt}] + messages_ai

                    # ================================
                    # Chamar IA
                    # ================================
                    result = await chat_completion(messages=ai_messages)
                    ai_text = result["content"]

                    # ================================
                    # Salvar resposta
                    # ================================
                    msg_out = Message(
                        lead_id=lead.id,
                        role="assistant",
                        content=ai_text,
                    )
                    db.add(msg_out)

                    await db.commit()

                    # ================================
                    # Enviar via WhatsApp
                    # ================================
                    await send_360dialog_message(api_key, from_number, ai_text)

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Erro no webhook 360dialog: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/360dialog/test")
async def test():
    return {"status": "ok", "message": "Webhook 360dialog rodando!"}
