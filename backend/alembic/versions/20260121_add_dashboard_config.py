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
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '20260121_dashboard_config'
down_revision = '20260121_knowledge_embeddings'
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    conn = op.get_bind()
    result = conn.execute(text(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :name)"
    ), {"name": table_name})
    return result.scalar()


def index_exists(index_name: str) -> bool:
    """Check if an index exists in the database."""
    conn = op.get_bind()
    result = conn.execute(text(
        "SELECT EXISTS (SELECT FROM pg_indexes WHERE indexname = :name)"
    ), {"name": index_name})
    return result.scalar()


def upgrade() -> None:
    """
    Cria tabelas para dashboard customizável e metas de vendas.
    Usa verificações para evitar erros se tabelas já existirem.
    """

    # =============================================
    # DASHBOARD CONFIGS
    # =============================================
    if not table_exists('dashboard_configs'):
        op.create_table(
            'dashboard_configs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(100), nullable=False, server_default='Principal'),
            sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('widgets', postgresql.JSONB(), nullable=False, server_default='[]'),
            sa.Column('settings', postgresql.JSONB(), nullable=True, server_default='{}'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        print("Created table: dashboard_configs")
    else:
        print("Table dashboard_configs already exists, skipping...")

    # Índices (com verificação)
    if not index_exists('idx_dashboard_configs_user'):
        op.create_index('idx_dashboard_configs_user', 'dashboard_configs', ['user_id'])
    if not index_exists('idx_dashboard_configs_tenant'):
        op.create_index('idx_dashboard_configs_tenant', 'dashboard_configs', ['tenant_id'])
    if not index_exists('idx_dashboard_configs_tenant_active'):
        op.create_index('idx_dashboard_configs_tenant_active', 'dashboard_configs', ['tenant_id', 'is_active'])

    # =============================================
    # SALES GOALS
    # =============================================
    if not table_exists('sales_goals'):
        op.create_table(
            'sales_goals',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('period', sa.String(7), nullable=False),
            sa.Column('revenue_goal', sa.Integer(), nullable=True),
            sa.Column('deals_goal', sa.Integer(), nullable=True),
            sa.Column('leads_goal', sa.Integer(), nullable=True),
            sa.Column('revenue_actual', sa.Integer(), server_default='0', nullable=False),
            sa.Column('deals_actual', sa.Integer(), server_default='0', nullable=False),
            sa.Column('config', postgresql.JSONB(), nullable=True, server_default='{}'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        print("Created table: sales_goals")
    else:
        print("Table sales_goals already exists, skipping...")

    # Índices (com verificação)
    if not index_exists('idx_sales_goals_tenant'):
        op.create_index('idx_sales_goals_tenant', 'sales_goals', ['tenant_id'])
    if not index_exists('idx_sales_goals_tenant_period'):
        op.create_index('idx_sales_goals_tenant_period', 'sales_goals', ['tenant_id', 'period'], unique=True)

    print("Dashboard config migration completed!")


def downgrade() -> None:
    """Remove tabelas de dashboard config e sales goals."""
    if table_exists('sales_goals'):
        op.drop_table('sales_goals')
    if table_exists('dashboard_configs'):
        op.drop_table('dashboard_configs')
