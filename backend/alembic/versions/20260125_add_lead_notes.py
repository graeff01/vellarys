"""add lead notes

Revision ID: 20260125_lead_notes
Revises: 20260125_message_status
Create Date: 2026-01-25

Cria tabela de anotações internas para leads.
Permite corretores adicionar observações privadas.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '20260125_lead_notes'
down_revision = '20260125_message_status'
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
    Cria tabela de anotações internas de leads.
    """

    if not table_exists('lead_notes'):
        op.create_table(
            'lead_notes',
            # Primary Key
            sa.Column('id', sa.Integer(), nullable=False),

            # Foreign Keys
            sa.Column('lead_id', sa.Integer(), nullable=False),
            sa.Column('author_id', sa.Integer(), nullable=False),

            # Content
            sa.Column('content', sa.Text(), nullable=False),

            # Timestamps
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

            # Constraints
            sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        print("✅ Tabela lead_notes criada")
    else:
        print("ℹ️ Tabela lead_notes já existe")

    # Índices
    if not index_exists('ix_lead_notes_lead_id'):
        op.create_index('ix_lead_notes_lead_id', 'lead_notes', ['lead_id'])
        print("✅ Índice ix_lead_notes_lead_id criado")

    if not index_exists('ix_lead_notes_created'):
        op.create_index('ix_lead_notes_created', 'lead_notes', ['lead_id', sa.text('created_at DESC')])
        print("✅ Índice ix_lead_notes_created criado")


def downgrade() -> None:
    """
    Remove tabela de lead_notes.
    """
    if index_exists('ix_lead_notes_created'):
        op.drop_index('ix_lead_notes_created', 'lead_notes')
        print("✅ Índice ix_lead_notes_created removido")

    if index_exists('ix_lead_notes_lead_id'):
        op.drop_index('ix_lead_notes_lead_id', 'lead_notes')
        print("✅ Índice ix_lead_notes_lead_id removido")

    if table_exists('lead_notes'):
        op.drop_table('lead_notes')
        print("✅ Tabela lead_notes removida")
