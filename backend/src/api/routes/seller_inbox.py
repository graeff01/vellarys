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

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from src.api.dependencies import get_current_user
from src.domain.entities import User, Seller, Lead, Message, LeadAssignment
from src.domain.entities.enums import UserRole, LeadStatus
from src.infrastructure.database import async_session
from src.infrastructure.services.whatsapp_service import WhatsAppService


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
            .join(LeadAssignment)
            .where(LeadAssignment.seller_id == seller.id)
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
                city=lead.metadata.get("city") if lead.metadata else None,
                interest=lead.metadata.get("interest") if lead.metadata else None,
                budget=lead.metadata.get("budget") if lead.metadata else None,
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
        # Verifica se o lead está atribuído ao corretor
        assignment_result = await session.execute(
            select(LeadAssignment)
            .where(LeadAssignment.lead_id == lead_id)
            .where(LeadAssignment.seller_id == seller.id)
        )
        assignment = assignment_result.scalar_one_or_none()

        if not assignment:
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
        assignment_result = await session.execute(
            select(LeadAssignment)
            .where(LeadAssignment.lead_id == lead_id)
            .where(LeadAssignment.seller_id == seller.id)
        )
        assignment = assignment_result.scalar_one_or_none()

        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Este lead não está atribuído a você"
            )

        # Marca como assumido pelo corretor
        lead.attended_by = "seller"
        lead.seller_took_over_at = datetime.utcnow()
        lead.status = LeadStatus.HANDED_OFF  # Atualiza status

        # Adiciona mensagem de sistema
        system_message = Message(
            lead_id=lead.id,
            role="system",
            content=f"🔄 {current_user.name} assumiu o atendimento",
            sender_type="system",
            created_at=datetime.utcnow()
        )
        session.add(system_message)

        await session.commit()
        await session.refresh(lead)

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
        assignment_result = await session.execute(
            select(LeadAssignment)
            .where(LeadAssignment.lead_id == lead_id)
            .where(LeadAssignment.seller_id == seller.id)
        )
        assignment = assignment_result.scalar_one_or_none()

        if not assignment:
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
            created_at=datetime.utcnow()
        )
        session.add(message)

        # Atualiza last_message_at do lead
        lead.last_message_at = datetime.utcnow()

        await session.commit()
        await session.refresh(message)

        # Envia via WhatsApp (usando número da empresa)
        try:
            whatsapp = WhatsAppService()
            await whatsapp.send_message(
                phone=lead.phone,
                message=request.content,
                tenant_id=current_user.tenant_id
            )
        except Exception as e:
            # Não falha a requisição se WhatsApp falhar
            # A mensagem já foi salva no banco
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"❌ Erro ao enviar WhatsApp: {e}")

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
        assignment_result = await session.execute(
            select(LeadAssignment)
            .where(LeadAssignment.lead_id == lead_id)
            .where(LeadAssignment.seller_id == seller.id)
        )
        assignment = assignment_result.scalar_one_or_none()

        if not assignment:
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
            created_at=datetime.utcnow()
        )
        session.add(system_message)

        await session.commit()

        return {
            "success": True,
            "message": "Lead devolvido para a IA",
            "attended_by": lead.attended_by
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
