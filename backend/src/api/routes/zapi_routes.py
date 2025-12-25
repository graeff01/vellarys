"""
ROTAS Z-API - Webhooks
======================
Recebe eventos do Z-API (mensagens, status, conexao)

Documentacao: https://developer.z-api.io/webhooks/introduction
"""

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from fastapi import APIRouter, Request, Depends, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.domain.entities import Tenant, Channel
from src.application.use_cases.process_message import process_message
from src.infrastructure.services.zapi_service import get_zapi_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/zapi", tags=["Z-API Webhooks"])

import hashlib
from datetime import datetime, timedelta

# Cache de mensagens processadas (em memória)
processed_messages = {}

def generate_message_hash(phone: str, content: str, timestamp: datetime) -> str:
    """Gera hash único para deduplicação."""
    # Arredonda timestamp para 5 segundos
    rounded_ts = int(timestamp.timestamp() / 5) * 5
    key = f"{phone}:{content}:{rounded_ts}"
    return hashlib.md5(key.encode()).hexdigest()

def is_duplicate_message(phone: str, content: str, timestamp: datetime) -> bool:
    """Verifica se mensagem já foi processada."""
    msg_hash = generate_message_hash(phone, content, timestamp)
    
    # Limpa mensagens antigas (mais de 1 minuto)
    cutoff = datetime.now() - timedelta(minutes=1)
    global processed_messages
    processed_messages = {
        k: v for k, v in processed_messages.items() 
        if v > cutoff
    }
    
    # Verifica duplicata
    if msg_hash in processed_messages:
        return True
    
    # Registra como processada
    processed_messages[msg_hash] = datetime.now()
    return False

# ════════════════════════════════════════════════════════════════
# SISTEMA DE DEDUPLICAÇÃO E LOCKS
# ════════════════════════════════════════════════════════════════

