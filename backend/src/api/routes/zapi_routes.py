"""
ROTAS Z-API - Webhooks (VERSÃO CORRIGIDA - SEM DUPLICAÇÃO)
============================================================
Recebe eventos do Z-API (mensagens, status, conexao)

CORREÇÕES:
- Deduplicação robusta por messageId
- Fallback para mensagens sem messageId
- Locks por telefone para prevenir race conditions
- Código limpo e organizado

Documentacao: https://developer.z-api.io/webhooks/introduction
"""

import logging
import asyncio
import hashlib
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from fastapi import APIRouter, Request, Depends, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.domain.entities import Tenant, Channel
from src.application.use_cases.process_message import process_message
from src.infrastructure.services import transcribe_audio_url
from src.infrastructure.services.zapi_service import get_zapi_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/zapi", tags=["Z-API Webhooks"])


# ════════════════════════════════════════════════════════════════
# SISTEMA DE DEDUPLICAÇÃO (SIMPLIFICADO E ROBUSTO)
# ════════════════════════════════════════════════════════════════

# Cache de messageIds processados (últimos 10 minutos)
_processed_messages = {}  # {messageId: timestamp}
_message_cache_lock = asyncio.Lock()

# Cache de mensagens sem messageId (fallback - últimos 2 minutos)
_fallback_cache = {}  # {phone:content_hash: timestamp}
_fallback_cache_lock = asyncio.Lock()

# Locks por telefone (previne race conditions)
_phone_locks = defaultdict(asyncio.Lock)


async def _cleanup_message_cache():
    """Remove messageIds processados há mais de 10 minutos."""
    async with _message_cache_lock:
        now = datetime.now(timezone.utc)
        to_remove = [
            msg_id for msg_id, timestamp in _processed_messages.items()
            if (now - timestamp).total_seconds() > 600  # 10 minutos
        ]
        for msg_id in to_remove:
            del _processed_messages[msg_id]
        
        if to_remove:
            logger.debug(f"🧹 Cache limpo: {len(to_remove)} messageIds removidos")


async def _cleanup_fallback_cache():
    """Remove mensagens do fallback cache após 2 minutos."""
    async with _fallback_cache_lock:
        now = datetime.now(timezone.utc)
        to_remove = [
            key for key, timestamp in _fallback_cache.items()
            if (now - timestamp).total_seconds() > 120  # 2 minutos
        ]
        for key in to_remove:
            del _fallback_cache[key]
        
        if to_remove:
            logger.debug(f"🧹 Fallback cache limpo: {len(to_remove)} entradas removidas")


def _generate_fallback_key(phone: str, content: str) -> str:
    """Gera chave única para mensagens sem messageId."""
    # Hash simples: phone + primeiros 100 chars da mensagem
    key_data = f"{phone}:{content[:100]}"
    return hashlib.md5(key_data.encode()).hexdigest()


async def _is_duplicate_fallback(phone: str, content: str) -> bool:
    """
    Verifica duplicação para mensagens sem messageId (fallback).
    Usa hash de phone + conteúdo (sem timestamp).
    """
    async with _fallback_cache_lock:
        key = _generate_fallback_key(phone, content)
        
        if key in _fallback_cache:
            return True
        
        # Registra como processado
        _fallback_cache[key] = datetime.now(timezone.utc)
        
        # Limpa cache antigo (async)
        asyncio.create_task(_cleanup_fallback_cache())
        
        return False


# ============================================
# WEBHOOK: MENSAGEM RECEBIDA
# ============================================

