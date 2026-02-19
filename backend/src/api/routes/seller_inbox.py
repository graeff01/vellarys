"""
API: INBOX DO CORRETOR
======================
Permite que corretores façam login no CRM e atendam seus leads.

NOVO FLUXO (handoff_mode = "crm_inbox"):
1. IA atende e qualifica lead
2. Sistema atribui lead ao corretor (seller)
3. Corretor recebe notificação
4. Corretor faz login no CRM
5. Corretor vê seus leads no inbox
6. Corretor clica "Assumir Conversa"
7. Corretor responde pelo CRM (usando WhatsApp da empresa)
8. IA para de responder automaticamente

Fluxo antigo (handoff_mode = "whatsapp_pessoal") continua funcionando normalmente.
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select, and_, or_, func, update as sql_update
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from src.api.dependencies import get_current_user
from src.domain.entities import User, Seller, Lead, Message
from src.domain.entities.lead_note import LeadNote
from src.domain.entities.handoff_history import HandoffHistory
from src.domain.entities.response_template import ResponseTemplate
from src.domain.entities.enums import UserRole, LeadStatus
from src.infrastructure.database import async_session
from src.infrastructure.services.whatsapp_service import send_whatsapp_message, get_profile_picture

# Imports condicionais - permite deploy mesmo se dependencies faltarem
try:
    from src.infrastructure.services.sse_service import event_stream_generator, broadcast_new_message, broadcast_lead_updated
    from src.infrastructure.services.storage_service import storage_service
    from src.infrastructure.services.template_interpolation_service import template_service
    from src.infrastructure.services.message_status_service import message_status_service
    ADVANCED_FEATURES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Advanced features disabled: {e}")
    event_stream_generator = None
    broadcast_new_message = None
    broadcast_lead_updated = None
    storage_service = None
    template_service = None
    message_status_service = None
    ADVANCED_FEATURES_AVAILABLE = False


router = APIRouter(prefix="/seller/inbox", tags=["Seller Inbox"])


# ==========================================
# SCHEMAS
# ==========================================

class InboxLeadResponse(BaseModel):
    """Lead no inbox do corretor."""
    id: int
    name: str
    phone: str
    status: str
    qualification: Optional[str]
    attended_by: Optional[str]

    # Métricas da conversa
    unread_messages: int
    last_message_at: Optional[datetime]
    last_message_preview: Optional[str]

    # Informações do lead
    city: Optional[str]
    interest: Optional[str]
    budget: Optional[str]
    profile_picture_url: Optional[str]  # Foto de perfil do WhatsApp

    # Controle
    is_taken_over: bool  # True se corretor já assumiu
    seller_took_over_at: Optional[datetime]

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Mensagem no histórico."""
    id: int
    role: str
    content: str
    created_at: datetime
    sender_type: Optional[str]  # "ai", "seller", "manager", "system"
    sender_user_id: Optional[int]
    sender_name: Optional[str]  # Nome do corretor que enviou

    class Config:
        from_attributes = True


class SendMessageRequest(BaseModel):
    """Request para enviar mensagem."""
    content: str


class TakeOverResponse(BaseModel):
    """Response quando corretor assume conversa."""
    success: bool
    message: str
    lead_id: int
    attended_by: str
    took_over_at: datetime


# ==========================================
# NOVOS SCHEMAS (13 FUNCIONALIDADES)
# ==========================================

class LeadNoteResponse(BaseModel):
    """Anotação interna sobre lead."""
    id: int
    lead_id: int
    author_id: int
    author_name: str
    content: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CreateNoteRequest(BaseModel):
    """Request para criar nota."""
    content: str


class ResponseTemplateResponse(BaseModel):
    """Template de resposta rápida."""
    id: int
    name: str
    shortcut: Optional[str]
    content: str
    category: Optional[str]
    is_active: bool
    usage_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class CreateTemplateRequest(BaseModel):
    """Request para criar template."""
    name: str
    shortcut: Optional[str] = None
    content: str
    category: Optional[str] = None


class UpdateTemplateRequest(BaseModel):
    """Request para atualizar template."""
    name: Optional[str] = None
    shortcut: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None


class ArchiveLeadRequest(BaseModel):
    """Request para arquivar lead."""
    reason: Optional[str] = None


class MetricsResponse(BaseModel):
    """Métricas de performance."""
    total_leads: int
    active_conversations: int
    avg_first_response_time_seconds: Optional[float]
    total_messages_sent: int
    total_messages_received: int
    conversion_rate: Optional[float]
    sla_compliance: Optional[float]  # % de leads respondidos em < 5min


# ==========================================
# HELPERS
# ==========================================

