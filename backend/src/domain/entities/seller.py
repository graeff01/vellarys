"""
MODELO: VENDEDOR (SELLER)
==========================

Representa um vendedor da equipe do tenant.
Recebe leads qualificados automaticamente.
"""

from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import String, Boolean, ForeignKey, Text, Integer, DateTime, Date
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Seller(Base, TimestampMixin):
    """
    Vendedor da equipe.
    
    O gestor cadastra seus vendedores aqui.
    O sistema distribui leads automaticamente para eles.
    """
    
    __tablename__ = "sellers"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    
    # ==========================================
    # DADOS BÁSICOS
    # ==========================================
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    whatsapp: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # ==========================================
    # SEGMENTAÇÃO (para distribuição)
    # ==========================================
    # Cidades que o vendedor atende (ex: ["São Paulo", "Guarulhos"])
    cities: Mapped[list] = mapped_column(ARRAY(String), default=list)
    
    # Especialidades (ex: ["venda", "aluguel"])
    specialties: Mapped[list] = mapped_column(ARRAY(String), default=list)
    
    # ==========================================
    # CONTROLE DE ATIVIDADE
    # ==========================================
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Limite de leads por dia (0 = sem limite)
    max_leads_per_day: Mapped[int] = mapped_column(Integer, default=0)
    
    # Contador de leads hoje (resetado diariamente)
    leads_today: Mapped[int] = mapped_column(Integer, default=0)
    leads_today_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Último lead recebido
    last_lead_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # ==========================================
    # MÉTRICAS (preenchidas automaticamente)
    # ==========================================
    total_leads: Mapped[int] = mapped_column(Integer, default=0)
    converted_leads: Mapped[int] = mapped_column(Integer, default=0)
    
    # Tempo médio de resposta em minutos (futuro)
    avg_response_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # ==========================================
    # DISPONIBILIDADE (para uso futuro)
    # ==========================================
    # Vendedor pode marcar como indisponível
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Horário de trabalho (ex: {"monday": {"start": "08:00", "end": "18:00"}, ...})
    working_hours: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Férias
    on_vacation: Mapped[bool] = mapped_column(Boolean, default=False)
    vacation_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # ==========================================
    # PRIORIDADE (para uso futuro)
    # ==========================================
    # 1-10, vendedores com maior prioridade recebem mais leads
    priority: Mapped[int] = mapped_column(Integer, default=5)
    
    # ==========================================
    # NOTIFICAÇÕES
    # ==========================================
    # Canais habilitados (ex: ["whatsapp", "email"])
    notification_channels: Mapped[list] = mapped_column(ARRAY(String), default=lambda: ["whatsapp"])
    
    # ==========================================
    # RELACIONAMENTOS
    # ==========================================
    tenant: Mapped["Tenant"] = relationship(back_populates="sellers")
    assignments: Mapped[List["LeadAssignment"]] = relationship(back_populates="seller", cascade="all, delete-orphan")
    products: Mapped[List["Product"]] = relationship(back_populates="seller")
    # ==========================================
    # MÉTODOS ÚTEIS
    # ==========================================
    @property
    def conversion_rate(self) -> float:
        """Taxa de conversão em porcentagem."""
        if self.total_leads == 0:
            return 0.0
        return round((self.converted_leads / self.total_leads) * 100, 1)
    
    def can_receive_lead(self, current_date: date = None) -> bool:
        """Verifica se o vendedor pode receber um novo lead."""
        if not self.active:
            return False
        
        if not self.available:
            return False
        
        if self.on_vacation:
            if self.vacation_until and current_date:
                if current_date <= self.vacation_until:
                    return False
            else:
                return False
        
        # Verifica limite diário
        if self.max_leads_per_day > 0:
            current = current_date or date.today()
            
            # Se é um novo dia, reseta o contador
            if self.leads_today_date != current:
                return True
            
            if self.leads_today >= self.max_leads_per_day:
                return False
        
        return True
    
    def increment_lead_count(self, current_date: date = None):
        """Incrementa o contador de leads."""
        current = current_date or date.today()
        
        # Se é um novo dia, reseta
        if self.leads_today_date != current:
            self.leads_today = 1
            self.leads_today_date = current
        else:
            self.leads_today += 1
        
        self.total_leads += 1
        self.last_lead_at = datetime.utcnow()