"""Entidades do domínio."""
from .base import Base, TimestampMixin
from .enums import (
    LeadStatus,
    LeadQualification,
    ChannelType,
    LeadSource,
    UserRole,
    EventType,
)
from .models import (
    Tenant,
    User,
    Channel,
    Lead,
    Message,
    Tag,
    LeadEvent,
    lead_tags,
    Notification,
)
from .lead import Lead
from .seller import Seller
from .lead_assignment import LeadAssignment
from .niche import Niche
from .admin_log import AdminLog
from .login_log import LoginLog
from .plan import Plan
from .tenant_usage import TenantUsage
from .tenant_subscription import TenantSubscription
from .audit_log import AuditLog
from .empreendimento import Empreendimento
from .push_subscription import PushSubscription  # ← NOVO

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    # Enums
    "LeadStatus",
    "LeadQualification",
    "ChannelType",
    "LeadSource",
    "UserRole",
    "EventType",
    # Models
    "Tenant",
    "User",
    "Channel",
    "Lead",
    "Message",
    "Tag",
    "LeadEvent",
    "lead_tags",
    "Notification",
    "Seller",
    "LeadAssignment",
    # Admin
    "Niche",
    "AdminLog",
    "LoginLog",
    # Plans & Subscriptions
    "Plan",
    "TenantUsage",
    "TenantSubscription",
    # Audit
    "AuditLog",
    # Imobiliário
    "Empreendimento",
    # Push Notifications
    "PushSubscription",  # ← NOVO
]