"""add lead archiving

Revision ID: 20260125_lead_archiving
Revises: 20260125_message_attachments
Create Date: 2026-01-25

Adiciona soft-delete de leads (arquivamento).
Permite organizar conversas finalizadas sem perder histórico.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '20260125_lead_archiving'
down_revision = '20260125_message_attachments'
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in the database."""
    conn = op.get_bind()
    result = conn.execute(text(
        "SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = :table AND column_name = :column)"
    ), {"table": table_name, "column": column_name})
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
    Adiciona campos para arquivamento de leads.
    """

    # 1. Campo archived_at
    if not column_exists('leads', 'archived_at'):
        op.add_column('leads',
            sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True))
        print("✅ Campo archived_at adicionado à tabela leads")
    else:
        print("ℹ️ Campo archived_at já existe")

    # 2. Campo archived_by
    if not column_exists('leads', 'archived_by'):
        op.add_column('leads',
            sa.Column('archived_by', sa.Integer(),
                     sa.ForeignKey('users.id', ondelete='SET NULL'),
                     nullable=True))
        print("✅ Campo archived_by adicionado")
    else:
        print("ℹ️ Campo archived_by já existe")

    # 3. Campo archive_reason
    if not column_exists('leads', 'archive_reason'):
        op.add_column('leads',
            sa.Column('archive_reason', sa.Text(), nullable=True))
        print("✅ Campo archive_reason adicionado")
    else:
        print("ℹ️ Campo archive_reason já existe")

    # 4. Índice parcial para leads não arquivados (query mais comum)
    if not index_exists('ix_leads_active'):
        op.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_leads_active
            ON leads(tenant_id, updated_at DESC)
            WHERE archived_at IS NULL
        """))
        print("✅ Índice parcial ix_leads_active criado")


def downgrade() -> None:
    """
    Remove campos de arquivamento.
    """
    if index_exists('ix_leads_active'):
        op.drop_index('ix_leads_active', 'leads')
        print("✅ Índice ix_leads_active removido")

    if column_exists('leads', 'archive_reason'):
        op.drop_column('leads', 'archive_reason')
        print("✅ Campo archive_reason removido")

    if column_exists('leads', 'archived_by'):
        op.drop_column('leads', 'archived_by')
        print("✅ Campo archived_by removido")

    if column_exists('leads', 'archived_at'):
        op.drop_column('leads', 'archived_at')
        print("✅ Campo archived_at removido")
