"""add handoff history

Revision ID: 20260125_handoff_history
Revises: 20260125_lead_archiving
Create Date: 2026-01-25

Cria tabela de histórico de transferências (handoffs).
Registra IA→Seller, Seller→AI, Seller→Seller para auditoria.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '20260125_handoff_history'
down_revision = '20260125_lead_archiving'
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
    Cria tabela de histórico de transferências.
    """

    if not table_exists('handoff_history'):
        op.create_table(
            'handoff_history',
            # Primary Key
            sa.Column('id', sa.Integer(), nullable=False),

            # Foreign Keys
            sa.Column('lead_id', sa.Integer(), nullable=False),
            sa.Column('from_seller_id', sa.Integer(), nullable=True),
            sa.Column('to_seller_id', sa.Integer(), nullable=True),
            sa.Column('initiated_by_user_id', sa.Integer(), nullable=True),

            # Handoff details
            sa.Column('from_attended_by', sa.String(20), nullable=True),  # "ai", "seller", etc
            sa.Column('to_attended_by', sa.String(20), nullable=False),   # "seller", "ai", etc
            sa.Column('reason', sa.Text(), nullable=True),

            # Timestamps
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

            # Constraints
            sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['from_seller_id'], ['sellers.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['to_seller_id'], ['sellers.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['initiated_by_user_id'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )
        print("✅ Tabela handoff_history criada")
    else:
        print("ℹ️ Tabela handoff_history já existe")

    # Índices
    if not index_exists('ix_handoff_history_lead'):
        op.create_index('ix_handoff_history_lead', 'handoff_history', ['lead_id', sa.text('created_at DESC')])
        print("✅ Índice ix_handoff_history_lead criado")

    if not index_exists('ix_handoff_history_from_to'):
        op.create_index('ix_handoff_history_from_to', 'handoff_history', ['from_attended_by', 'to_attended_by'])
        print("✅ Índice ix_handoff_history_from_to criado")


def downgrade() -> None:
    """
    Remove tabela de handoff_history.
    """
    if index_exists('ix_handoff_history_from_to'):
        op.drop_index('ix_handoff_history_from_to', 'handoff_history')
        print("✅ Índice ix_handoff_history_from_to removido")

    if index_exists('ix_handoff_history_lead'):
        op.drop_index('ix_handoff_history_lead', 'handoff_history')
        print("✅ Índice ix_handoff_history_lead removido")

    if table_exists('handoff_history'):
        op.drop_table('handoff_history')
        print("✅ Tabela handoff_history removida")