async def get_seller_from_user(user: User) -> Seller:
    """Busca o Seller vinculado ao User logado."""

    if user.role != UserRole.SELLER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas corretores podem acessar o inbox"
        )

    async with async_session() as session:
        result = await session.execute(
            select(Seller)
            .where(Seller.user_id == user.id)
            .where(Seller.tenant_id == user.tenant_id)
        )
        seller = result.scalar_one_or_none()

        if not seller:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Corretor não encontrado. Contate o administrador para vincular seu usuário."
            )

        return seller


def get_last_message_preview(messages: List[Message]) -> Optional[str]:
    """Retorna preview da última mensagem."""
    if not messages:
        return None

    last = messages[-1]
    preview = last.content[:50]

    if len(last.content) > 50:
        preview += "..."

    return preview


# ==========================================
# ENDPOINTS
# ==========================================

@router.get("/leads", response_model=List[InboxLeadResponse])
async def list_inbox_leads(
    current_user: User = Depends(get_current_user),
    status_filter: Optional[str] = None,
    attended_filter: Optional[str] = None,  # "ai", "seller", "all"
):
    """
    Lista leads atribuídos ao corretor logado.

    Filtros:
    - status_filter: Filtrar por status do lead (novo, qualificado, etc)
    - attended_filter: "ai" (ainda com IA), "seller" (já assumido), "all"
    """

    seller = await get_seller_from_user(current_user)

    async with async_session() as session:
        # Query base: leads atribuídos ao seller
        query = (
            select(Lead)
            .where(Lead.assigned_seller_id == seller.id)
            .where(Lead.tenant_id == current_user.tenant_id)
            .options(selectinload(Lead.messages))
            .order_by(Lead.updated_at.desc())
        )

        # Filtro por status
        if status_filter:
            query = query.where(Lead.status == status_filter)

        # Filtro por quem está atendendo
        if attended_filter and attended_filter != "all":
            query = query.where(Lead.attended_by == attended_filter)

        result = await session.execute(query)
        leads = result.scalars().all()

        # Monta response
        inbox_leads = []
        for lead in leads:
            # Conta mensagens não lidas (mensagens após o corretor assumir ou últimas 24h)
            unread_count = 0
            if lead.seller_took_over_at:
                unread_count = len([
                    m for m in lead.messages
                    if m.created_at > lead.seller_took_over_at and m.role == "user"
                ])
            else:
                # Se ainda não assumiu, conta mensagens do lead (user)
                unread_count = len([m for m in lead.messages if m.role == "user"])

            inbox_leads.append(InboxLeadResponse(
                id=lead.id,
                name=lead.name or "Lead",
                phone=lead.phone,
                status=lead.status,
                qualification=lead.qualification,
                attended_by=lead.attended_by or "ai",
                unread_messages=unread_count,
                last_message_at=lead.messages[-1].created_at if lead.messages else None,
                last_message_preview=get_last_message_preview(lead.messages),
                city=lead.custom_data.get("city") if lead.custom_data else None,
                interest=lead.custom_data.get("interest") if lead.custom_data else None,
                budget=lead.custom_data.get("budget") if lead.custom_data else None,
                profile_picture_url=lead.profile_picture_url,
                is_taken_over=(lead.attended_by == "seller"),
                seller_took_over_at=lead.seller_took_over_at
            ))

        return inbox_leads


