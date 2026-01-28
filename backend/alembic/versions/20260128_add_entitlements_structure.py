"""add entitlements structure

Revision ID: 20260128_add_entitlements
Revises: 20260126_add_appointments
Create Date: 2026-01-28 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260128_add_entitlements'
down_revision: Union[str, None] = '20260126_add_appointments'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Cria nova arquitetura de entitlements SEM remover estrutura antiga.
    Sistema continua funcionando normalmente.
    """

    # =========================================================================
    # 1. PLAN_ENTITLEMENTS - Define o que cada plano oferece
    # =========================================================================
    op.create_table(
        'plan_entitlements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),

        # Tipo de entitlement
        sa.Column('entitlement_type', sa.String(50), nullable=False),  # "feature" | "limit" | "addon"
        sa.Column('entitlement_key', sa.String(100), nullable=False, index=True),

        # Valor (JSONB flexível)
        sa.Column('entitlement_value', postgresql.JSONB(), nullable=False),

        # Metadata
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(50), nullable=False),  # "core" | "advanced" | "enterprise"

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('plan_id', 'entitlement_key', name='uq_plan_entitlement'),
    )

    op.create_index('ix_plan_entitlements_plan_id', 'plan_entitlements', ['plan_id'])
    op.create_index('ix_plan_entitlements_type_key', 'plan_entitlements', ['entitlement_type', 'entitlement_key'])

    # =========================================================================
    # 2. SUBSCRIPTION_OVERRIDES - SuperAdmin customizações
    # =========================================================================
    op.create_table(
        'subscription_overrides',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),

        # Override
        sa.Column('override_key', sa.String(100), nullable=False, index=True),
        sa.Column('override_type', sa.String(50), nullable=False),  # "feature" | "limit"
        sa.Column('override_value', postgresql.JSONB(), nullable=False),

        # Auditoria
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['subscription_id'], ['tenant_subscriptions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('subscription_id', 'override_key', name='uq_subscription_override'),
    )

    op.create_index('ix_subscription_overrides_subscription_id', 'subscription_overrides', ['subscription_id'])
    op.create_index('ix_subscription_overrides_expires_at', 'subscription_overrides', ['expires_at'])

    # =========================================================================
    # 3. FEATURE_FLAGS - Gestor toggles operacionais
    # =========================================================================
    op.create_table(
        'feature_flags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # Flag
        sa.Column('flag_key', sa.String(100), nullable=False, index=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, default=True),

        # Auditoria
        sa.Column('last_changed_by_id', sa.Integer(), nullable=False),
        sa.Column('last_changed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['last_changed_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('tenant_id', 'flag_key', name='uq_tenant_feature_flag'),
    )

    op.create_index('ix_feature_flags_tenant_id', 'feature_flags', ['tenant_id'])
    op.create_index('ix_feature_flags_tenant_flag', 'feature_flags', ['tenant_id', 'flag_key'])

    # =========================================================================
    # 4. FEATURE_AUDIT_LOGS - Histórico completo
    # =========================================================================
    op.create_table(
        'feature_audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # O que mudou
        sa.Column('change_type', sa.String(50), nullable=False),  # "override" | "flag" | "plan_change"
        sa.Column('entity_type', sa.String(50), nullable=False),  # "feature" | "limit"
        sa.Column('entity_key', sa.String(100), nullable=False),

        # Valores
        sa.Column('old_value', postgresql.JSONB(), nullable=True),
        sa.Column('new_value', postgresql.JSONB(), nullable=True),

        # Contexto
        sa.Column('changed_by_id', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),

        # Timestamp
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by_id'], ['users.id'], ondelete='SET NULL'),
    )

    op.create_index('ix_feature_audit_logs_tenant_id', 'feature_audit_logs', ['tenant_id'])
    op.create_index('ix_feature_audit_logs_created_at', 'feature_audit_logs', ['created_at'])
    op.create_index('ix_feature_audit_logs_entity', 'feature_audit_logs', ['entity_type', 'entity_key'])


def downgrade() -> None:
    """Reverte mudanças (caso necessário)."""
    op.drop_table('feature_audit_logs')
    op.drop_table('feature_flags')
    op.drop_table('subscription_overrides')
    op.drop_table('plan_entitlements')
