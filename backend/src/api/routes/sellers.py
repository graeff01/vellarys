"""
ROTAS: VENDEDORES (SELLERS)
============================

CRUD completo para gerenciar a equipe de vendas.
Apenas gestores (admins) podem gerenciar vendedores.
"""

from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.domain.entities import Seller, Lead, User, Tenant
from src.api.dependencies import get_current_user, get_current_tenant


router = APIRouter(prefix="/sellers", tags=["Vendedores"])


# ==========================================
# SCHEMAS (Pydantic)
# ==========================================

class SellerCreate(BaseModel):
    """Schema para criar vendedor."""
    name: str = Field(..., min_length=2, max_length=200)
    whatsapp: str = Field(..., min_length=10, max_length=20)
    email: Optional[str] = None
    cities: List[str] = Field(default_factory=list)
    specialties: List[str] = Field(default_factory=list)
    max_leads_per_day: int = Field(default=0, ge=0)
    priority: int = Field(default=5, ge=1, le=10)
    notification_channels: List[str] = Field(default_factory=lambda: ["whatsapp"])


class SellerUpdate(BaseModel):
    """Schema para atualizar vendedor."""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    whatsapp: Optional[str] = Field(None, min_length=10, max_length=20)
    email: Optional[str] = None
    cities: Optional[List[str]] = None
    specialties: Optional[List[str]] = None
    max_leads_per_day: Optional[int] = Field(None, ge=0)
    priority: Optional[int] = Field(None, ge=1, le=10)
    active: Optional[bool] = None
    available: Optional[bool] = None
    on_vacation: Optional[bool] = None
    vacation_until: Optional[date] = None
    working_hours: Optional[dict] = None
    notification_channels: Optional[List[str]] = None


class SellerResponse(BaseModel):
    """Schema de resposta do vendedor."""
    id: int
    name: str
    whatsapp: str
    email: Optional[str]
    cities: List[str]
    specialties: List[str]
    active: bool
    available: bool
    max_leads_per_day: int
    leads_today: int
    total_leads: int
    converted_leads: int
    conversion_rate: float
    priority: int
    on_vacation: bool
    vacation_until: Optional[date]
    notification_channels: List[str]
    created_at: str

    class Config:
        from_attributes = True


# ==========================================
# ENDPOINTS
# ==========================================