@router.post("/receive")
async def zapi_receive_message(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook principal - recebe mensagens do WhatsApp.
    
    Payload exemplo:
    {
        "instanceId": "...",
        "phone": "5551999999999",
        "fromMe": false,
        "momment": 1234567890,
        "messageId": "...",
        "pushName": "Nome do Contato",
        "text": {
            "message": "Ola, quero saber mais!"
        },
        "isGroup": false
    }
    """
    try:
        payload = await request.json()
        
        # Log para debug
        logger.info(f"📥 Z-API Webhook recebido: {payload.get('phone', 'unknown')}")
        
        # ════════════════════════════════════════════════════════════════
        # PASSO 1: IGNORA MENSAGENS DE GRUPO E FROM_ME
        # ════════════════════════════════════════════════════════════════
        
        if payload.get("isGroup"):
            logger.debug("Ignorando mensagem de grupo")
            return {"status": "ignored", "reason": "group_message"}
        
        if payload.get("fromMe"):
            logger.debug("Ignorando mensagem enviada por mim")
            return {"status": "ignored", "reason": "from_me"}
        
        # ════════════════════════════════════════════════════════════════
        # NOVO PASSO 2: BUSCA TENANT (NECESSÁRIO PARA CONTEXTO DE TRANSCRIÇÃO)
        # ════════════════════════════════════════════════════════════════
        result = await db.execute(
            select(Channel)
            .where(Channel.type == "whatsapp")
            .where(Channel.active == True)
        )
        channel = result.scalar_one_or_none()
        
        if not channel:
            logger.error("Nenhum canal WhatsApp ativo encontrado")
            return {"status": "error", "reason": "no_channel"}
        
        result = await db.execute(
            select(Tenant)
            .where(Tenant.id == channel.tenant_id)
            .where(Tenant.active == True)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            logger.error(f"Tenant nao encontrado para channel {channel.id}")
            return {"status": "error", "reason": "no_tenant"}

        # ════════════════════════════════════════════════════════════════
        # PASSO 3: EXTRAI DADOS DA MENSAGEM
        # ════════════════════════════════════════════════════════════════
        
        phone = payload.get("phone")
        sender_name = payload.get("pushName") or payload.get("senderName")
        instance_id = payload.get("instanceId")
        message_id = payload.get("messageId")
        
        # Extrai texto da mensagem (pode vir em diferentes formatos)
        message_text = None
        
        if payload.get("text"):
            message_text = payload["text"].get("message")
        elif payload.get("image"):
            message_text = payload["image"].get("caption") or "[Imagem recebida]"
        elif payload.get("audio"):
            audio_url = payload["audio"].get("audioUrl")
            if audio_url:
                logger.info(f"🎙️ Áudio detectado! Iniciando transcrição Whisper...")
                
                # Build context-aware prompt for Whisper
                whisper_prompt = "Industrial, São Luís, Mathias Velho, Harmonia, Mato Grande, Fátima, Rio Branco, Ilha das Garças, Centro, Marechal Rondon, Nossa Senhora das Graças, Niterói, Brigadeira, São José, Igara, Guajuviras, Estância Velha, Olaria, Canoas, Rio Grande do Sul, imobiliária, corretor, apartamento, casa, FGTS, financiamento."
                if tenant and tenant.settings:
                    company_name = tenant.settings.get("company_name", "")
                    if company_name:
                        whisper_prompt = f"{company_name}, {whisper_prompt}"
                
                transcription = await transcribe_audio_url(audio_url, prompt=whisper_prompt)
                if transcription:
                    message_text = transcription
                    logger.info(f"✅ Áudio transcrito: {message_text[:50]}...")
                else:
                    message_text = "[Áudio recebido (falha na transcrição)]"
            else:
                message_text = "[Áudio recebido]"
        elif payload.get("document"):
            message_text = payload["document"].get("caption") or "[Documento recebido]"
        elif payload.get("video"):
            message_text = payload["video"].get("caption") or "[Video recebido]"
        elif payload.get("sticker"):
            message_text = "[Sticker recebido]"
        elif payload.get("location"):
            message_text = "[Localizacao recebida]"
        elif payload.get("contact"):
            message_text = "[Contato recebido]"
        elif payload.get("buttonsResponseMessage"):
            message_text = payload["buttonsResponseMessage"].get("selectedButtonId") or "[Botao clicado]"
        elif payload.get("listResponseMessage"):
            message_text = payload["listResponseMessage"].get("title") or "[Opcao selecionada]"
        
        if not phone or not message_text:
            logger.warning(f"Payload incompleto: phone={phone}, text={message_text}")
            return {"status": "ignored", "reason": "incomplete_payload"}
        
        # ════════════════════════════════════════════════════════════════
        # PASSO 4: DEDUPLICAÇÃO (PRIORIDADE: messageId)
        # ════════════════════════════════════════════════════════════════
        
        if message_id:
            # Usa messageId (método confiável)
            async with _message_cache_lock:
                if message_id in _processed_messages:
                    logger.info(f"✅ Webhook duplicado bloqueado (messageId): {message_id}")
                    return {"status": "ok", "message": "already_processed"}
                
                # Marca como processado
                _processed_messages[message_id] = datetime.now(timezone.utc)
            
            # Limpa cache antigo (async, não bloqueia)
            asyncio.create_task(_cleanup_message_cache())
        
        else:
            # Fallback: usa hash de phone + conteúdo (sem messageId)
            logger.warning("⚠️ Webhook sem messageId - usando fallback")
            
            is_duplicate = await _is_duplicate_fallback(phone, message_text)
            if is_duplicate:
                logger.warning(f"⚠️ Webhook duplicado detectado (fallback): {phone}")
                return {"status": "ok", "message": "already_processed_fallback"}
        
        logger.info(f"🏢 Processando para tenant: {tenant.slug}")
        
        # ════════════════════════════════════════════════════════════════
        # PASSO 5: LOCK POR TELEFONE + PROCESSA MENSAGEM
        # ════════════════════════════════════════════════════════════════
        
        async with _phone_locks[phone]:
            logger.info(f"🔒 Lock adquirido para {phone}")
            
            try:
                result = await asyncio.wait_for(
                    process_message(
                        db=db,
                        tenant_slug=tenant.slug,
                        channel_type="whatsapp",
                        external_id=phone,
                        content=message_text,
                        sender_name=sender_name,
                        sender_phone=phone,
                    ),
                    timeout=30.0
                )
                
                logger.info(f"✅ Processamento concluído para {phone}")
                
            except asyncio.TimeoutError:
                logger.error(f"⏱️ Timeout processando mensagem de {phone}")
                return {
                    "status": "error",
                    "reason": "processing_timeout",
                    "message": "Processamento excedeu 30 segundos"
                }
            
            finally:
                logger.info(f"🔓 Lock liberado para {phone}")
        
        # ════════════════════════════════════════════════════════════════
        # PASSO 6: ENVIA RESPOSTA
        # ════════════════════════════════════════════════════════════════
        
        if result.get("reply"):
            zapi_instance = None
            zapi_token = None
            
            if channel.config:
                zapi_instance = channel.config.get("instance_id") or channel.config.get("zapi_instance_id")
                zapi_token = channel.config.get("token") or channel.config.get("zapi_token")
            
            zapi = get_zapi_client(instance_id=zapi_instance, token=zapi_token)
            
            typing_delay = result.get("typing_delay", 2)
            if typing_delay > 0:
                logger.info(f"💬 Aguardando {typing_delay}s (simulando digitação)...")
                await asyncio.sleep(min(typing_delay, 5))
            
            send_result = await zapi.send_text(
                phone=phone, 
                message=result["reply"],
                delay_message=2
            )
            
            if not send_result.get("success"):
                logger.error(f"❌ Erro enviando resposta: {send_result.get('error')}")
        
        return {
            "status": "processed",
            "lead_id": result.get("lead_id"),
            "is_new": result.get("is_new_lead"),
            "qualification": result.get("qualification"),
        }
        
    except Exception as e:
        logger.error(f"❌ Erro no webhook Z-API receive: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


# ============================================
# WEBHOOK: STATUS DA MENSAGEM
# ============================================

@router.post("/status")
async def zapi_message_status(request: Request):
    """
    Webhook de status de mensagem enviada.
    
    Status possiveis:
    - PENDING: Na fila
    - SENT: Enviada
    - RECEIVED: Recebida pelo destinatario
    - READ: Lida pelo destinatario
    - PLAYED: Audio reproduzido
    - ERROR: Erro no envio
    """
    try:
        payload = await request.json()
        
        status = payload.get("status")
        message_id = payload.get("messageId")
        phone = payload.get("phone")
        
        logger.debug(f"Z-API Status: {status} - Phone: {phone} - MsgID: {message_id}")
        
        # Aqui voce pode atualizar o status da mensagem no banco
        # se quiser rastrear entregas/leituras
        
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"Erro no webhook status: {e}")
        return {"status": "error", "message": str(e)}


# ============================================
# WEBHOOK: CONEXAO
# ============================================

@router.post("/connect")
async def zapi_connected(request: Request):
    """
    Webhook chamado quando instancia conecta.
    """
    try:
        payload = await request.json()
        
        instance_id = payload.get("instanceId")
        phone = payload.get("phone")
        
        logger.info(f"✅ Z-API Conectado! Instance: {instance_id}, Phone: {phone}")
        
        # Aqui voce pode:
        # - Atualizar status do canal no banco
        # - Enviar notificacao para o gestor
        # - Registrar log de auditoria
        
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"Erro no webhook connect: {e}")
        return {"status": "error", "message": str(e)}


# ============================================
# WEBHOOK: DESCONEXAO
# ============================================

@router.post("/disconnect")
async def zapi_disconnected(request: Request):
    """
    Webhook chamado quando instancia desconecta.
    """
    try:
        payload = await request.json()
        
        instance_id = payload.get("instanceId")
        reason = payload.get("reason")
        
        logger.warning(f"⚠️ Z-API Desconectado! Instance: {instance_id}, Reason: {reason}")
        
        # Aqui voce pode:
        # - Atualizar status do canal no banco
        # - Enviar ALERTA para o gestor (importante!)
        # - Tentar reconectar automaticamente
        
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"Erro no webhook disconnect: {e}")
        return {"status": "error", "message": str(e)}


# ============================================
# ENDPOINT: VERIFICAR STATUS
# ============================================

@router.get("/status")
async def check_zapi_status():
    """
    Verifica status da conexao Z-API.
    """
    try:
        zapi = get_zapi_client()
        
        if not zapi.is_configured():
            return {
                "connected": False,
                "error": "Z-API nao configurado. Verifique ZAPI_INSTANCE_ID e ZAPI_TOKEN."
            }
        
        result = await zapi.check_connection()
        
        return {
            "connected": result.get("connected", False),
            "details": result.get("data"),
            "error": result.get("error")
        }
        
    except Exception as e:
        logger.error(f"Erro verificando status Z-API: {e}")
        return {"connected": False, "error": str(e)}


# ============================================
# ENDPOINT: ENVIAR MENSAGEM TESTE
# ============================================

@router.post("/test-send")
async def test_send_message(request: Request):
    """
    Endpoint para testar envio de mensagem.
    
    Body:
    {
        "phone": "5551999999999",
        "message": "Teste de envio!"
    }
    """
    try:
        body = await request.json()
        
        phone = body.get("phone")
        message = body.get("message", "Teste de envio via Z-API!")
        
        if not phone:
            return {"success": False, "error": "Phone obrigatorio"}
        
        zapi = get_zapi_client()
        
        if not zapi.is_configured():
            return {"success": False, "error": "Z-API nao configurado"}
        
        result = await zapi.send_text(phone, message)
        
        return result
        
    except Exception as e:
        logger.error(f"Erro no teste de envio: {e}")
        return {"success": False, "error": str(e)}


# ============================================
# ENDPOINT: OBTER QR CODE
# ============================================

@router.get("/qrcode")
async def get_qrcode():
    """
    Obtem QR Code para conectar instancia.
    """
    try:
        zapi = get_zapi_client()
        
        if not zapi.is_configured():
            return {"success": False, "error": "Z-API nao configurado"}
        
        result = await zapi.get_qrcode()
        
        return result
        
    except Exception as e:
        logger.error(f"Erro obtendo QR Code: {e}")
        return {"success": False, "error": str(e)}