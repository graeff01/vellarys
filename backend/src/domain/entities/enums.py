"""Enums - valores fixos que se repetem no sistema."""

from enum import Enum


class LeadStatus(str, Enum):
    """Status do lead no funil."""
    NEW = "novo"                    # Acabou de chegar
    IN_PROGRESS = "em_atendimento"  # Em atendimento pela IA
    QUALIFIED = "qualificado"       # Qualificado (dados coletados)
    HANDED_OFF = "transferido"      # Transferido para humano
    CONVERTED = "convertido"        # Virou cliente
    LOST = "perdido"                # Perdido/desistiu


class LeadQualification(str, Enum):
    """Nível de qualificação do lead."""
    HOT = "quente"
    WARM = "morno"
    COLD = "frio"
    NEW = "novo"


class ChannelType(str, Enum):
    """Tipos de canal de comunicação."""
    WHATSAPP = "whatsapp"
    WEB = "web"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    EMAIL = "email"


class LeadSource(str, Enum):
    """Origem do lead."""
    ORGANIC = "organico"
    PAID = "pago"
    REFERRAL = "indicacao"
    SOCIAL = "social"
    OTHER = "outro"


class UserRole(str, Enum):
    """Nível de acesso do usuário."""
    SUPERADMIN = "superadmin"  # Equipe Velaris - acesso total
    ADMIN = "admin"            # Admin do tenant/cliente
    MANAGER = "gestor"         # Gestor do tenant
    USER = "usuario"           # Usuário comum


class EventType(str, Enum):
    """Tipos de evento no histórico do lead."""
    STATUS_CHANGE = "mudanca_status"
    QUALIFICATION_CHANGE = "mudanca_qualificacao"
    ASSIGNED = "atribuido"
    NOTE = "nota"
    TAG_ADDED = "tag_adicionada"
    TAG_REMOVED = "tag_removida"