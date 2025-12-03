"""
MODELO: NICHE (Nicho de atendimento)
=====================================

Nichos configuráveis pelo painel admin.
Substitui o arquivo niches.py hardcoded.
"""

from typing import Optional, List
from sqlalchemy import String, Boolean, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class Niche(Base, TimestampMixin):
    """
    Nicho de atendimento configurável.
    
    Cada nicho define como a IA deve se comportar
    para aquele tipo de negócio.
    """
    
    __tablename__ = "niches"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Identificação
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Ex: "🏠", "🏥", "💪"
    
    # Configuração da IA
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Campos a coletar
    required_fields: Mapped[List[str]] = mapped_column(JSONB, default=list)
    optional_fields: Mapped[List[str]] = mapped_column(JSONB, default=list)
    
    # Regras de qualificação
    qualification_rules: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Formato: {"hot": ["palavras", "que", "indicam", "quente"], "warm": [...], "cold": [...]}
    
    # Personalização por contexto (novo!)
    context_rules: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Formato: {"tem_filhos": "Sugira opções family-friendly", "trabalha_centro": "..."}
    
    # Objeções e respostas
    objection_responses: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Formato: {"ta_caro": "Resposta para contornar...", "vou_pensar": "..."}
    
    # Status
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)  # Nicho padrão (services)