@router.get("/leads/{lead_id}/messages", response_model=List[MessageResponse])
async def get_lead_conversation(
    lead_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Retorna histórico completo de mensagens do lead.

    Inclui:
    - Mensagens da IA
    - Mensagens do lead
    - Mensagens do corretor
    - Mensagens de outros corretores (se houver)
    """

    seller = await get_seller_from_user(current_user)

    async with async_session() as session:
        # Busca lead para verificar atribuição
        lead_result = await session.execute(
            select(Lead)
            .where(Lead.id == lead_id)
            .where(Lead.tenant_id == current_user.tenant_id)
        )
        lead = lead_result.scalar_one_or_none()

        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead não encontrado"
            )

        # Verifica se está atribuído ao corretor
        if lead.assigned_seller_id != seller.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Este lead não está atribuído a você"
            )

        # Busca mensagens
        messages_result = await session.execute(
            select(Message)
            .where(Message.lead_id == lead_id)
            .options(selectinload(Message.sender_user))
            .order_by(Message.created_at.asc())
        )
        messages = messages_result.scalars().all()

        # Monta response com nome do sender
        response_messages = []
        for msg in messages:
            sender_name = None
            if msg.sender_user:
                sender_name = msg.sender_user.name
            elif msg.sender_type == "ai":
                sender_name = "Assistente IA"
            elif msg.role == "user":
                sender_name = "Cliente"

            response_messages.append(MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
                sender_type=msg.sender_type,
                sender_user_id=msg.sender_user_id,
                sender_name=sender_name
            ))

        return response_messages


@router.post("/leads/{lead_id}/take-over", response_model=TakeOverResponse)
async def take_over_conversation(
    lead_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Corretor assume a conversa.

    Ações:
    1. Muda lead.attended_by para "seller"
    2. Registra lead.seller_took_over_at
    3. IA para de responder automaticamente
    4. Corretor passa a responder via CRM
    """

    seller = await get_seller_from_user(current_user)

    async with async_session() as session:
        # Busca lead
        lead_result = await session.execute(
            select(Lead)
            .where(Lead.id == lead_id)
            .where(Lead.tenant_id == current_user.tenant_id)
        )
        lead = lead_result.scalar_one_or_none()

        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead não encontrado"
            )

        # Verifica se está atribuído ao corretor
        if lead.assigned_seller_id != seller.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Este lead não está atribuído a você"
            )

        # Marca como assumido pelo corretor
        lead.attended_by = "seller"
        lead.seller_took_over_at = datetime.now(timezone.utc)
        lead.status = LeadStatus.HANDED_OFF  # Atualiza status

        # Adiciona mensagem de sistema
        system_message = Message(
            lead_id=lead.id,
            role="system",
            content=f"🔄 {current_user.name} assumiu o atendimento",
            sender_type="system",
            created_at=datetime.now(timezone.utc)
        )
        session.add(system_message)

        await session.commit()
        await session.refresh(lead)

        # 🆕 ENVIA MENSAGEM VIA WHATSAPP avisando que o vendedor assumiu
        try:
            takeover_message = f"Olá! Agora você está sendo atendido por *{seller.name}*, nosso especialista. Como posso ajudar? 😊"
            result = await send_whatsapp_message(
                to=lead.phone,
                message=takeover_message
            )
            if not result.get("success"):
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"❌ Falha ao enviar notificação de take-over: {result.get('error')}")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"❌ Erro ao enviar notificação de take-over via WhatsApp: {e}", exc_info=True)

        return TakeOverResponse(
            success=True,
            message="Conversa assumida com sucesso! Você agora pode responder o lead.",
            lead_id=lead.id,
            attended_by=lead.attended_by,
            took_over_at=lead.seller_took_over_at
        )


@router.post("/leads/{lead_id}/send-message")
async def send_message_as_seller(
    lead_id: int,
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Envia mensagem para o lead via WhatsApp da empresa.

    Fluxo:
    1. Verifica se corretor assumiu a conversa (attended_by == "seller")
    2. Salva mensagem no banco com sender_type="seller" e sender_user_id
    3. Envia via WhatsApp usando número da empresa
    4. IA não responde mais automaticamente
    """

    seller = await get_seller_from_user(current_user)

    async with async_session() as session:
        # Busca lead
        lead_result = await session.execute(
            select(Lead)
            .where(Lead.id == lead_id)
            .where(Lead.tenant_id == current_user.tenant_id)
        )
        lead = lead_result.scalar_one_or_none()

        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead não encontrado"
            )

        # Verifica se está atribuído
        if lead.assigned_seller_id != seller.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Este lead não está atribuído a você"
            )

        # Verifica se corretor assumiu a conversa
        if lead.attended_by != "seller":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Você precisa assumir a conversa antes de enviar mensagens. Clique em 'Assumir Conversa'."
            )

        # Salva mensagem no banco
        message = Message(
            lead_id=lead.id,
            role="assistant",  # Mensagem saindo do sistema
            content=request.content,
            sender_type="seller",
            sender_user_id=current_user.id,
            created_at=datetime.now(timezone.utc)
        )
        session.add(message)

        # Atualiza last_message_at do lead
        lead.last_message_at = datetime.now(timezone.utc)

        await session.commit()
        await session.refresh(message)

        # Envia via WhatsApp (usando número da empresa)
        import logging
        logger = logging.getLogger(__name__)

        try:
            logger.info(f"📤 Enviando mensagem via WhatsApp para {lead.phone}")
            result = await send_whatsapp_message(
                to=lead.phone,
                message=request.content
            )

            if result.get("success"):
                logger.info(f"✅ Mensagem enviada com sucesso via WhatsApp")
            else:
                logger.error(f"❌ Falha ao enviar WhatsApp: {result.get('error')}")
        except Exception as e:
            # Não falha a requisição se WhatsApp falhar
            # A mensagem já foi salva no banco
            logger.error(f"❌ Erro ao enviar WhatsApp para {lead.phone}: {e}", exc_info=True)
            logger.error(f"❌ Tenant ID: {current_user.tenant_id}, Lead ID: {lead.id}")

        return {
            "success": True,
            "message": "Mensagem enviada com sucesso",
            "message_id": message.id,
            "sent_at": message.created_at
        }


@router.post("/leads/{lead_id}/return-to-ai")
async def return_to_ai(
    lead_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Devolve lead para a IA.

    Útil quando:
    - Corretor não conseguiu contato
    - Lead pediu para voltar depois
    - Corretor quer que IA continue nutrindo
    """

    seller = await get_seller_from_user(current_user)

    async with async_session() as session:
        # Busca lead
        lead_result = await session.execute(
            select(Lead)
            .where(Lead.id == lead_id)
            .where(Lead.tenant_id == current_user.tenant_id)
        )
        lead = lead_result.scalar_one_or_none()

        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead não encontrado"
            )

        # Verifica se está atribuído
        if lead.assigned_seller_id != seller.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Este lead não está atribuído a você"
            )

        # Retorna para IA
        lead.attended_by = "ai"
        lead.status = LeadStatus.IN_PROGRESS

        # Mensagem de sistema
        system_message = Message(
            lead_id=lead.id,
            role="system",
            content=f"🤖 {current_user.name} devolveu o lead para a IA continuar o atendimento",
            sender_type="system",
            created_at=datetime.now(timezone.utc)
        )
        session.add(system_message)

        await session.commit()

        return {
            "success": True,
            "message": "Lead devolvido para a IA",
            "attended_by": lead.attended_by
        }


