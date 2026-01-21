"""update plans structure and remove niches field

Revision ID: 20260121_update_plans
Revises: 20260120_add_performance_indexes
Create Date: 2026-01-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260121_update_plans'
down_revision = '20260120_add_performance_indexes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Migration para atualizar estrutura de planos:
    1. Remove campo 'niches' dos limits (JSONB)
    2. Adiciona novas features ao campo features (JSONB)
    3. Atualiza valores dos planos existentes (se houver)

    Como limits e features são JSONB, podemos fazer update direto nos dados
    sem precisar alterar schema de colunas.
    """

    # Cria bind para executar SQL
    connection = op.get_bind()

    # ============================================================================
    # 1. REMOVE 'niches' de todos os planos (do campo limits JSONB)
    # ============================================================================
    print("📝 Removendo campo 'niches' dos limits...")
    connection.execute(sa.text("""
        UPDATE plans
        SET limits = limits - 'niches'
        WHERE limits ? 'niches'
    """))

    # ============================================================================
    # 2. ATUALIZA PLANO "STARTER" PARA "ESSENCIAL" (se existir)
    # ============================================================================
    print("📝 Atualizando plano 'starter' para 'essencial'...")

    # Verifica se existe plano 'starter'
    result = connection.execute(sa.text("""
        SELECT id FROM plans WHERE slug = 'starter'
    """))

    if result.rowcount > 0:
        connection.execute(sa.text("""
            UPDATE plans
            SET
                slug = 'essencial',
                name = 'Essencial',
                description = 'Para imobiliárias iniciando com IA',
                price_monthly = 297.00,
                price_yearly = 2970.00,
                limits = jsonb_build_object(
                    'leads_per_month', 300,
                    'messages_per_month', 3000,
                    'sellers', 3,
                    'ai_tokens_per_month', 150000
                ),
                features = jsonb_build_object(
                    'ai_qualification', true,
                    'whatsapp_integration', true,
                    'web_chat', true,
                    'push_notifications', true,
                    'basic_reports', true,
                    'lead_export', true,
                    'appointment_booking', false,
                    'calendar_integration', false,
                    'reengagement', false,
                    'advanced_reports', false,
                    'humanized_voice', false,
                    'multi_channel', false,
                    'semantic_search', false,
                    'api_access', false,
                    'white_label', false,
                    'priority_support', false
                )
            WHERE slug = 'starter'
        """))
        print("✅ Plano 'starter' atualizado para 'essencial'")

    # ============================================================================
    # 3. ATUALIZA PLANO "PROFESSIONAL"
    # ============================================================================
    print("📝 Atualizando plano 'professional'...")

    result = connection.execute(sa.text("""
        SELECT id FROM plans WHERE slug = 'professional'
    """))

    if result.rowcount > 0:
        connection.execute(sa.text("""
            UPDATE plans
            SET
                name = 'Professional',
                description = 'Melhor custo-benefício para crescimento',
                price_monthly = 697.00,
                price_yearly = 6970.00,
                is_featured = true,
                limits = jsonb_build_object(
                    'leads_per_month', 1500,
                    'messages_per_month', 15000,
                    'sellers', 15,
                    'ai_tokens_per_month', 750000
                ),
                features = jsonb_build_object(
                    'ai_qualification', true,
                    'whatsapp_integration', true,
                    'web_chat', true,
                    'push_notifications', true,
                    'basic_reports', true,
                    'lead_export', true,
                    'appointment_booking', true,
                    'appointment_mode', 'assisted',
                    'calendar_integration', true,
                    'reengagement', true,
                    'advanced_reports', true,
                    'humanized_voice', true,
                    'multi_channel', true,
                    'semantic_search', true,
                    'api_access', false,
                    'white_label', false,
                    'priority_support', false
                )
            WHERE slug = 'professional'
        """))
        print("✅ Plano 'professional' atualizado")

    # ============================================================================
    # 4. ATUALIZA PLANO "ENTERPRISE"
    # ============================================================================
    print("📝 Atualizando plano 'enterprise'...")

    result = connection.execute(sa.text("""
        SELECT id FROM plans WHERE slug = 'enterprise'
    """))

    if result.rowcount > 0:
        connection.execute(sa.text("""
            UPDATE plans
            SET
                name = 'Enterprise',
                description = 'Solução completa para grandes operações',
                price_monthly = 1497.00,
                price_yearly = 14970.00,
                limits = jsonb_build_object(
                    'leads_per_month', -1,
                    'messages_per_month', -1,
                    'sellers', -1,
                    'ai_tokens_per_month', 2000000
                ),
                features = jsonb_build_object(
                    'ai_qualification', true,
                    'whatsapp_integration', true,
                    'web_chat', true,
                    'push_notifications', true,
                    'basic_reports', true,
                    'lead_export', true,
                    'appointment_booking', true,
                    'appointment_mode', 'automatic',
                    'calendar_integration', true,
                    'appointment_auto_create', true,
                    'appointment_reminders', true,
                    'calendar_email_invites', true,
                    'reengagement', true,
                    'advanced_reports', true,
                    'humanized_voice', true,
                    'multi_channel', true,
                    'semantic_search', true,
                    'api_access', true,
                    'webhooks', true,
                    'white_label', true,
                    'priority_support', true,
                    'account_manager', true,
                    'custom_integrations', true,
                    'sla_99_5', true
                )
            WHERE slug = 'enterprise'
        """))
        print("✅ Plano 'enterprise' atualizado")

    # ============================================================================
    # 5. ATUALIZA TENANTS QUE ESTÃO COM PLANO "STARTER" PARA "ESSENCIAL"
    # ============================================================================
    print("📝 Atualizando tenants com plano 'starter' para 'essencial'...")
    connection.execute(sa.text("""
        UPDATE tenants
        SET plan = 'essencial'
        WHERE plan = 'starter'
    """))

    print("✅ Migration de planos concluída com sucesso!")


def downgrade() -> None:
    """
    Reverte as mudanças (volta para estrutura antiga)
    """
    connection = op.get_bind()

    # Volta essencial para starter
    connection.execute(sa.text("""
        UPDATE plans
        SET
            slug = 'starter',
            name = 'Starter',
            price_monthly = 97.00,
            price_yearly = 970.00
        WHERE slug = 'essencial'
    """))

    # Volta tenants também
    connection.execute(sa.text("""
        UPDATE tenants
        SET plan = 'starter'
        WHERE plan = 'essencial'
    """))

    # Restaura preços antigos do professional
    connection.execute(sa.text("""
        UPDATE plans
        SET
            price_monthly = 197.00,
            price_yearly = 1970.00,
            is_featured = true
        WHERE slug = 'professional'
    """))

    # Restaura preços antigos do enterprise
    connection.execute(sa.text("""
        UPDATE plans
        SET
            price_monthly = 497.00,
            price_yearly = 4970.00
        WHERE slug = 'enterprise'
    """))

    print("⏮️ Downgrade de planos concluído")
