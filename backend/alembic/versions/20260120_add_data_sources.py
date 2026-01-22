"""add data_sources table for multi-tenant property lookup

Revision ID: 20260120_003
Revises: 20260120_add_performance_indexes
Create Date: 2026-01-20 10:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

revision = '20260120_003'
down_revision = '20260120_add_performance_indexes'
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(text(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :name)"
    ), {"name": table_name})
    return result.scalar()


def index_exists(index_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(text(
        "SELECT EXISTS (SELECT FROM pg_indexes WHERE indexname = :name)"
    ), {"name": index_name})
    return result.scalar()


def upgrade():
    # Criar tabela data_sources
    if not table_exists('data_sources'):
        op.create_table(
            'data_sources',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('slug', sa.String(100), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('type', sa.String(50), nullable=False, server_default='manual'),
            sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('config', postgresql.JSONB(), nullable=False, server_default='{}'),
            sa.Column('credentials_encrypted', postgresql.JSONB(), nullable=True),
            sa.Column('field_mapping', postgresql.JSONB(), nullable=True),
            sa.Column('cache_ttl_seconds', sa.Integer(), nullable=False, server_default='300'),
            sa.Column('cache_strategy', sa.String(50), nullable=False, server_default='memory'),
            sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('last_sync_status', sa.String(50), nullable=True),
            sa.Column('last_sync_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('last_error', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )

    # Índices
    if not index_exists('ix_data_sources_tenant_id'):
        op.create_index('ix_data_sources_tenant_id', 'data_sources', ['tenant_id'])
    if not index_exists('ix_data_sources_tenant_active'):
        op.create_index('ix_data_sources_tenant_active', 'data_sources', ['tenant_id', 'active'])
    if not index_exists('ix_data_sources_tenant_slug'):
        op.create_index('ix_data_sources_tenant_slug', 'data_sources', ['tenant_id', 'slug'], unique=True)
    if not index_exists('ix_data_sources_tenant_priority'):
        op.create_index('ix_data_sources_tenant_priority', 'data_sources', ['tenant_id', 'priority'])


def downgrade():
    if index_exists('ix_data_sources_tenant_priority'):
        op.drop_index('ix_data_sources_tenant_priority', table_name='data_sources')
    if index_exists('ix_data_sources_tenant_slug'):
        op.drop_index('ix_data_sources_tenant_slug', table_name='data_sources')
    if index_exists('ix_data_sources_tenant_active'):
        op.drop_index('ix_data_sources_tenant_active', table_name='data_sources')
    if index_exists('ix_data_sources_tenant_id'):
        op.drop_index('ix_data_sources_tenant_id', table_name='data_sources')
    if table_exists('data_sources'):
        op.drop_table('data_sources')
