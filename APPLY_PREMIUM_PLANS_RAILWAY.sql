-- ============================================================================
-- MIGRAÇÃO: Planos B2B Premium (2 Tiers)
-- ============================================================================
-- Execute este SQL no Railway PostgreSQL Query Editor
-- Tempo estimado: 1 minuto
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. ATUALIZAR PLANO PROFESSIONAL
-- ============================================================================

UPDATE plans
SET
    name = 'Professional',
    description = 'Tudo que você precisa para crescer',
    price_monthly = 897.00,
    price_yearly = 8970.00,
    limits = '{
        "leads_per_month": 2000,
        "messages_per_month": 20000,
        "sellers": 15,
        "ai_tokens_per_month": 1000000
    }'::jsonb,
    features = '{
        "ai_qualification": true,
        "whatsapp_integration": true,
        "web_chat": true,
        "messenger_integration": true,
        "push_notifications": true,
        "templates_enabled": true,
        "notes_enabled": true,
        "attachments_enabled": true,
        "search_enabled": true,
        "sse_enabled": true,
        "calendar_enabled": true,
        "calendar_integration": true,
        "appointment_booking": true,
        "appointment_mode": "assisted",
        "metrics_enabled": true,
        "reports_enabled": true,
        "basic_reports": true,
        "advanced_reports": true,
        "lead_export": true,
        "archive_enabled": true,
        "reengagement_enabled": true,
        "reengagement_limit": 1,
        "voice_response_enabled": true,
        "semantic_search": true,
        "ai_guard_enabled": false,
        "knowledge_base_enabled": false,
        "copilot_enabled": false,
        "ai_sentiment_alerts_enabled": false,
        "ai_auto_handoff_enabled": false,
        "api_access_enabled": false,
        "webhooks": false,
        "white_label": false,
        "custom_integrations": false,
        "priority_support": false,
        "account_manager": false,
        "sla_99_5": false,
        "sso_enabled": false,
        "security_ghost_mode_enabled": false,
        "distrib_auto_assign_enabled": false,
        "audit_log_enabled": false,
        "auto_backup": false
    }'::jsonb,
    sort_order = 1,
    is_featured = true,
    updated_at = NOW()
WHERE slug = 'professional';

-- Se não existir, criar
INSERT INTO plans (slug, name, description, price_monthly, price_yearly, limits, features, sort_order, is_featured, active, created_at, updated_at)
SELECT 
    'professional',
    'Professional',
    'Tudo que você precisa para crescer',
    897.00,
    8970.00,
    '{
        "leads_per_month": 2000,
        "messages_per_month": 20000,
        "sellers": 15,
        "ai_tokens_per_month": 1000000
    }'::jsonb,
    '{
        "ai_qualification": true,
        "whatsapp_integration": true,
        "web_chat": true,
        "messenger_integration": true,
        "push_notifications": true,
        "templates_enabled": true,
        "notes_enabled": true,
        "attachments_enabled": true,
        "search_enabled": true,
        "sse_enabled": true,
        "calendar_enabled": true,
        "calendar_integration": true,
        "appointment_booking": true,
        "appointment_mode": "assisted",
        "metrics_enabled": true,
        "reports_enabled": true,
        "basic_reports": true,
        "advanced_reports": true,
        "lead_export": true,
        "archive_enabled": true,
        "reengagement_enabled": true,
        "reengagement_limit": 1,
        "voice_response_enabled": true,
        "semantic_search": true,
        "ai_guard_enabled": false,
        "knowledge_base_enabled": false,
        "copilot_enabled": false,
        "ai_sentiment_alerts_enabled": false,
        "ai_auto_handoff_enabled": false,
        "api_access_enabled": false,
        "webhooks": false,
        "white_label": false,
        "custom_integrations": false,
        "priority_support": false,
        "account_manager": false,
        "sla_99_5": false,
        "sso_enabled": false,
        "security_ghost_mode_enabled": false,
        "distrib_auto_assign_enabled": false,
        "audit_log_enabled": false,
        "auto_backup": false
    }'::jsonb,
    1,
    true,
    true,
    NOW(),
    NOW()
WHERE NOT EXISTS (SELECT 1 FROM plans WHERE slug = 'professional');

-- ============================================================================
-- 2. ATUALIZAR PLANO ENTERPRISE
-- ============================================================================