@router.post("/leads/{lead_id}/fetch-profile-picture")
async def fetch_lead_profile_picture(
    lead_id: int,
    current_user: User = Depends(get_current_user),
):
    """
    Busca e salva a foto de perfil do WhatsApp do lead.

    Endpoint chamado pelo frontend quando abre a conversa.
    Atualiza o campo profile_picture_url no banco de dados.
    """

    seller = await get_seller_from_user(current_user)

    async with async_session() as session:
        # Busca lead
        lead_result = await session.execute(
            select(Lead)
            .where(Lead.id == lead_id)
            .where(Lead.tenant_id == current_user.tenant_id)
        )
        lead = lead_result.scalar_one_or_none()

        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead não encontrado"
            )

        # Verifica se está atribuído
        if lead.assigned_seller_id != seller.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Este lead não está atribuído a você"
            )

        # Se já tem foto, retorna direto
        if lead.profile_picture_url:
            return {
                "success": True,
                "url": lead.profile_picture_url,
                "cached": True
            }

        # Busca foto via Z-API
        import logging
        logger = logging.getLogger(__name__)

        try:
            logger.info(f"📸 Buscando foto de perfil para {lead.phone}")
            result = await get_profile_picture(phone=lead.phone)

            if result.get("success"):
                profile_url = result.get("url")
                lead.profile_picture_url = profile_url
                await session.commit()

                logger.info(f"✅ Foto de perfil salva para lead {lead_id}")
                return {
                    "success": True,
                    "url": profile_url,
                    "cached": False
                }
            else:
                logger.warning(f"⚠️ Lead {lead_id} sem foto de perfil: {result.get('error')}")
                return {
                    "success": False,
                    "error": result.get("error", "Sem foto de perfil")
                }

        except Exception as e:
            logger.error(f"❌ Erro ao buscar foto de perfil: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


# ==========================================
# ADMIN: VINCULAR USER A SELLER
# ==========================================

@router.post("/admin/link-seller-user")
async def link_seller_to_user(
    seller_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    [ADMIN] Vincula um Seller a um User para permitir login.

    Usado para:
    1. Criar conta de login para um corretor existente
    2. Permitir que corretor acesse o CRM

    Requisitos:
    - User deve ter role "corretor"
    - Seller e User devem ser do mesmo tenant
    """

    # Verifica permissão
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem vincular corretores"
        )

    async with async_session() as session:
        # Busca seller
        seller_result = await session.execute(
            select(Seller)
            .where(Seller.id == seller_id)
            .where(Seller.tenant_id == current_user.tenant_id)
        )
        seller = seller_result.scalar_one_or_none()

        if not seller:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Corretor não encontrado"
            )

        # Busca user
        user_result = await session.execute(
            select(User)
            .where(User.id == user_id)
            .where(User.tenant_id == current_user.tenant_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )

        # Verifica role
        if user.role != UserRole.SELLER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Usuário deve ter role 'corretor', mas tem '{user.role}'"
            )

        # Vincula
        seller.user_id = user.id

        await session.commit()

        return {
            "success": True,
            "message": f"Corretor {seller.name} vinculado ao usuário {user.name}",
            "seller_id": seller.id,
            "user_id": user.id
        }


# ==========================================
# ✨ NOVOS ENDPOINTS - 13 FUNCIONALIDADES
# ==========================================

# ============================================
# 1. SSE - TEMPO REAL
# ============================================

@router.get("/leads/{lead_id}/stream")
async def stream_lead_events(
    lead_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Server-Sent Events para atualizações em tempo real.

    Eventos:
    - new_message: Nova mensagem recebida/enviada
    - message_status: Status de entrega atualizado
    - typing: Indicador de digitação
    - lead_updated: Dados do lead alterados
    - handoff: Transferência de atendimento
    """
    # Verifica se lead pertence ao tenant do usuário
    async with async_session() as session:
        result = await session.execute(
            select(Lead)
            .where(Lead.id == lead_id)
            .where(Lead.tenant_id == current_user.tenant_id)
        )
        lead = result.scalar_one_or_none()

        if not lead:
            raise HTTPException(status_code=404, detail="Lead não encontrado")

    # Retorna stream SSE
    return StreamingResponse(
        event_stream_generator(lead_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ============================================
# 2-6. TEMPLATES DE RESPOSTAS RÁPIDAS
# ============================================

@router.get("/templates", response_model=List[ResponseTemplateResponse])
async def list_templates(
    current_user: User = Depends(get_current_user),
    category: Optional[str] = None,
    search: Optional[str] = None
):
    """Lista templates do tenant."""
    async with async_session() as session:
        query = (
            select(ResponseTemplate)
            .where(ResponseTemplate.tenant_id == current_user.tenant_id)
            .where(ResponseTemplate.is_active == True)
            .order_by(ResponseTemplate.usage_count.desc())
        )

        if category:
            query = query.where(ResponseTemplate.category == category)

        if search:
            query = query.where(
                or_(
                    ResponseTemplate.name.ilike(f"%{search}%"),
                    ResponseTemplate.content.ilike(f"%{search}%")
                )
            )

        result = await session.execute(query)
        templates = result.scalars().all()

        return templates


@router.post("/templates", response_model=ResponseTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    request: CreateTemplateRequest,
    current_user: User = Depends(get_current_user)
):
    """Cria novo template."""
    # Valida sintaxe
    is_valid, error = template_service.validate_template(request.content)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)

    async with async_session() as session:
        template = ResponseTemplate(
            tenant_id=current_user.tenant_id,
            created_by_user_id=current_user.id,
            name=request.name,
            shortcut=request.shortcut,
            content=request.content,
            category=request.category,
            is_active=True,
            usage_count=0
        )

        session.add(template)
        await session.commit()
        await session.refresh(template)

        return template


@router.patch("/templates/{template_id}", response_model=ResponseTemplateResponse)
async def update_template(
    template_id: int,
    request: UpdateTemplateRequest,
    current_user: User = Depends(get_current_user)
):
    """Atualiza template existente."""
    async with async_session() as session:
        result = await session.execute(
            select(ResponseTemplate)
            .where(ResponseTemplate.id == template_id)
            .where(ResponseTemplate.tenant_id == current_user.tenant_id)
        )
        template = result.scalar_one_or_none()

        if not template:
            raise HTTPException(status_code=404, detail="Template não encontrado")

        # Atualiza campos
        if request.name is not None:
            template.name = request.name
        if request.shortcut is not None:
            template.shortcut = request.shortcut
        if request.content is not None:
            # Valida sintaxe
            is_valid, error = template_service.validate_template(request.content)
            if not is_valid:
                raise HTTPException(status_code=400, detail=error)
            template.content = request.content
        if request.category is not None:
            template.category = request.category
        if request.is_active is not None:
            template.is_active = request.is_active

        await session.commit()
        await session.refresh(template)

        return template


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_user)
):
    """Soft-delete de template (marca como inativo)."""
    async with async_session() as session:
        result = await session.execute(
            select(ResponseTemplate)
            .where(ResponseTemplate.id == template_id)
            .where(ResponseTemplate.tenant_id == current_user.tenant_id)
        )
        template = result.scalar_one_or_none()

        if not template:
            raise HTTPException(status_code=404, detail="Template não encontrado")

        template.is_active = False
        await session.commit()


@router.post("/templates/{template_id}/use")
async def use_template(
    template_id: int,
    lead_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Retorna template interpolado com dados do lead/seller.

    Incrementa contador de uso.
    """
    async with async_session() as session:
        # Busca template
        template_result = await session.execute(
            select(ResponseTemplate)
            .where(ResponseTemplate.id == template_id)
            .where(ResponseTemplate.tenant_id == current_user.tenant_id)
            .where(ResponseTemplate.is_active == True)
        )
        template = template_result.scalar_one_or_none()

        if not template:
            raise HTTPException(status_code=404, detail="Template não encontrado")

        # Busca lead
        lead_result = await session.execute(
            select(Lead)
            .where(Lead.id == lead_id)
            .where(Lead.tenant_id == current_user.tenant_id)
        )
        lead = lead_result.scalar_one_or_none()

        if not lead:
            raise HTTPException(status_code=404, detail="Lead não encontrado")

        # Busca seller (se houver)
        seller_data = None
        if lead.assigned_seller_id:
            seller_result = await session.execute(
                select(Seller)
                .where(Seller.id == lead.assigned_seller_id)
            )
            seller = seller_result.scalar_one_or_none()
            if seller:
                seller_data = {"name": seller.name, "phone": seller.phone or ""}

        # Busca tenant
        from src.domain.entities.models import Tenant
        tenant_result = await session.execute(
            select(Tenant).where(Tenant.id == current_user.tenant_id)
        )
        tenant = tenant_result.scalar_one_or_none()

        # Monta contexto
        context = template_service.build_context(
            lead_data={"name": lead.name or "Cliente", "phone": lead.phone or "", "city": lead.city or ""},
            seller_data=seller_data,
            tenant_data={"name": tenant.name} if tenant else None
        )

        # Interpola
        interpolated = template_service.interpolate(template.content, context)

        # Incrementa contador
        template.usage_count += 1
        await session.commit()

        return {
            "template_id": template_id,
            "content": interpolated
        }


# ============================================
# 7-9. ANOTAÇÕES INTERNAS (NOTES)
# ============================================

@router.get("/leads/{lead_id}/notes", response_model=List[LeadNoteResponse])
async def list_lead_notes(
    lead_id: int,
    current_user: User = Depends(get_current_user)
):
    """Lista anotações de um lead."""
    async with async_session() as session:
        # Verifica acesso ao lead
        lead_result = await session.execute(
            select(Lead)
            .where(Lead.id == lead_id)
            .where(Lead.tenant_id == current_user.tenant_id)
        )
        if not lead_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Lead não encontrado")

        # Busca notes
        result = await session.execute(
            select(LeadNote)
            .join(User, LeadNote.author_id == User.id)
            .where(LeadNote.lead_id == lead_id)
            .order_by(LeadNote.created_at.desc())
        )
        notes = result.scalars().all()

        # Enriquece com nome do autor
        response = []
        for note in notes:
            user_result = await session.execute(
                select(User).where(User.id == note.author_id)
            )
            author = user_result.scalar_one_or_none()

            response.append(LeadNoteResponse(
                id=note.id,
                lead_id=note.lead_id,
                author_id=note.author_id,
                author_name=author.name if author else "Desconhecido",
                content=note.content,
                created_at=note.created_at,
                updated_at=note.updated_at
            ))

        return response


@router.post("/leads/{lead_id}/notes", response_model=LeadNoteResponse, status_code=status.HTTP_201_CREATED)
async def create_lead_note(
    lead_id: int,
    request: CreateNoteRequest,
    current_user: User = Depends(get_current_user)
):
    """Cria anotação em um lead."""
    async with async_session() as session:
        # Verifica acesso
        lead_result = await session.execute(
            select(Lead)
            .where(Lead.id == lead_id)
            .where(Lead.tenant_id == current_user.tenant_id)
        )
        if not lead_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Lead não encontrado")

        # Cria nota
        note = LeadNote(
            lead_id=lead_id,
            author_id=current_user.id,
            content=request.content
        )

        session.add(note)
        await session.commit()
        await session.refresh(note)

        return LeadNoteResponse(
            id=note.id,
            lead_id=note.lead_id,
            author_id=note.author_id,
            author_name=current_user.name,
            content=note.content,
            created_at=note.created_at,
            updated_at=note.updated_at
        )


@router.delete("/leads/{lead_id}/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead_note(
    lead_id: int,
    note_id: int,
    current_user: User = Depends(get_current_user)
):
    """Exclui anotação (apenas o autor pode excluir)."""
    async with async_session() as session:
        result = await session.execute(
            select(LeadNote)
            .where(LeadNote.id == note_id)
            .where(LeadNote.lead_id == lead_id)
        )
        note = result.scalar_one_or_none()

        if not note:
            raise HTTPException(status_code=404, detail="Anotação não encontrada")

        # Apenas autor pode excluir
        if note.author_id != current_user.id:
            raise HTTPException(status_code=403, detail="Apenas o autor pode excluir esta anotação")

        await session.delete(note)
        await session.commit()


# ============================================
# 10-11. ANEXOS (ATTACHMENTS)
# ============================================

@router.post("/leads/{lead_id}/upload")
async def upload_attachment(
    lead_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Faz upload de anexo (imagem, documento, áudio, vídeo).

    Validações:
    - Tamanho máximo: 10MB
    - Tipos: image/*, application/pdf, audio/*, video/*
    """
    async with async_session() as session:
        # Verifica acesso
        lead_result = await session.execute(
            select(Lead)
            .where(Lead.id == lead_id)
            .where(Lead.tenant_id == current_user.tenant_id)
        )
        if not lead_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Lead não encontrado")

        # Validação de tamanho (máx 10MB)
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        file_content = await file.read()
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Arquivo muito grande. Máximo permitido: 10MB. Recebido: {len(file_content) / 1024 / 1024:.1f}MB"
            )

        # Validação de tipo MIME
        ALLOWED_TYPES = {"image/", "application/pdf", "audio/", "video/"}
        content_type = file.content_type or ""
        if not any(content_type.startswith(t) for t in ALLOWED_TYPES):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de arquivo não permitido: {content_type}"
            )

        # Upload via service
        try:
            attachment_data = await storage_service.upload_file(
                file_content=file_content,
                filename=file.filename,
                content_type=file.content_type
            )

            return {
                "success": True,
                "attachment": attachment_data
            }

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.get("/leads/{lead_id}/attachments")
async def list_lead_attachments(
    lead_id: int,
    current_user: User = Depends(get_current_user)
):
    """Lista todos os anexos enviados em conversas do lead."""
    async with async_session() as session:
        # Busca mensagens com anexos
        result = await session.execute(
            select(Message)
            .join(Lead, Message.lead_id == Lead.id)
            .where(Lead.id == lead_id)
            .where(Lead.tenant_id == current_user.tenant_id)
            .where(Message.attachments != None)
            .where(Message.attachments != [])
            .order_by(Message.created_at.desc())
        )
        messages = result.scalars().all()

        # Extrai anexos
        attachments = []
        for msg in messages:
            if msg.attachments:
                for att in msg.attachments:
                    attachments.append({
                        **att,
                        "message_id": msg.id,
                        "message_created_at": msg.created_at
                    })

        return {"attachments": attachments}


