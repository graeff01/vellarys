"""add dashboard config and sales goals tables

Revision ID: 20260121_dashboard_config
Revises: 20260121_knowledge_embeddings
Create Date: 2026-01-21

Adiciona tabelas para:
- dashboard_configs: Configuração personalizada do dashboard por usuário
- sales_goals: Metas de vendas mensais por tenant
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260121_dashboard_config'
down_revision = '20260121_knowledge_embeddings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Cria tabelas para dashboard customizável e metas de vendas.
    """

    # =============================================
    # DASHBOARD CONFIGS
    # =============================================
    op.create_table(
        'dashboard_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False, server_default='Principal'),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),

        # Widgets: Lista de configurações de widgets
        # [{"id": "...", "type": "...", "enabled": true, "position": 0, "size": "full", "settings": {}}]
        sa.Column('widgets', postgresql.JSONB(), nullable=False, server_default='[]'),

        # Configurações globais do dashboard
        sa.Column('settings', postgresql.JSONB(), nullable=True, server_default='{}'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Foreign keys
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),

        # Primary key
        sa.PrimaryKeyConstraint('id'),
    )

    # Índices
    op.create_index('idx_dashboard_configs_user', 'dashboard_configs', ['user_id'])
    op.create_index('idx_dashboard_configs_tenant', 'dashboard_configs', ['tenant_id'])
    op.create_index('idx_dashboard_configs_tenant_active', 'dashboard_configs', ['tenant_id', 'is_active'])

    # =============================================
    # SALES GOALS
    # =============================================
    op.create_table(
        'sales_goals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # Período (YYYY-MM)
        sa.Column('period', sa.String(7), nullable=False),  # "2026-01"

        # Metas (em centavos para evitar problemas com decimais)
        sa.Column('revenue_goal', sa.Integer(), nullable=True),  # Meta de receita
        sa.Column('deals_goal', sa.Integer(), nullable=True),  # Meta de número de vendas
        sa.Column('leads_goal', sa.Integer(), nullable=True),  # Meta de leads

        # Valores realizados
        sa.Column('revenue_actual', sa.Integer(), server_default='0', nullable=False),
        sa.Column('deals_actual', sa.Integer(), server_default='0', nullable=False),

        # Configurações extras
        sa.Column('config', postgresql.JSONB(), nullable=True, server_default='{}'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Foreign keys
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),

        # Primary key
        sa.PrimaryKeyConstraint('id'),
    )

    # Índices
    op.create_index('idx_sales_goals_tenant', 'sales_goals', ['tenant_id'])
    op.create_index('idx_sales_goals_tenant_period', 'sales_goals', ['tenant_id', 'period'], unique=True)


def downgrade() -> None:
    """Remove tabelas de dashboard config e sales goals."""
    op.drop_table('sales_goals')
    op.drop_table('dashboard_configs')
