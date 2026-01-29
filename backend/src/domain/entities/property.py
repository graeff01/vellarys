"""
Property - Im\u00f3vel (Mercado Imobili\u00e1rio)
========================================

Cat\u00e1logo de im\u00f3veis dispon\u00edveis para venda/loca\u00e7\u00e3o.
Usado pelo Match Autom\u00e1tico de Im\u00f3veis para buscar op\u00e7\u00f5es
que correspondam aos crit\u00e9rios do lead.

Campos principais:
- Tipo (casa, apartamento, sobrado, terreno, sala_comercial)
- Localiza\u00e7\u00e3o (endere\u00e7o, bairro, cidade, coordenadas)
- Detalhes (m\u00b2, quartos, banheiros, vagas)
- Valores (venda, aluguel, condom\u00ednio, IPTU)
- M\u00eddia (fotos, v\u00eddeos, tour virtual)
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING, List, Dict, Any
from sqlalchemy import String, Integer, Boolean, ForeignKey, Text, Numeric, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.mutable import MutableList, MutableDict

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .models import Tenant, User


class PropertyType:
    """Tipos de im\u00f3vel."""
    HOUSE = "casa"
    APARTMENT = "apartamento"
    DUPLEX = "sobrado"
    LAND = "terreno"
    COMMERCIAL = "sala_comercial"
    WAREHOUSE = "galpao"
    FARM = "fazenda"
    COTTAGE = "chacara"


class Property(Base, TimestampMixin):
    """Im\u00f3vel dispon\u00edvel no cat\u00e1logo."""

    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    # Basic Info
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    property_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Location
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    neighborhood: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    zip_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 8), nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Numeric(11, 8), nullable=True)

    # Details
    size_sqm: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    rooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    bathrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    parking_spots: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    floor: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_floors: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Features (JSONB array)
    features: Mapped[List[str]] = mapped_column(
        MutableList.as_mutable(JSONB),
        default=list,
        nullable=True
    )

    # Values
    sale_price: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True, index=True)
    rent_price: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True, index=True)
    condo_fee: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    iptu: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)

    # Media
    images: Mapped[List[str]] = mapped_column(
        MutableList.as_mutable(JSONB),
        default=list,
        nullable=True
    )
    video_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    virtual_tour_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Custom data
    custom_data: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB),
        default=dict,
        nullable=True
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship()
    creator: Mapped[Optional["User"]] = relationship()

    # Composite indexes
    __table_args__ = (
        Index("ix_properties_tenant_active_available", "tenant_id", "is_active", "is_available"),
        Index("ix_properties_type_rooms_price", "property_type", "rooms", "sale_price"),
    )

    def __repr__(self) -> str:
        return f"<Property(id={self.id}, type='{self.property_type}', city='{self.city}', price={self.sale_price})>"