# ============================================
# 12-14. ARQUIVAMENTO (ARCHIVE)
# ============================================

@router.post("/leads/{lead_id}/archive")
async def archive_lead(
    lead_id: int,
    request: ArchiveLeadRequest,
    current_user: User = Depends(get_current_user)
):
    """Arquiva lead (soft-delete)."""
    async with async_session() as session:
        result = await session.execute(
            select(Lead)
            .where(Lead.id == lead_id)
            .where(Lead.tenant_id == current_user.tenant_id)
        )
        lead = result.scalar_one_or_none()

        if not lead:
            raise HTTPException(status_code=404, detail="Lead não encontrado")

        if lead.archived_at:
            raise HTTPException(status_code=400, detail="Lead já está arquivado")

        # Arquiva
        lead.archived_at = datetime.now(timezone.utc)
        lead.archived_by = current_user.id
        lead.archive_reason = request.reason

        await session.commit()

        # Broadcast atualização
        await broadcast_lead_updated(lead_id, {"archived": True})

        return {
            "success": True,
            "message": "Lead arquivado com sucesso",
            "archived_at": lead.archived_at
        }


@router.post("/leads/{lead_id}/unarchive")
async def unarchive_lead(
    lead_id: int,
    current_user: User = Depends(get_current_user)
):
    """Desarquiva lead."""
    async with async_session() as session:
        result = await session.execute(
            select(Lead)
            .where(Lead.id == lead_id)
            .where(Lead.tenant_id == current_user.tenant_id)
        )
        lead = result.scalar_one_or_none()

        if not lead:
            raise HTTPException(status_code=404, detail="Lead não encontrado")

        if not lead.archived_at:
            raise HTTPException(status_code=400, detail="Lead não está arquivado")

        # Desarquiva
        lead.archived_at = None
        lead.archived_by = None
        lead.archive_reason = None

        await session.commit()

        # Broadcast
        await broadcast_lead_updated(lead_id, {"archived": False})

        return {
            "success": True,
            "message": "Lead desarquivado com sucesso"
        }


