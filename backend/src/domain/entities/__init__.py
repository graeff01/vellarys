"""Entidades do domínio."""
from .base import Base, TimestampMixin
from .enums import (
    LeadStatus,
    LeadQualification,
    ChannelType,
    LeadSource,
    UserRole,
    EventType,
    OpportunityStatus,
)

from .models import (
    Tenant,
    User,
    Channel,
    Lead,
    Message,
    LeadEvent,
    Notification,
    Tag,
)

from .seller import Seller
from .lead_assignment import LeadAssignment

from .niche import Niche
from .admin_log import AdminLog
from .login_log import LoginLog
from .plan import Plan
from .tenant_usage import TenantUsage
from .tenant_subscription import TenantSubscription
from .audit_log import AuditLog
from .product import Product
from .push_subscription import PushSubscription
from .refresh_token import RefreshToken
from .password_reset_token import PasswordResetToken
from .message_template import MessageTemplate
from .data_source import DataSource, DataSourceType
from .property_embedding import PropertyEmbedding
from .knowledge_embedding import KnowledgeEmbedding
from .dashboard_config import DashboardConfig, SalesGoal, WIDGET_TYPES, DEFAULT_DASHBOARD_WIDGETS
from .opportunity import Opportunity

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
    "OpportunityStatus",
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
    # Produtos
    "Product",
    # Push Notifications
    "PushSubscription",
    # Auth
    "RefreshToken",
    "PasswordResetToken",
    # Templates
    "MessageTemplate",
    # Data Sources
    "DataSource",
    "DataSourceType",
    # Embeddings
    "PropertyEmbedding",
    "KnowledgeEmbedding",
    # Dashboard
    "DashboardConfig",
    "SalesGoal",
    "WIDGET_TYPES",
    "DEFAULT_DASHBOARD_WIDGETS",
    # Opportunities
    "Opportunity",
]