# Cache de messageIds processados (últimos 10 minutos)
_processed_messages = {}  # {messageId: timestamp}
_message_cache_lock = asyncio.Lock()

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
        logger.info(f"Z-API Webhook recebido: {payload.get('phone', 'unknown')}")
        
        # ════════════════════════════════════════════════════════════════
        # BUG FIX #1: DEDUPLICAÇÃO DE MENSAGENS
        # ════════════════════════════════════════════════════════════════
        message_id = payload.get("messageId")
        
        if message_id:
            async with _message_cache_lock:
                # Verifica se já processamos este messageId
                if message_id in _processed_messages:
                    logger.warning(f"⚠️ Webhook duplicado detectado: {message_id}")
                    return {"status": "ok", "message": "already_processed"}
                
                # Marca como processado
                _processed_messages[message_id] = datetime.now(timezone.utc)
            
            # Limpa cache antigo (async, não bloqueia)
            asyncio.create_task(_cleanup_message_cache())
        else:
            logger.warning("⚠️ Webhook sem messageId - deduplicação desabilitada")
        
        # Ignora mensagens de grupo
        if payload.get("isGroup"):
            logger.debug("Ignorando mensagem de grupo")
            return {"status": "ignored", "reason": "group_message"}
        
        # Ignora mensagens enviadas por mim
        if payload.get("fromMe"):
            logger.debug("Ignorando mensagem enviada por mim")
            return {"status": "ignored", "reason": "from_me"}
        
        # Extrai dados da mensagem
        phone = payload.get("phone")
        sender_name = payload.get("pushName") or payload.get("senderName")
        instance_id = payload.get("instanceId")
        
        # Extrai texto da mensagem (pode vir em diferentes formatos)
        message_text = None
        
        # Texto simples
        if payload.get("text"):
            message_text = payload["text"].get("message")
        
        # Imagem com legenda
        elif payload.get("image"):
            message_text = payload["image"].get("caption") or "[Imagem recebida]"
        
        # Audio
        elif payload.get("audio"):
            message_text = "[Audio recebido]"
        
        # Documento
        elif payload.get("document"):
            message_text = payload["document"].get("caption") or "[Documento recebido]"
        
        # Video
        elif payload.get("video"):
            message_text = payload["video"].get("caption") or "[Video recebido]"
        
        # Sticker
        elif payload.get("sticker"):
            message_text = "[Sticker recebido]"
        
        # Localizacao
        elif payload.get("location"):
            message_text = "[Localizacao recebida]"
        
        # Contato
        elif payload.get("contact"):
            message_text = "[Contato recebido]"
        
        # Botao clicado
        elif payload.get("buttonsResponseMessage"):
            message_text = payload["buttonsResponseMessage"].get("selectedButtonId") or "[Botao clicado]"
        
        # Lista selecionada
        elif payload.get("listResponseMessage"):
            message_text = payload["listResponseMessage"].get("title") or "[Opcao selecionada]"
        # Deduplicação
        if is_duplicate_message(phone, message_text, datetime.now()):
            logger.warning(f"⚠️ Mensagem duplicada ignorada: {phone}")
            return {"success": True, "message": "Duplicata ignorada"}
                    
        if not phone or not message_text:
            logger.warning(f"Payload incompleto: phone={phone}, text={message_text}")
            return {"status": "ignored", "reason": "incomplete_payload"}
        
        # ==============================================
        # BUSCA TENANT PELO INSTANCE_ID
        # ==============================================
        # Por enquanto, busca o primeiro tenant ativo com canal whatsapp
        # TODO: Mapear instance_id para tenant (tabela ou campo)
        
        result = await db.execute(
            select(Channel)
            .where(Channel.type == "whatsapp")
            .where(Channel.active == True)
        )
        channel = result.scalar_one_or_none()
        
        if not channel:
            logger.error("Nenhum canal WhatsApp ativo encontrado")
            return {"status": "error", "reason": "no_channel"}
        
        # Busca tenant do canal
        result = await db.execute(
            select(Tenant)
            .where(Tenant.id == channel.tenant_id)
            .where(Tenant.active == True)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            logger.error(f"Tenant nao encontrado para channel {channel.id}")
            return {"status": "error", "reason": "no_tenant"}
        
        logger.info(f"Processando para tenant: {tenant.slug}")
        
        # ════════════════════════════════════════════════════════════════
        # BUG FIX #2: LOCK POR TELEFONE (Previne processamento paralelo)
        # ════════════════════════════════════════════════════════════════
        
        async with _phone_locks[phone]:
            logger.info(f"🔒 Lock adquirido para {phone}")
            
            # ==============================================
            # PROCESSA A MENSAGEM (com timeout de 30s)
            # ==============================================
            
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
                    timeout=30.0  # Timeout de 30 segundos
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
        
        # ==============================================
        # ENVIA RESPOSTA
        # ==============================================
        
        if result.get("reply"):
            # Busca credenciais Z-API do canal ou usa as globais
            zapi_instance = None
            zapi_token = None
            
            if channel.config:
                zapi_instance = channel.config.get("instance_id") or channel.config.get("zapi_instance_id")
                zapi_token = channel.config.get("token") or channel.config.get("zapi_token")
            
            # Cria cliente Z-API
            zapi = get_zapi_client(instance_id=zapi_instance, token=zapi_token)
            
            # Delay baseado no typing_delay calculado
            typing_delay = result.get("typing_delay", 2)
            if typing_delay > 0:
                logger.info(f"💬 Aguardando {typing_delay}s (simulando digitação)...")
                await asyncio.sleep(min(typing_delay, 5))  # Max 5s
            
            # Envia resposta
            send_result = await zapi.send_text(
                phone=phone, 
                message=result["reply"],
                delay_message=2  # Simula digitacao
            )
            
            if not send_result.get("success"):
                logger.error(f"Erro enviando resposta: {send_result.get('error')}")
        
        return {
            "status": "processed",
            "lead_id": result.get("lead_id"),
            "is_new": result.get("is_new_lead"),
            "qualification": result.get("qualification"),
        }
        
    except Exception as e:
        logger.error(f"Erro no webhook Z-API receive: {e}", exc_info=True)
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
        
        logger.info(f"Z-API Conectado! Instance: {instance_id}, Phone: {phone}")
        
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
        
        logger.warning(f"Z-API Desconectado! Instance: {instance_id}, Reason: {reason}")
        
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