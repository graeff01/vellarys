"""
ROTAS DE HANDOFF MANUAL
=======================

Endpoints para o gestor gerenciar a transferência manual de leads para vendedores.

Fluxo:
1. IA qualifica lead como QUENTE
2. Sistema notifica GESTOR (WhatsApp + Painel)
3. Gestor analisa e escolhe vendedor no painel
4. Sistema envia WhatsApp para o VENDEDOR com dados do lead
5. Lead fica com status "handed_off" + assigned_seller_id
6. Vendedor chama o cliente

Funciona para TODOS os nichos (imobiliário, saúde, fitness, educação, etc).
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.entities import (
    Lead, LeadEvent, Seller, Tenant, User, Notification
)
from src.domain.entities.enums import LeadStatus, EventType
from src.api.dependencies import (
    get_db,
    get_current_user,
    get_current_tenant,
)
from src.infrastructure.services import (
    execute_handoff,
    generate_lead_summary,
)
from src.infrastructure.services.notification_service import (
    notify_seller,
    notify_gestor,
    create_panel_notification,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/leads", tags=["Handoff Manual"])


# =============================================================================
# SCHEMAS
# =============================================================================

class AssignLeadRequest(BaseModel):
    """Request para atribuir lead a um vendedor."""
    seller_id: int = Field(..., description="ID do vendedor que vai receber o lead")
    notes: Optional[str] = Field(None, description="Observações do gestor", max_length=500)
    notify_seller: bool = Field(True, description="Se deve enviar WhatsApp para o vendedor")


class HandoffRequest(BaseModel):
    """Request para executar handoff de um lead."""
    reason: Optional[str] = Field(
        "manual_by_manager",
        description="Motivo do handoff",
        max_length=200
    )
    notes: Optional[str] = Field(None, description="Observações do gestor", max_length=500)
    notify_lead: bool = Field(
        True,
        description="Se deve enviar mensagem de transferência para o lead"
    )


class AssignAndHandoffRequest(BaseModel):
    """Request para atribuir e fazer handoff em uma única ação."""
    seller_id: int = Field(..., description="ID do vendedor que vai receber o lead")
    reason: Optional[str] = Field(
        "manual_by_manager",
        description="Motivo do handoff"
    )
    notes: Optional[str] = Field(None, description="Observações do gestor", max_length=500)
    notify_lead: bool = Field(
        True,
        description="Se deve enviar mensagem de transferência para o lead"
    )
    notify_seller: bool = Field(
        True,
        description="Se deve enviar WhatsApp para o vendedor"
    )


class LeadHandoffResponse(BaseModel):
    """Response após operação de handoff."""
    success: bool
    lead_id: int
    lead_name: Optional[str]
    lead_phone: Optional[str]
    status: str
    assigned_seller_id: Optional[int]
    assigned_seller_name: Optional[str]
    handed_off_at: Optional[datetime]
    message: str
    seller_notified: bool = False
    seller_notification_error: Optional[str] = None


class PendingHandoffLead(BaseModel):
    """Lead aguardando handoff."""
    id: int
    name: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    qualification: Optional[str]
    source: Optional[str]
    summary: Optional[str]
    empreendimento_nome: Optional[str]
    created_at: datetime
    last_message_at: Optional[datetime]
    message_count: int
    assigned_seller_id: Optional[int]
    assigned_seller_name: Optional[str]
    
    class Config:
        from_attributes = True


class HandoffHistoryItem(BaseModel):
    """Item do histórico de handoff."""
    id: int
    event_type: str
    old_value: Optional[str]
    new_value: Optional[str]
    description: Optional[str]
    created_at: datetime
    created_by_name: Optional[str]


# =============================================================================
# HELPERS
# =============================================================================

async def get_lead_with_validation(
    db: AsyncSession,
    lead_id: int,
    tenant: Tenant,
) -> Lead:
    """Busca lead validando que pertence ao tenant."""
    result = await db.execute(
        select(Lead)
        .where(Lead.id == lead_id)
        .where(Lead.tenant_id == tenant.id)
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead {lead_id} não encontrado"
        )
    
    return lead


async def get_seller_with_validation(
    db: AsyncSession,
    seller_id: int,
    tenant: Tenant,
) -> Seller:
    """Busca vendedor validando que pertence ao tenant e está ativo."""
    result = await db.execute(
        select(Seller)
        .where(Seller.id == seller_id)
        .where(Seller.tenant_id == tenant.id)
        .where(Seller.active == True)
    )
    seller = result.scalar_one_or_none()
    
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendedor {seller_id} não encontrado ou inativo"
        )
    
    return seller


def create_handoff_event(
    lead_id: int,
    event_type: str,
    old_value: str = None,
    new_value: str = None,
    description: str = None,
    user_id: int = None,
) -> LeadEvent:
    """Cria evento de handoff."""
    return LeadEvent(
        lead_id=lead_id,
        event_type=event_type,
        old_value=old_value,
        new_value=new_value,
        description=description,
    )


async def ensure_lead_summary(db: AsyncSession, lead: Lead) -> None:
    """Gera summary do lead se não existir."""
    if lead.summary:
        return
    
    try:
        from src.domain.entities import Message
        result = await db.execute(
            select(Message)
            .where(Message.lead_id == lead.id)
            .order_by(Message.created_at.desc())
            .limit(30)
        )
        messages = result.scalars().all()
        conversation = [{"role": m.role, "content": m.content} for m in reversed(messages)]
        
        if conversation:
            lead.summary = await generate_lead_summary(
                conversation=conversation,
                extracted_data=lead.custom_data or {},
                qualification={"qualification": lead.qualification},
            )
    except Exception as e:
        logger.error(f"Erro gerando summary: {e}")


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post(
    "/{lead_id}/assign",
    response_model=LeadHandoffResponse,
    summary="Atribuir lead a vendedor",
    description="""
    Atribui um lead a um vendedor específico SEM fazer handoff.
    
    Use quando:
    - Quer pré-atribuir o lead mas a IA ainda vai continuar atendendo
    - Quer trocar o vendedor atribuído
    
    O status do lead NÃO muda.
    Opcionalmente envia WhatsApp para o vendedor.
    """
)
async def assign_lead_to_seller(
    lead_id: int,
    request: AssignLeadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """Atribui lead a um vendedor sem fazer handoff."""
    
    # Validações
    lead = await get_lead_with_validation(db, lead_id, tenant)
    seller = await get_seller_with_validation(db, request.seller_id, tenant)
    
    # Guarda valor anterior
    old_seller_id = lead.assigned_seller_id
    old_seller_name = None
    if old_seller_id:
        result = await db.execute(select(Seller).where(Seller.id == old_seller_id))
        old_seller = result.scalar_one_or_none()
        old_seller_name = old_seller.name if old_seller else None
    
    # Atualiza lead
    lead.assigned_seller_id = seller.id
    lead.assignment_method = "manual"
    lead.assigned_at = datetime.now(timezone.utc)
    
    # Cria evento
    event = create_handoff_event(
        lead_id=lead.id,
        event_type="assignment",
        old_value=old_seller_name,
        new_value=seller.name,
        description=f"Atribuído manualmente por {current_user.name or current_user.email}. {request.notes or ''}".strip(),
    )
    db.add(event)
    
    # ⭐ NOTIFICA VENDEDOR VIA WHATSAPP
    seller_notified = False
    seller_notification_error = None
    
    if request.notify_seller:
        # Garante que tem summary
        await ensure_lead_summary(db, lead)
        
        notification_result = await notify_seller(
            db=db,
            tenant=tenant,
            lead=lead,
            seller=seller,
            assigned_by=current_user.name or current_user.email,
            notes=request.notes,
        )
        seller_notified = notification_result.get("whatsapp", False)
        seller_notification_error = notification_result.get("whatsapp_error")
    
    await db.commit()
    
    logger.info(f"Lead {lead_id} atribuído ao vendedor {seller.id} ({seller.name}) por {current_user.email}")
    
    return LeadHandoffResponse(
        success=True,
        lead_id=lead.id,
        lead_name=lead.name,
        lead_phone=lead.phone,
        status=lead.status,
        assigned_seller_id=seller.id,
        assigned_seller_name=seller.name,
        handed_off_at=None,
        message=f"Lead atribuído ao vendedor {seller.name}",
        seller_notified=seller_notified,
        seller_notification_error=seller_notification_error,
    )


@router.post(
    "/{lead_id}/handoff",
    response_model=LeadHandoffResponse,
    summary="Executar handoff do lead",
    description="""
    Executa o handoff de um lead (muda status para 'handed_off').
    
    Use quando:
    - O lead já está atribuído a um vendedor e você quer oficializar a transferência
    - Quer parar o atendimento da IA para este lead
    
    Se o lead não tiver vendedor atribuído, o handoff vai para o gestor padrão.
    """
)
async def execute_lead_handoff(
    lead_id: int,
    request: HandoffRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """Executa handoff de um lead."""
    
    # Validações
    lead = await get_lead_with_validation(db, lead_id, tenant)
    
    # Verifica se já está transferido
    if lead.status == LeadStatus.HANDED_OFF.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lead já está transferido"
        )
    
    # Guarda status anterior
    old_status = lead.status
    
    # Gera summary se não tiver
    await ensure_lead_summary(db, lead)
    
    # Executa handoff
    handoff_result = await execute_handoff(
        lead=lead,
        tenant=tenant,
        reason=request.reason or "manual_by_manager",
        db=db,
    )
    
    # Cria evento
    event = create_handoff_event(
        lead_id=lead.id,
        event_type=EventType.STATUS_CHANGE.value,
        old_value=old_status,
        new_value=LeadStatus.HANDED_OFF.value,
        description=f"Handoff manual por {current_user.name or current_user.email}. Motivo: {request.reason}. {request.notes or ''}".strip(),
    )
    db.add(event)
    
    # Busca nome do vendedor se tiver
    seller_name = None
    if lead.assigned_seller_id:
        result = await db.execute(select(Seller).where(Seller.id == lead.assigned_seller_id))
        seller = result.scalar_one_or_none()
        seller_name = seller.name if seller else None
    
    await db.commit()
    
    logger.info(f"Handoff executado para lead {lead_id} por {current_user.email}")
    
    return LeadHandoffResponse(
        success=True,
        lead_id=lead.id,
        lead_name=lead.name,
        lead_phone=lead.phone,
        status=lead.status,
        assigned_seller_id=lead.assigned_seller_id,
        assigned_seller_name=seller_name,
        handed_off_at=datetime.now(timezone.utc),
        message=handoff_result.get("message_for_lead", "Lead transferido com sucesso"),
    )


@router.post(
    "/{lead_id}/assign-and-handoff",
    response_model=LeadHandoffResponse,
    summary="Atribuir vendedor e fazer handoff",
    description="""
    Atribui o lead a um vendedor E executa o handoff em uma única operação.
    
    Este é o endpoint principal que o gestor deve usar quando:
    1. Recebe notificação de lead quente
    2. Analisa o lead
    3. Decide qual vendedor vai atender
    4. Marca no sistema
    
    O sistema automaticamente:
    - Atribui o lead ao vendedor
    - Muda status para 'handed_off' (IA para de atender)
    - Envia WhatsApp para o vendedor com dados do lead
    """
)
async def assign_and_handoff(
    lead_id: int,
    request: AssignAndHandoffRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """Atribui lead a vendedor e executa handoff."""
    
    # Validações
    lead = await get_lead_with_validation(db, lead_id, tenant)
    seller = await get_seller_with_validation(db, request.seller_id, tenant)
    
    # Verifica se já está transferido
    if lead.status == LeadStatus.HANDED_OFF.value:
        # Se já transferido, apenas atualiza o vendedor e notifica
        old_seller_id = lead.assigned_seller_id
        lead.assigned_seller_id = seller.id
        lead.assignment_method = "manual"
        
        event = create_handoff_event(
            lead_id=lead.id,
            event_type="reassignment",
            old_value=str(old_seller_id) if old_seller_id else None,
            new_value=str(seller.id),
            description=f"Reatribuído para {seller.name} por {current_user.name or current_user.email}",
        )
        db.add(event)
        
        # Notifica novo vendedor
        seller_notified = False
        seller_notification_error = None
        
        if request.notify_seller:
            await ensure_lead_summary(db, lead)
            
            notification_result = await notify_seller(
                db=db,
                tenant=tenant,
                lead=lead,
                seller=seller,
                assigned_by=current_user.name or current_user.email,
                notes=request.notes,
            )
            seller_notified = notification_result.get("whatsapp", False)
            seller_notification_error = notification_result.get("whatsapp_error")
        
        await db.commit()
        
        return LeadHandoffResponse(
            success=True,
            lead_id=lead.id,
            lead_name=lead.name,
            lead_phone=lead.phone,
            status=lead.status,
            assigned_seller_id=seller.id,
            assigned_seller_name=seller.name,
            handed_off_at=None,
            message=f"Lead reatribuído para {seller.name}",
            seller_notified=seller_notified,
            seller_notification_error=seller_notification_error,
        )
    
    # Guarda valores anteriores
    old_status = lead.status
    old_seller_id = lead.assigned_seller_id
    
    # 1. Atribui vendedor
    lead.assigned_seller_id = seller.id
    lead.assignment_method = "manual"
    lead.assigned_at = datetime.now(timezone.utc)
    
    # 2. Gera summary se não tiver
    await ensure_lead_summary(db, lead)
    
    # 3. Executa handoff
    handoff_result = await execute_handoff(
        lead=lead,
        tenant=tenant,
        reason=request.reason or "manual_by_manager",
        db=db,
    )
    
    # 4. Cria eventos
    # Evento de atribuição
    event_assign = create_handoff_event(
        lead_id=lead.id,
        event_type="assignment",
        old_value=str(old_seller_id) if old_seller_id else None,
        new_value=str(seller.id),
        description=f"Atribuído para {seller.name}",
    )
    db.add(event_assign)
    
    # Evento de handoff
    event_handoff = create_handoff_event(
        lead_id=lead.id,
        event_type=EventType.STATUS_CHANGE.value,
        old_value=old_status,
        new_value=LeadStatus.HANDED_OFF.value,
        description=f"Handoff manual por {current_user.name or current_user.email}. Vendedor: {seller.name}. {request.notes or ''}".strip(),
    )
    db.add(event_handoff)
    
    # 5. Cria notificação de conclusão no painel
    notification = Notification(
        tenant_id=tenant.id,
        type="handoff_completed",
        title="✅ Lead Transferido",
        message=f"{lead.name or 'Lead'} foi transferido para {seller.name}",
        reference_type="lead",
        reference_id=lead.id,
        read=False,
    )
    db.add(notification)
    
    # ⭐ 6. NOTIFICA VENDEDOR VIA WHATSAPP
    seller_notified = False
    seller_notification_error = None
    
    if request.notify_seller:
        notification_result = await notify_seller(
            db=db,
            tenant=tenant,
            lead=lead,
            seller=seller,
            assigned_by=current_user.name or current_user.email,
            notes=request.notes,
        )
        seller_notified = notification_result.get("whatsapp", False)
        seller_notification_error = notification_result.get("whatsapp_error")
        
        if seller_notified:
            logger.info(f"📲 WhatsApp enviado para vendedor {seller.name}")
        else:
            logger.warning(f"⚠️ Falha ao notificar vendedor: {seller_notification_error}")
    
    await db.commit()
    
    logger.info(f"Lead {lead_id} atribuído a {seller.name} e handoff executado por {current_user.email}")
    
    return LeadHandoffResponse(
        success=True,
        lead_id=lead.id,
        lead_name=lead.name,
        lead_phone=lead.phone,
        status=lead.status,
        assigned_seller_id=seller.id,
        assigned_seller_name=seller.name,
        handed_off_at=datetime.now(timezone.utc),
        message=f"Lead transferido para {seller.name}",
        seller_notified=seller_notified,
        seller_notification_error=seller_notification_error,
    )


@router.get(
    "/pending-handoff",
    response_model=List[PendingHandoffLead],
    summary="Listar leads aguardando handoff",
    description="""
    Lista todos os leads quentes que ainda não foram transferidos.
    
    Inclui:
    - Leads com qualification = 'quente' ou 'hot'
    - Leads com status != 'handed_off'
    
    Ordenados por qualificação (quentes primeiro) e data de criação.
    """
)
async def list_pending_handoff_leads(
    qualification: Optional[str] = Query(
        None,
        description="Filtrar por qualificação específica"
    ),
    has_seller: Optional[bool] = Query(
        None,
        description="Filtrar por leads que já têm/não têm vendedor atribuído"
    ),
    limit: int = Query(50, ge=1, le=200, description="Máximo de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """Lista leads quentes aguardando handoff."""
    
    # Query base
    query = (
        select(Lead)
        .where(Lead.tenant_id == tenant.id)
        .where(Lead.status != LeadStatus.HANDED_OFF.value)
        .where(
            or_(
                Lead.qualification == "quente",
                Lead.qualification == "hot",
                Lead.qualification == "morno",
            )
        )
    )
    
    # Filtros opcionais
    if qualification:
        query = query.where(Lead.qualification == qualification)
    
    if has_seller is not None:
        if has_seller:
            query = query.where(Lead.assigned_seller_id.isnot(None))
        else:
            query = query.where(Lead.assigned_seller_id.is_(None))
    
    # Ordenação: quentes primeiro, depois por data
    query = query.order_by(
        Lead.qualification.desc(),
        Lead.created_at.desc()
    )
    
    # Paginação
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    leads = result.scalars().all()
    
    # Monta resposta
    response = []
    for lead in leads:
        # Busca nome do vendedor se tiver
        seller_name = None
        if lead.assigned_seller_id:
            seller_result = await db.execute(
                select(Seller).where(Seller.id == lead.assigned_seller_id)
            )
            seller = seller_result.scalar_one_or_none()
            seller_name = seller.name if seller else None
        
        # Conta mensagens
        from src.domain.entities import Message
        msg_count_result = await db.execute(
            select(Message.id).where(Message.lead_id == lead.id)
        )
        message_count = len(msg_count_result.scalars().all())
        
        # Busca última mensagem
        last_msg_result = await db.execute(
            select(Message.created_at)
            .where(Message.lead_id == lead.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_message_at = last_msg_result.scalar_one_or_none()
        
        # Dados específicos do nicho (empreendimento para imobiliário, etc)
        empreendimento_nome = None
        if lead.custom_data:
            empreendimento_nome = lead.custom_data.get("empreendimento_nome")
        
        response.append(PendingHandoffLead(
            id=lead.id,
            name=lead.name,
            phone=lead.phone,
            email=lead.email,
            qualification=lead.qualification,
            source=lead.source,
            summary=lead.summary,
            empreendimento_nome=empreendimento_nome,
            created_at=lead.created_at,
            last_message_at=last_message_at,
            message_count=message_count,
            assigned_seller_id=lead.assigned_seller_id,
            assigned_seller_name=seller_name,
        ))
    
    return response


@router.get(
    "/{lead_id}/handoff-history",
    response_model=List[HandoffHistoryItem],
    summary="Histórico de handoffs do lead",
    description="Retorna o histórico de atribuições e transferências do lead."
)
async def get_lead_handoff_history(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """Busca histórico de handoffs de um lead."""
    
    # Valida lead
    lead = await get_lead_with_validation(db, lead_id, tenant)
    
    # Busca eventos relacionados a handoff/assignment
    result = await db.execute(
        select(LeadEvent)
        .where(LeadEvent.lead_id == lead.id)
        .where(
            or_(
                LeadEvent.event_type == EventType.STATUS_CHANGE.value,
                LeadEvent.event_type == "assignment",
                LeadEvent.event_type == "reassignment",
                LeadEvent.event_type == "handoff",
            )
        )
        .order_by(LeadEvent.created_at.desc())
    )
    events = result.scalars().all()
    
    response = []
    for event in events:
        response.append(HandoffHistoryItem(
            id=event.id,
            event_type=event.event_type,
            old_value=event.old_value,
            new_value=event.new_value,
            description=event.description,
            created_at=event.created_at,
            created_by_name=None,
        ))
    
    return response


@router.post(
    "/{lead_id}/reopen",
    response_model=LeadHandoffResponse,
    summary="Reabrir lead transferido",
    description="""
    Reabre um lead que foi transferido, voltando para atendimento da IA.
    
    Use quando:
    - O vendedor não conseguiu contato
    - O cliente voltou a mandar mensagem
    - Houve erro no handoff
    """
)
async def reopen_handed_off_lead(
    lead_id: int,
    reason: str = Query("reopen_by_manager", description="Motivo da reabertura"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """Reabre um lead que foi transferido."""
    
    lead = await get_lead_with_validation(db, lead_id, tenant)
    
    if lead.status != LeadStatus.HANDED_OFF.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lead não está transferido"
        )
    
    old_status = lead.status
    
    # Volta para in_progress
    lead.status = LeadStatus.IN_PROGRESS.value
    
    # Cria evento
    event = create_handoff_event(
        lead_id=lead.id,
        event_type=EventType.STATUS_CHANGE.value,
        old_value=old_status,
        new_value=LeadStatus.IN_PROGRESS.value,
        description=f"Reaberto por {current_user.name or current_user.email}. Motivo: {reason}",
    )
    db.add(event)
    
    # Notificação
    notification = Notification(
        tenant_id=tenant.id,
        type="lead_reopened",
        title="🔄 Lead Reaberto",
        message=f"{lead.name or 'Lead'} foi reaberto para atendimento",
        reference_type="lead",
        reference_id=lead.id,
        read=False,
    )
    db.add(notification)
    
    await db.commit()
    
    logger.info(f"Lead {lead_id} reaberto por {current_user.email}")
    
    # Busca nome do vendedor
    seller_name = None
    if lead.assigned_seller_id:
        result = await db.execute(select(Seller).where(Seller.id == lead.assigned_seller_id))
        seller = result.scalar_one_or_none()
        seller_name = seller.name if seller else None
    
    return LeadHandoffResponse(
        success=True,
        lead_id=lead.id,
        lead_name=lead.name,
        lead_phone=lead.phone,
        status=lead.status,
        assigned_seller_id=lead.assigned_seller_id,
        assigned_seller_name=seller_name,
        handed_off_at=None,
        message="Lead reaberto para atendimento"
    )