@router.get("/archived")
async def list_archived_leads(
    current_user: User = Depends(get_current_user)
):
    """Lista leads arquivados."""
    seller = await get_seller_from_user(current_user)

    async with async_session() as session:
        result = await session.execute(
            select(Lead)
            .where(Lead.assigned_seller_id == seller.id)
            .where(Lead.tenant_id == current_user.tenant_id)
            .where(Lead.archived_at != None)
            .order_by(Lead.archived_at.desc())
        )
        leads = result.scalars().all()

        return {
            "archived_leads": [
                {
                    "id": lead.id,
                    "name": lead.name,
                    "phone": lead.phone,
                    "archived_at": lead.archived_at,
                    "archive_reason": lead.archive_reason
                }
                for lead in leads
            ]
        }


# ============================================
# 15. MÉTRICAS DE PERFORMANCE / SLA
# ============================================

@router.get("/metrics", response_model=MetricsResponse)
async def get_seller_metrics(
    current_user: User = Depends(get_current_user),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
):
    """
    Retorna métricas de performance do vendedor.

    Métricas:
    - Total de leads
    - Conversas ativas
    - Tempo médio de primeira resposta
    - Total de mensagens enviadas/recebidas
    - Taxa de conversão
    - SLA compliance (% respondidos em < 5min)
    """
    seller = await get_seller_from_user(current_user)

    async with async_session() as session:
        # Total de leads
        total_leads_result = await session.execute(
            select(func.count(Lead.id))
            .where(Lead.assigned_seller_id == seller.id)
            .where(Lead.tenant_id == current_user.tenant_id)
        )
        total_leads = total_leads_result.scalar() or 0

        # Conversas ativas (não arquivadas)
        active_result = await session.execute(
            select(func.count(Lead.id))
            .where(Lead.assigned_seller_id == seller.id)
            .where(Lead.tenant_id == current_user.tenant_id)
            .where(Lead.archived_at == None)
        )
        active_conversations = active_result.scalar() or 0

        # Tempo médio de primeira resposta
        avg_response_result = await session.execute(
            select(func.avg(Lead.first_response_time_seconds))
            .where(Lead.assigned_seller_id == seller.id)
            .where(Lead.tenant_id == current_user.tenant_id)
            .where(Lead.first_response_time_seconds > 0)
        )
        avg_first_response = avg_response_result.scalar()

        # Total de mensagens
        messages_sent_result = await session.execute(
            select(func.sum(Lead.total_seller_messages))
            .where(Lead.assigned_seller_id == seller.id)
            .where(Lead.tenant_id == current_user.tenant_id)
        )
        total_messages_sent = messages_sent_result.scalar() or 0

        messages_received_result = await session.execute(
            select(func.sum(Lead.total_lead_messages))
            .where(Lead.assigned_seller_id == seller.id)
            .where(Lead.tenant_id == current_user.tenant_id)
        )
        total_messages_received = messages_received_result.scalar() or 0

        # SLA compliance (< 5min = 300s)
        sla_total_result = await session.execute(
            select(func.count(Lead.id))
            .where(Lead.assigned_seller_id == seller.id)
            .where(Lead.first_response_time_seconds > 0)
        )
        sla_total = sla_total_result.scalar() or 0

        sla_compliant_result = await session.execute(
            select(func.count(Lead.id))
            .where(Lead.assigned_seller_id == seller.id)
            .where(Lead.first_response_time_seconds > 0)
            .where(Lead.first_response_time_seconds <= 300)
        )
        sla_compliant = sla_compliant_result.scalar() or 0

        sla_compliance = (sla_compliant / sla_total * 100) if sla_total > 0 else None

        # Taxa de conversão (qualified / total)
        qualified_result = await session.execute(
            select(func.count(Lead.id))
            .where(Lead.assigned_seller_id == seller.id)
            .where(Lead.tenant_id == current_user.tenant_id)
            .where(Lead.status.in_(["converted", "won"]))
        )
        qualified = qualified_result.scalar() or 0
        conversion_rate = (qualified / total_leads * 100) if total_leads > 0 else None

        return MetricsResponse(
            total_leads=total_leads,
            active_conversations=active_conversations,
            avg_first_response_time_seconds=avg_first_response,
            total_messages_sent=total_messages_sent,
            total_messages_received=total_messages_received,
            conversion_rate=conversion_rate,
            sla_compliance=sla_compliance
        )


