"""
INFRASTRUCTURE SERVICES
========================

Serviços de infraestrutura do Velaris.

Organização:
- Core AI: OpenAI, Sentimento, Respostas
- Comunicação: WhatsApp (Gupshup, 360Dialog)
- Segurança: Auth, Rate Limit, Security, LGPD
- Negócio: Guards, Handoff, Distribution, Reengagement
- Operacional: Business Hours, Notifications, Export, Audit
"""

# =============================================================================
# CORE AI - OpenAI e Inteligência
# =============================================================================

from .openai_service import (
    # Funções base
    chat_completion,
    extract_lead_data,
    qualify_lead,
    generate_lead_summary,
    generate_proactive_suggestions,
    # Funções inteligentes
    detect_sentiment,
    generate_context_aware_response,
    generate_conversation_summary,
    calculate_typing_delay,
    get_random_greeting,
    get_random_acknowledgment,
)

# =============================================================================
# COMUNICAÇÃO - WhatsApp
# =============================================================================

# WhatsApp (legado)
from .whatsapp_service import send_whatsapp_message

# Gupshup (WhatsApp Business API)
from .gupshup_service import (
    GupshupService,
    GupshupConfig,
    SendMessageResult,
    ParsedIncomingMessage,
    get_gupshup_service,
    configure_gupshup_service,
    send_gupshup_message,
)

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

# AI Guards (validações de escopo, FAQ, limites)
from .ai_guard_service import (
    run_ai_guards,
    run_ai_guards_async,
    check_faq,
    check_scope,
    check_message_limit,
    # NOTA: check_business_hours removido daqui
    # Agora usa o business_hours_service que é mais completo
)

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

# Business Hours (Serviço completo de horário comercial)
from .business_hours_service import (
    check_business_hours,
    is_within_business_hours,
    get_out_of_hours_message,
    get_next_business_opening,
    get_business_hours_summary,
    BusinessHoursCheckResult,
)

# Notification Service (Notificações painel + WhatsApp gestor + vendedor)
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

from .zapi_service import ZAPIService


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # =========================================================================
    # CORE AI
    # =========================================================================
    "chat_completion",
    "ZAPIService",
    "extract_lead_data",
    "qualify_lead",
    "generate_lead_summary",
    "generate_proactive_suggestions",
    "detect_sentiment",
    "generate_context_aware_response",
    "generate_conversation_summary",
    "calculate_typing_delay",
    "get_random_greeting",
    "get_random_acknowledgment",
    
    # =========================================================================
    # COMUNICAÇÃO - WhatsApp
    # =========================================================================
    # Legado
    "send_whatsapp_message",
    # Gupshup
    "GupshupService",
    "GupshupConfig",
    "SendMessageResult",
    "ParsedIncomingMessage",
    "get_gupshup_service",
    "configure_gupshup_service",
    "send_gupshup_message",
    
    # =========================================================================
    # SEGURANÇA
    # =========================================================================
    # Auth
    "hash_password",
    "verify_password",
    # Rate Limiting (Login)
    "check_rate_limit",
    "log_login_attempt",
    "get_login_history",
    # Message Rate Limiting
    "check_message_rate_limit",
    "get_rate_limit_status",
    "reset_rate_limit",
    "get_rate_limit_response",
    "get_rate_limiter",
    # Security
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
    # Audit
    "log_audit",
    "log_message_received",
    "log_security_threat",
    "log_lgpd_action",
    "log_ai_action",
    "flush_audit_buffer",
    "get_audit_logs",
    "AuditAction",
    "AuditSeverity",
    
    # =========================================================================
    # NEGÓCIO
    # =========================================================================
    # AI Guards
    "run_ai_guards",
    "run_ai_guards_async",
    "check_faq",
    "check_scope",
    "check_message_limit",
    # Handoff
    "execute_handoff",
    "check_handoff_triggers",
    # Distribution
    "distribute_lead",
    "get_available_sellers",
    "assign_lead_to_seller",
    # Reengagement
    "process_reengagement_batch",
    "execute_reengagement",
    "get_leads_to_reengage",
    "get_reengagement_message",
    "mark_lead_activity",
    "DEFAULT_REENGAGEMENT_CONFIG",
    
    # =========================================================================
    # OPERACIONAL
    # =========================================================================
    # Business Hours
    "check_business_hours",
    "is_within_business_hours",
    "get_out_of_hours_message",
    "get_next_business_opening",
    "get_business_hours_summary",
    "BusinessHoursCheckResult",
    # Notification Service
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
    # Export
    "export_to_excel",
    "export_to_csv",
    "export_to_pdf",
    "get_leads_for_export",
    "get_metrics_for_export",
]