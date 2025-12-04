"""
WEBHOOK TWILIO WHATSAPP
=======================

Recebe mensagens do WhatsApp via Twilio e processa com a IA.
"""

from fastapi import APIRouter, Request, Response, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from src.infrastructure.database import get_db
from src.domain.entities import Lead, Message, Tenant
from src.infrastructure.services import chat_completion
from src.domain.prompts import get_niche_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["Webhook Twilio"])


def create_twiml_response(message: str) -> str:
    """Cria resposta TwiML manualmente sem depender do pacote twilio."""
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{message}</Message>
</Response>'''


@router.post("/twilio")
async def twilio_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Recebe mensagens do WhatsApp via Twilio Sandbox.
    
    O Twilio envia dados como form-urlencoded, não JSON.
    """
    try:
        # Twilio envia como form data
        form_data = await request.form()
        
        # Extrair dados da mensagem
        from_number = form_data.get("From", "")  # whatsapp:+5511999999999
        to_number = form_data.get("To", "")      # whatsapp:+14155238886
        body = form_data.get("Body", "")         # Texto da mensagem
        
        # Limpar números (remover "whatsapp:")
        from_number = from_number.replace("whatsapp:", "").replace("+", "")
        to_number = to_number.replace("whatsapp:", "").replace("+", "")
        
        logger.info(f"📱 Mensagem Twilio: {from_number} -> {to_number}: {body}")
        print(f"📱 Mensagem Twilio: {from_number} -> {to_number}: {body}")
        
        # Buscar tenant pelo canal (ou usar o primeiro tenant para teste)
        tenant_result = await db.execute(
            select(Tenant).where(Tenant.active == True).limit(1)
        )
        tenant = tenant_result.scalar_one_or_none()
        
        if not tenant:
            logger.error("Nenhum tenant ativo encontrado")
            return Response(
                content=create_twiml_response("Sistema indisponível"),
                media_type="application/xml"
            )
        
        # Buscar ou criar lead
        lead_result = await db.execute(
            select(Lead).where(
                Lead.tenant_id == tenant.id,
                Lead.phone == from_number
            )
        )
        lead = lead_result.scalar_one_or_none()
        
        if not lead:
            # Criar novo lead
            lead = Lead(
                tenant_id=tenant.id,
                phone=from_number,
                name=f"WhatsApp {from_number[-4:]}",
                source="whatsapp_twilio",
                status="new",
            )
            db.add(lead)
            await db.flush()
            logger.info(f"✨ Novo lead criado: {lead.id}")
            print(f"✨ Novo lead criado: {lead.id}")
        
        # Salvar mensagem recebida
        message_in = Message(
            tenant_id=tenant.id,
            lead_id=lead.id,
            direction="inbound",
            content=body,
            channel="whatsapp",
        )
        db.add(message_in)
        
        # Buscar histórico de mensagens para contexto
        messages_result = await db.execute(
            select(Message)
            .where(Message.lead_id == lead.id)
            .order_by(Message.created_at.desc())
            .limit(10)
        )
        history = messages_result.scalars().all()
        
        # Montar histórico para a IA
        messages_for_ai = []
        for msg in reversed(list(history)):
            role = "user" if msg.direction == "inbound" else "assistant"
            messages_for_ai.append({"role": role, "content": msg.content})
        
        # Adicionar mensagem atual
        messages_for_ai.append({"role": "user", "content": body})
        
        # Configurar prompt baseado no tenant
        settings = tenant.settings or {}
        niche = settings.get("niche", "services")
        tone = settings.get("tone", "cordial")
        company_name = settings.get("company_name", tenant.name)
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
        print(f"🤖 Resposta IA: {ai_response[:100]}...")
        
        # Salvar resposta da IA
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
        
        # Responder para o Twilio (formato TwiML)
        return Response(
            content=create_twiml_response(ai_response),
            media_type="application/xml"
        )
        
    except Exception as e:
        logger.error(f"❌ Erro no webhook Twilio: {str(e)}")
        print(f"❌ Erro no webhook Twilio: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Retornar resposta de erro
        return Response(
            content=create_twiml_response("Desculpe, ocorreu um erro. Tente novamente."),
            media_type="application/xml"
        )


@router.get("/twilio/test")
async def twilio_test():
    """Endpoint de teste para verificar se a rota está funcionando."""
    return {"status": "ok", "message": "Twilio webhook está ativo!"}