"""
INFRASTRUCTURE SERVICES
========================

Serviços de infraestrutura do Velaris.

Organização:
- Core AI: OpenAI, Sentimento, Respostas
- Comunicação: WhatsApp (Z-API)
- Segurança: Auth, Rate Limit, Security, LGPD
- Negócio: Guards, Handoff, Distribution, Reengagement
- Operacional: Business Hours, Notifications, Export, Audit
"""

# =============================================================================
# CORE AI - OpenAI e Inteligência
# =============================================================================

from .openai_service import (
    chat_completion,
    extract_lead_data,
    qualify_lead,
    generate_lead_summary,
    generate_proactive_suggestions,
    detect_sentiment,
    generate_context_aware_response,
    generate_conversation_summary,
    calculate_typing_delay,
    get_random_greeting,
    get_random_acknowledgment,
)

# =============================================================================
# COMUNICAÇÃO - WhatsApp (Z-API)
# =============================================================================

from .zapi_service import ZAPIService

# =============================================================================
# SEGURANÇA - Auth, Rate Limit, Security, LGPD
# =============================================================================

# Auth
from .auth_service import hash_password, verify_password

# Rate Limiting (Login)
from .rate_limit_service import (
    check_rate_limit,
    log_login_attempt,
    get_login_history,
)

# Message Rate Limiting
from .message_rate_limiter import (
    check_message_rate_limit,
    get_rate_limit_status,
    reset_rate_limit,
    get_rate_limit_response,
    get_rate_limiter,
)

# Security
from .security_service import (
    run_security_check,
    get_safe_response_for_threat,
    sanitize_input,
    ThreatLevel,
    ThreatType,
    SecurityCheckResult,
)

# LGPD
from .lgpd_service import (
    detect_lgpd_request,
    get_lgpd_response,
    export_lead_data,
    delete_lead_data,
    rectify_lead_data,
    anonymize_lead,
    get_processing_info,
)

# Audit
from .audit_service import (
    log_audit,
    log_message_received,
    log_security_threat,
    log_lgpd_action,
    log_ai_action,
    flush_audit_buffer,
    get_audit_logs,
    AuditAction,
    AuditSeverity,
)

# =============================================================================
# NEGÓCIO - Guards, Handoff, Distribution, Reengagement
# =============================================================================

# AI Guards
from .ai_guard_service import (
    run_ai_guards,
    run_ai_guards_async,
    check_faq,
    check_scope,
    check_message_limit,
)

def _get_default_headers(self) -> dict:
    headers = {}
    if self.client_token:
        headers["Client-Token"] = self.client_token
    return headers

# Handoff
from .handoff_service import (
    execute_handoff,
    check_handoff_triggers,
)

# Distribution
from .distribution_service import (
    distribute_lead,
    get_available_sellers,
    assign_lead_to_seller,
)

# Reengagement
from .reengagement_service import (
    process_reengagement_batch,
    execute_reengagement,
    get_leads_to_reengage,
    get_reengagement_message,
    mark_lead_activity,
    DEFAULT_REENGAGEMENT_CONFIG,
)

# =============================================================================
# OPERACIONAL - Business Hours, Notifications, Export
# =============================================================================

# Business Hours
from .business_hours_service import (
    check_business_hours,
    is_within_business_hours,
    get_out_of_hours_message,
    get_next_business_opening,
    get_business_hours_summary,
    BusinessHoursCheckResult,
)

# Notifications
from .notification_service import (
    notify_gestor,
    notify_seller,
    notify_seller_whatsapp,
    notify_lead_hot,
    notify_lead_empreendimento,
    notify_out_of_hours,
    notify_handoff_requested,
    create_panel_notification,
    notify_gestor_whatsapp,
    build_lead_summary_text,
    build_seller_notification_message,
)

# Export
from .export_service import (
    export_to_excel,
    export_to_csv,
    export_to_pdf,
    get_leads_for_export,
    get_metrics_for_export,
)

# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # CORE AI
    "chat_completion",
    "extract_lead_data",
    "qualify_lead",
    "generate_lead_summary",
    "detect_sentiment",
    "generate_context_aware_response",
    "generate_conversation_summary",
    "calculate_typing_delay",
    "get_random_greeting",
    "get_random_acknowledgment",

    # WHATSAPP
    "ZAPIService",

    # AUTH
    "hash_password",
    "verify_password",

    # RATE LIMIT
    "check_rate_limit",
    "log_login_attempt",
    "get_login_history",
    "check_message_rate_limit",
    "get_rate_limit_status",
    "reset_rate_limit",
    "get_rate_limit_response",
    "get_rate_limiter",

    # SECURITY
    "run_security_check",
    "get_safe_response_for_threat",
    "sanitize_input",
    "ThreatLevel",
    "ThreatType",
    "SecurityCheckResult",

    # LGPD
    "detect_lgpd_request",
    "get_lgpd_response",
    "export_lead_data",
    "delete_lead_data",
    "rectify_lead_data",
    "anonymize_lead",
    "get_processing_info",

    # AUDIT
    "log_audit",
    "log_message_received",
    "log_security_threat",
    "log_lgpd_action",
    "log_ai_action",
    "flush_audit_buffer",
    "get_audit_logs",
    "AuditAction",
    "AuditSeverity",

    # BUSINESS
    "run_ai_guards",
    "run_ai_guards_async",
    "check_faq",
    "check_scope",
    "check_message_limit",
    "execute_handoff",
    "check_handoff_triggers",
    "distribute_lead",
    "get_available_sellers",
    "assign_lead_to_seller",
    "process_reengagement_batch",
    "execute_reengagement",
    "get_leads_to_reengage",
    "get_reengagement_message",
    "mark_lead_activity",
    "DEFAULT_REENGAGEMENT_CONFIG",

    # OPERACIONAL
    "check_business_hours",
    "is_within_business_hours",
    "get_out_of_hours_message",
    "get_next_business_opening",
    "get_business_hours_summary",
    "BusinessHoursCheckResult",
    "notify_gestor",
    "notify_seller",
    "notify_seller_whatsapp",
    "notify_lead_hot",
    "notify_lead_empreendimento",
    "notify_out_of_hours",
    "notify_handoff_requested",
    "create_panel_notification",
    "notify_gestor_whatsapp",
    "build_lead_summary_text",
    "build_seller_notification_message",
    "export_to_excel",
    "export_to_csv",
    "export_to_pdf",
    "get_leads_for_export",
    "get_metrics_for_export",
]