@router.get("/config/specialties")
async def get_specialties_config(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """
    Retorna especialidades disponíveis baseadas no nicho do tenant.
    """
    settings = tenant.settings or {}
    niche = settings.get("niche", "services")
    
    # Especialidades por nicho
    specialties_by_niche = {
        "real_estate": [
            {"value": "venda", "label": "Venda"},
            {"value": "aluguel", "label": "Aluguel"},
            {"value": "lancamento", "label": "Lançamento"},
            {"value": "comercial", "label": "Comercial"},
            {"value": "residencial", "label": "Residencial"},
            {"value": "terreno", "label": "Terreno"},
        ],
        "healthcare": [
            {"value": "consulta", "label": "Consulta"},
            {"value": "exame", "label": "Exame"},
            {"value": "procedimento", "label": "Procedimento"},
            {"value": "retorno", "label": "Retorno"},
            {"value": "urgencia", "label": "Urgência"},
        ],
        "fitness": [
            {"value": "musculacao", "label": "Musculação"},
            {"value": "funcional", "label": "Funcional"},
            {"value": "natacao", "label": "Natação"},
            {"value": "personal", "label": "Personal"},
            {"value": "pilates", "label": "Pilates"},
            {"value": "luta", "label": "Artes Marciais"},
        ],
        "education": [
            {"value": "presencial", "label": "Presencial"},
            {"value": "online", "label": "Online"},
            {"value": "intensivo", "label": "Intensivo"},
            {"value": "regular", "label": "Regular"},
            {"value": "particular", "label": "Aula Particular"},
        ],
        "services": [
            {"value": "residencial", "label": "Residencial"},
            {"value": "comercial", "label": "Comercial"},
            {"value": "urgente", "label": "Urgente"},
            {"value": "orcamento", "label": "Orçamento"},
            {"value": "manutencao", "label": "Manutenção"},
            {"value": "instalacao", "label": "Instalação"},
        ],
    }
    
    # Pega especialidades do nicho ou usa services como fallback
    specialties = specialties_by_niche.get(niche, specialties_by_niche["services"])
    
    # Adiciona especialidades customizadas do tenant (se existirem)
    custom_specialties = settings.get("custom_seller_specialties", [])
    for custom in custom_specialties:
        if custom not in [s["value"] for s in specialties]:
            specialties.append({"value": custom, "label": custom.title()})
    
    return {
        "niche": niche,
        "specialties": specialties,
        "allow_custom": True,
    }


@router.get("/stats/summary")
async def sellers_stats(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna estatísticas gerais dos vendedores.
    """
    # Total de vendedores
    total_result = await db.execute(
        select(func.count(Seller.id))
        .where(Seller.tenant_id == tenant.id)
    )
    total = total_result.scalar() or 0
    
    # Vendedores ativos
    active_result = await db.execute(
        select(func.count(Seller.id))
        .where(Seller.tenant_id == tenant.id)
        .where(Seller.active == True)
    )
    active = active_result.scalar() or 0
    
    # Vendedores disponíveis
    available_result = await db.execute(
        select(func.count(Seller.id))
        .where(Seller.tenant_id == tenant.id)
        .where(Seller.active == True)
        .where(Seller.available == True)
        .where(Seller.on_vacation == False)
    )
    available = available_result.scalar() or 0
    
    # Total de leads atribuídos
    leads_result = await db.execute(
        select(func.sum(Seller.total_leads))
        .where(Seller.tenant_id == tenant.id)
    )
    total_leads = leads_result.scalar() or 0
    
    # Total de conversões
    conversions_result = await db.execute(
        select(func.sum(Seller.converted_leads))
        .where(Seller.tenant_id == tenant.id)
    )
    total_conversions = conversions_result.scalar() or 0
    
    return {
        "total_sellers": total,
        "active_sellers": active,
        "available_sellers": available,
        "total_leads_distributed": total_leads,
        "total_conversions": total_conversions,
        "avg_conversion_rate": round((total_conversions / total_leads * 100), 1) if total_leads > 0 else 0,
    }


@router.get("")
async def list_sellers(
    active_only: bool = Query(False, description="Filtrar apenas ativos"),
    available_only: bool = Query(False, description="Filtrar apenas disponíveis"),
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista todos os vendedores do tenant.
    """
    query = select(Seller).where(Seller.tenant_id == tenant.id)
    
    if active_only:
        query = query.where(Seller.active == True)
    
    if available_only:
        query = query.where(Seller.available == True)
        query = query.where(Seller.on_vacation == False)
    
    query = query.order_by(Seller.name)
    
    result = await db.execute(query)
    sellers = result.scalars().all()
    
    return {
        "sellers": [
            {
                "id": s.id,
                "name": s.name,
                "whatsapp": s.whatsapp,
                "email": s.email,
                "cities": s.cities or [],
                "specialties": s.specialties or [],
                "active": s.active,
                "available": s.available,
                "max_leads_per_day": s.max_leads_per_day,
                "leads_today": s.leads_today if s.leads_today_date == date.today() else 0,
                "total_leads": s.total_leads,
                "converted_leads": s.converted_leads,
                "conversion_rate": s.conversion_rate,
                "priority": s.priority,
                "on_vacation": s.on_vacation,
                "vacation_until": s.vacation_until.isoformat() if s.vacation_until else None,
                "notification_channels": s.notification_channels or ["whatsapp"],
                "last_lead_at": s.last_lead_at.isoformat() if s.last_lead_at else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in sellers
        ],
        "total": len(sellers),
    }


@router.post("")
async def create_seller(
    payload: SellerCreate,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Cria um novo vendedor.
    """
    # Verifica se já existe vendedor com esse WhatsApp no tenant
    result = await db.execute(
        select(Seller)
        .where(Seller.tenant_id == tenant.id)
        .where(Seller.whatsapp == payload.whatsapp)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Já existe um vendedor com esse WhatsApp"
        )
    
    seller = Seller(
        tenant_id=tenant.id,
        name=payload.name,
        whatsapp=payload.whatsapp,
        email=payload.email,
        cities=payload.cities,
        specialties=payload.specialties,
        max_leads_per_day=payload.max_leads_per_day,
        priority=payload.priority,
        notification_channels=payload.notification_channels,
    )
    
    db.add(seller)
    await db.commit()
    await db.refresh(seller)
    
    return {
        "success": True,
        "message": "Vendedor criado com sucesso",
        "seller": {
            "id": seller.id,
            "name": seller.name,
            "whatsapp": seller.whatsapp,
        }
    }


@router.get("/{seller_id}")
async def get_seller(
    seller_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna detalhes de um vendedor.
    """
    result = await db.execute(
        select(Seller)
        .where(Seller.id == seller_id)
        .where(Seller.tenant_id == tenant.id)
    )
    seller = result.scalar_one_or_none()
    
    if not seller:
        raise HTTPException(status_code=404, detail="Vendedor não encontrado")
    
    # Busca leads atribuídos
    leads_result = await db.execute(
        select(func.count(Lead.id))
        .where(Lead.assigned_seller_id == seller_id)
    )
    assigned_leads = leads_result.scalar() or 0
    
    return {
        "id": seller.id,
        "name": seller.name,
        "whatsapp": seller.whatsapp,
        "email": seller.email,
        "cities": seller.cities or [],
        "specialties": seller.specialties or [],
        "active": seller.active,
        "available": seller.available,
        "max_leads_per_day": seller.max_leads_per_day,
        "leads_today": seller.leads_today if seller.leads_today_date == date.today() else 0,
        "total_leads": seller.total_leads,
        "converted_leads": seller.converted_leads,
        "conversion_rate": seller.conversion_rate,
        "priority": seller.priority,
        "on_vacation": seller.on_vacation,
        "vacation_until": seller.vacation_until.isoformat() if seller.vacation_until else None,
        "working_hours": seller.working_hours,
        "notification_channels": seller.notification_channels or ["whatsapp"],
        "last_lead_at": seller.last_lead_at.isoformat() if seller.last_lead_at else None,
        "avg_response_time": seller.avg_response_time,
        "assigned_leads": assigned_leads,
        "created_at": seller.created_at.isoformat() if seller.created_at else None,
    }


@router.patch("/{seller_id}")
async def update_seller(
    seller_id: int,
    payload: SellerUpdate,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Atualiza um vendedor.
    """
    result = await db.execute(
        select(Seller)
        .where(Seller.id == seller_id)
        .where(Seller.tenant_id == tenant.id)
    )
    seller = result.scalar_one_or_none()
    
    if not seller:
        raise HTTPException(status_code=404, detail="Vendedor não encontrado")
    
    # Atualiza apenas campos enviados
    update_data = payload.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(seller, field, value)
    
    await db.commit()
    await db.refresh(seller)
    
    return {
        "success": True,
        "message": "Vendedor atualizado com sucesso",
        "seller": {
            "id": seller.id,
            "name": seller.name,
            "active": seller.active,
        }
    }


@router.delete("/{seller_id}")
async def delete_seller(
    seller_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove um vendedor.
    
    Os leads atribuídos a ele ficam sem atribuição.
    """
    result = await db.execute(
        select(Seller)
        .where(Seller.id == seller_id)
        .where(Seller.tenant_id == tenant.id)
    )
    seller = result.scalar_one_or_none()
    
    if not seller:
        raise HTTPException(status_code=404, detail="Vendedor não encontrado")
    
    # Remove atribuições dos leads
    await db.execute(
        Lead.__table__.update()
        .where(Lead.assigned_seller_id == seller_id)
        .values(assigned_seller_id=None, assigned_at=None, assignment_method=None)
    )
    
    await db.delete(seller)
    await db.commit()
    
    return {
        "success": True,
        "message": "Vendedor removido com sucesso"
    }


@router.post("/{seller_id}/toggle-availability")
async def toggle_availability(
    seller_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Alterna disponibilidade do vendedor.
    """
    result = await db.execute(
        select(Seller)
        .where(Seller.id == seller_id)
        .where(Seller.tenant_id == tenant.id)
    )
    seller = result.scalar_one_or_none()
    
    if not seller:
        raise HTTPException(status_code=404, detail="Vendedor não encontrado")
    
    seller.available = not seller.available
    await db.commit()
    
    return {
        "success": True,
        "available": seller.available,
        "message": f"Vendedor {'disponível' if seller.available else 'indisponível'}"
    }