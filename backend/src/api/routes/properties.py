"""
API Routes: Properties (Imóveis)
==================================

CRUD de imóveis + Match Automático com IA.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.domain.entities.property import Property, PropertyType
from src.domain.entities.models import Tenant, User
from src.infrastructure.database import get_db
from src.api.dependencies import get_current_user, get_current_tenant


router = APIRouter(prefix="/properties", tags=["properties"])


# =============================================================================
# SCHEMAS
# =============================================================================

class PropertyCreate(BaseModel):
    """Criar imóvel."""
    title: str = Field(..., min_length=5, max_length=200)
    description: Optional[str] = None
    property_type: str
    address: str
    neighborhood: Optional[str] = None
    city: str
    state: str = Field(..., min_length=2, max_length=2)
    zip_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    size_sqm: Optional[float] = None
    rooms: Optional[int] = None
    bathrooms: Optional[int] = None
    parking_spots: Optional[int] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    features: List[str] = Field(default_factory=list)
    sale_price: Optional[float] = None
    rent_price: Optional[float] = None
    condo_fee: Optional[float] = None
    iptu: Optional[float] = None
    images: List[str] = Field(default_factory=list)
    video_url: Optional[str] = None
    virtual_tour_url: Optional[str] = None
    is_active: bool = True
    is_available: bool = True


class PropertyUpdate(BaseModel):
    """Atualizar imóvel."""
    title: Optional[str] = None
    description: Optional[str] = None
    property_type: Optional[str] = None
    address: Optional[str] = None
    neighborhood: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    sale_price: Optional[float] = None
    rent_price: Optional[float] = None
    is_active: Optional[bool] = None
    is_available: Optional[bool] = None
    features: Optional[List[str]] = None
    images: Optional[List[str]] = None


class PropertyResponse(BaseModel):
    """Resposta de imóvel."""
    id: int
    title: str
    description: Optional[str]
    property_type: str
    address: str
    neighborhood: Optional[str]
    city: str
    state: str
    size_sqm: Optional[float]
    rooms: Optional[int]
    bathrooms: Optional[int]
    parking_spots: Optional[int]
    features: List[str]
    sale_price: Optional[float]
    rent_price: Optional[float]
    condo_fee: Optional[float]
    iptu: Optional[float]
    images: List[str]
    video_url: Optional[str]
    virtual_tour_url: Optional[str]
    is_active: bool
    is_available: bool

    class Config:
        from_attributes = True


class PropertyMatchCriteria(BaseModel):
    """Critérios de busca extraídos da mensagem."""
    property_type: Optional[str] = None
    min_rooms: Optional[int] = None
    max_rooms: Optional[int] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    neighborhoods: List[str] = Field(default_factory=list)
    cities: List[str] = Field(default_factory=list)
    required_features: List[str] = Field(default_factory=list)


# =============================================================================
# CRUD ENDPOINTS
# =============================================================================

@router.get("", response_model=List[PropertyResponse])
async def list_properties(
    property_type: Optional[str] = None,
    city: Optional[str] = None,
    neighborhood: Optional[str] = None,
    min_rooms: Optional[int] = None,
    max_rooms: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    is_available: bool = True,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Lista imóveis com filtros."""
    query = select(Property).where(
        Property.tenant_id == tenant.id,
        Property.is_active == True
    )

    if is_available:
        query = query.where(Property.is_available == True)

    if property_type:
        query = query.where(Property.property_type == property_type)

    if city:
        query = query.where(Property.city.ilike(f"%{city}%"))

    if neighborhood:
        query = query.where(Property.neighborhood.ilike(f"%{neighborhood}%"))

    if min_rooms:
        query = query.where(Property.rooms >= min_rooms)

    if max_rooms:
        query = query.where(Property.rooms <= max_rooms)

    if min_price:
        query = query.where(
            or_(
                Property.sale_price >= min_price,
                Property.rent_price >= min_price
            )
        )

    if max_price:
        query = query.where(
            or_(
                Property.sale_price <= max_price,
                Property.rent_price <= max_price
            )
        )

    query = query.order_by(Property.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{property_id}", response_model=PropertyResponse)
async def get_property(
    property_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Busca imóvel por ID."""
    prop = await db.get(Property, property_id)

    if not prop or prop.tenant_id != tenant.id:
        raise HTTPException(404, "Imóvel não encontrado")

    return prop


@router.post("", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
async def create_property(
    payload: PropertyCreate,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Cria novo imóvel."""
    prop = Property(
        tenant_id=tenant.id,
        created_by=user.id,
        **payload.model_dump()
    )

    db.add(prop)
    await db.commit()
    await db.refresh(prop)

    return prop


@router.patch("/{property_id}", response_model=PropertyResponse)
async def update_property(
    property_id: int,
    payload: PropertyUpdate,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Atualiza imóvel."""
    prop = await db.get(Property, property_id)

    if not prop or prop.tenant_id != tenant.id:
        raise HTTPException(404, "Imóvel não encontrado")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(prop, field, value)

    await db.commit()
    await db.refresh(prop)

    return prop


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: int,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Deleta imóvel."""
    prop = await db.get(Property, property_id)

    if not prop or prop.tenant_id != tenant.id:
        raise HTTPException(404, "Imóvel não encontrado")

    await db.delete(prop)
    await db.commit()

    return None


# =============================================================================
# MATCH AUTOMÁTICO COM IA
# =============================================================================

@router.post("/match", response_model=dict)
async def match_properties(
    message: str,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Match automático de imóveis baseado em mensagem do lead.

    Usa IA para extrair critérios da mensagem e buscar imóveis compatíveis.

    Exemplo:
    "Procuro casa 3 quartos zona norte até 500k"

    → Detecta:
      - tipo: casa
      - quartos: 3
      - região: zona norte
      - valor_max: 500000

    → Retorna imóveis que correspondem
    """
    from src.services.property_matcher import PropertyMatcherService

    matcher = PropertyMatcherService(db, tenant.id)
    matches = await matcher.find_matches(message)

    return {
        "message": message,
        "criteria": matches["criteria"],
        "properties": matches["properties"],
        "count": len(matches["properties"])
    }


@router.post("/extract-criteria", response_model=PropertyMatchCriteria)
async def extract_criteria(
    message: str,
    user: User = Depends(get_current_user),
):
    """
    Extrai critérios de busca de uma mensagem usando IA.

    Exemplo:
    "Quero apto 2 quartos perto do metrô até 350 mil"

    → Retorna:
      {
        "property_type": "apartamento",
        "min_rooms": 2,
        "max_rooms": 2,
        "max_price": 350000,
        "required_features": ["perto_metro"]
      }
    """
    from src.services.property_matcher import PropertyMatcherService

    criteria = await PropertyMatcherService.extract_criteria_from_message(message)
    return criteria