UPDATE plans
SET
    name = 'Enterprise',
    description = 'Liberdade total + Máxima automação',
    price_monthly = 1997.00,
    price_yearly = 19970.00,
    limits = '{
        "leads_per_month": -1,
        "messages_per_month": -1,
        "sellers": -1,
        "ai_tokens_per_month": 3000000
    }'::jsonb,
    features = '{
        "ai_qualification": true,
        "whatsapp_integration": true,
        "web_chat": true,
        "messenger_integration": true,
        "push_notifications": true,
        "templates_enabled": true,
        "notes_enabled": true,
        "attachments_enabled": true,
        "search_enabled": true,
        "sse_enabled": true,
        "calendar_enabled": true,
        "calendar_integration": true,
        "appointment_booking": true,
        "appointment_mode": "automatic",
        "appointment_auto_create": true,
        "appointment_reminders": true,
        "calendar_email_invites": true,
        "appointment_rescheduling": true,
        "metrics_enabled": true,
        "reports_enabled": true,
        "basic_reports": true,
        "advanced_reports": true,
        "lead_export": true,
        "archive_enabled": true,
        "reengagement_enabled": true,
        "reengagement_limit": -1,
        "voice_response_enabled": true,
        "semantic_search": true,
        "ai_guard_enabled": true,
        "knowledge_base_enabled": true,
        "copilot_enabled": true,
        "ai_sentiment_alerts_enabled": true,
        "ai_auto_handoff_enabled": true,
        "api_access_enabled": true,
        "webhooks": true,
        "white_label": true,
        "custom_integrations": true,
        "sso_enabled": true,
        "security_ghost_mode_enabled": true,
        "security_export_lock_enabled": false,
        "distrib_auto_assign_enabled": true,
        "audit_log_enabled": true,
        "auto_backup": true,
        "priority_support": true,
        "account_manager": true,
        "sla_99_5": true
    }'::jsonb,
    sort_order = 2,
    is_featured = false,
    updated_at = NOW()
WHERE slug = 'enterprise';

-- Se não existir, criar
INSERT INTO plans (slug, name, description, price_monthly, price_yearly, limits, features, sort_order, is_featured, active, created_at, updated_at)
SELECT 
    'enterprise',
    'Enterprise',
    'Liberdade total + Máxima automação',
    1997.00,
    19970.00,
    '{
        "leads_per_month": -1,
        "messages_per_month": -1,
        "sellers": -1,
        "ai_tokens_per_month": 3000000
    }'::jsonb,
    '{
        "ai_qualification": true,
        "whatsapp_integration": true,
        "web_chat": true,
        "messenger_integration": true,
        "push_notifications": true,
        "templates_enabled": true,
        "notes_enabled": true,
        "attachments_enabled": true,
        "search_enabled": true,
        "sse_enabled": true,
        "calendar_enabled": true,
        "calendar_integration": true,
        "appointment_booking": true,
        "appointment_mode": "automatic",
        "appointment_auto_create": true,
        "appointment_reminders": true,
        "calendar_email_invites": true,
        "appointment_rescheduling": true,
        "metrics_enabled": true,
        "reports_enabled": true,
        "basic_reports": true,
        "advanced_reports": true,
        "lead_export": true,
        "archive_enabled": true,
        "reengagement_enabled": true,
        "reengagement_limit": -1,
        "voice_response_enabled": true,
        "semantic_search": true,
        "ai_guard_enabled": true,
        "knowledge_base_enabled": true,
        "copilot_enabled": true,
        "ai_sentiment_alerts_enabled": true,
        "ai_auto_handoff_enabled": true,
        "api_access_enabled": true,
        "webhooks": true,
        "white_label": true,
        "custom_integrations": true,
        "sso_enabled": true,
        "security_ghost_mode_enabled": true,
        "security_export_lock_enabled": false,
        "distrib_auto_assign_enabled": true,
        "audit_log_enabled": true,
        "auto_backup": true,
        "priority_support": true,
        "account_manager": true,
        "sla_99_5": true
    }'::jsonb,
    2,
    false,
    true,
    NOW(),
    NOW()
WHERE NOT EXISTS (SELECT 1 FROM plans WHERE slug = 'enterprise');

-- ============================================================================
-- 3. MIGRAR CLIENTES DO PLANO "ESSENCIAL" PARA "PROFESSIONAL"
-- ============================================================================

-- Migrar assinaturas
UPDATE tenant_subscriptions ts
SET 
    plan_id = (SELECT id FROM plans WHERE slug = 'professional' LIMIT 1),
    updated_at = NOW()
WHERE plan_id = (SELECT id FROM plans WHERE slug = 'essencial' LIMIT 1);

-- ============================================================================
-- 4. REMOVER PLANO "ESSENCIAL"
-- ============================================================================

DELETE FROM plans WHERE slug = 'essencial';

COMMIT;

-- ============================================================================
-- VERIFICAÇÃO
-- ============================================================================

SELECT 
    slug,
    name,
    price_monthly,
    price_yearly,
    (limits->>'leads_per_month')::text as leads_limit,
    (limits->>'sellers')::text as sellers_limit,
    (features->>'appointment_mode')::text as appointment_mode,
    (features->>'api_access_enabled')::text as has_api,
    sort_order,
    is_featured
FROM plans
WHERE active = true
ORDER BY sort_order;

-- Verificar clientes por plano
SELECT 
    p.slug as plano,
    p.name as nome_plano,
    COUNT(ts.id) as total_clientes
FROM plans p
LEFT JOIN tenant_subscriptions ts ON ts.plan_id = p.id
WHERE p.active = true
GROUP BY p.id, p.slug, p.name
ORDER BY p.sort_order;
