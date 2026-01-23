"""add opportunities table

Revision ID: 20260122_opportunities
Revises: 20260121_dashboard_config
Create Date: 2026-01-22

Adiciona tabela para:
- opportunities: Oportunidades/negócios vinculados a leads
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '20260122_opportunities'
down_revision = '20260121_dashboard_config'
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
    Cria tabela de oportunidades/negócios.
    Usa verificações para evitar erros se tabela já existir.
    """

    # =============================================
    # OPPORTUNITIES
    # =============================================
    if not table_exists('opportunities'):
        op.create_table(
            'opportunities',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('lead_id', sa.Integer(), nullable=False),
            sa.Column('product_id', sa.Integer(), nullable=True),
            sa.Column('seller_id', sa.Integer(), nullable=True),
            sa.Column('title', sa.String(200), nullable=False),
            sa.Column('value', sa.Integer(), server_default='0', nullable=False),
            sa.Column('status', sa.String(20), server_default='novo', nullable=False),
            sa.Column('expected_close_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('won_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('lost_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('lost_reason', sa.String(200), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('custom_data', postgresql.JSONB(), nullable=True, server_default='{}'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['seller_id'], ['sellers.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )
        print("Created table: opportunities")
    else:
        print("Table opportunities already exists, skipping...")

    # Índices (com verificação)
    if not index_exists('ix_opportunities_tenant_id'):
        op.create_index('ix_opportunities_tenant_id', 'opportunities', ['tenant_id'])
    if not index_exists('ix_opportunities_lead_id'):
        op.create_index('ix_opportunities_lead_id', 'opportunities', ['lead_id'])
    if not index_exists('ix_opportunities_product_id'):
        op.create_index('ix_opportunities_product_id', 'opportunities', ['product_id'])
    if not index_exists('ix_opportunities_seller_id'):
        op.create_index('ix_opportunities_seller_id', 'opportunities', ['seller_id'])
    if not index_exists('ix_opportunities_status'):
        op.create_index('ix_opportunities_status', 'opportunities', ['status'])
    if not index_exists('ix_opportunities_tenant_status'):
        op.create_index('ix_opportunities_tenant_status', 'opportunities', ['tenant_id', 'status'])
    if not index_exists('ix_opportunities_tenant_created'):
        op.create_index('ix_opportunities_tenant_created', 'opportunities', ['tenant_id', 'created_at'])
    if not index_exists('ix_opportunities_lead_status'):
        op.create_index('ix_opportunities_lead_status', 'opportunities', ['lead_id', 'status'])

    print("Opportunities migration completed!")


def downgrade() -> None:
    """Remove tabela de opportunities."""
    if table_exists('opportunities'):
        op.drop_table('opportunities')