# ============================================
# 16. BUSCA DE MENSAGENS
# ============================================

@router.get("/search")
async def search_messages(
    q: str,
    current_user: User = Depends(get_current_user),
    limit: int = 50
):
    """
    Busca full-text em mensagens do vendedor.

    Retorna mensagens + dados do lead.
    """
    seller = await get_seller_from_user(current_user)

    async with async_session() as session:
        # Busca mensagens
        result = await session.execute(
            select(Message, Lead)
            .join(Lead, Message.lead_id == Lead.id)
            .where(Lead.assigned_seller_id == seller.id)
            .where(Lead.tenant_id == current_user.tenant_id)
            .where(Message.content.ilike(f"%{q}%"))
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        rows = result.all()

        return {
            "results": [
                {
                    "message_id": msg.id,
                    "content": msg.content,
                    "role": msg.role,
                    "created_at": msg.created_at,
                    "lead": {
                        "id": lead.id,
                        "name": lead.name,
                        "phone": lead.phone
                    }
                }
                for msg, lead in rows
            ]
        }


# ============================================
# 17. WEBHOOK - STATUS DE MENSAGENS
# ============================================

@router.post("/webhook/message-status")
async def webhook_message_status(
    webhook_data: Dict[str, Any],
    request: Request,
):
    """
    Webhook do Z-API para atualizar status de mensagens.

    Eventos:
    - MESSAGE_DELIVERED
    - MESSAGE_READ
    - MESSAGE_FAILED
    """
    # Validação básica: verificar token se configurado
    from src.config import get_settings
    _settings = get_settings()
    if _settings.webhook_verify_token:
        token = None
        # Tenta extrair token do header ou query param
        auth_header = request.headers.get("X-Webhook-Token") or request.query_params.get("verify_token")
        if auth_header != _settings.webhook_verify_token:
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Invalid webhook token")

    success = await message_status_service.process_status_webhook(
        db=async_session(),
        webhook_data=webhook_data
    )

    if success:
        return {"status": "processed"}
    else:
        return {"status": "ignored"}


# ============================================
# 18. VARIÁVEIS DISPONÍVEIS PARA TEMPLATES
# ============================================

@router.get("/templates/variables")
async def list_template_variables(
    current_user: User = Depends(get_current_user)
):
    """Lista variáveis disponíveis para usar em templates."""
    return {
        "variables": template_service.get_available_variables()
    }
