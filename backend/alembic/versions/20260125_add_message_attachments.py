"""add message attachments

Revision ID: 20260125_message_attachments
Revises: 20260125_lead_notes
Create Date: 2026-01-25

Adiciona suporte a anexos em mensagens (imagens, documentos, vídeos).
Armazenados como JSONB array.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '20260125_message_attachments'
down_revision = '20260125_lead_notes'
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
    Adiciona campo attachments (JSONB) em mensagens.
    """

    if not column_exists('messages', 'attachments'):
        op.add_column('messages',
            sa.Column('attachments', postgresql.JSONB(), nullable=True, server_default='[]'))
        print("✅ Campo attachments adicionado à tabela messages")
    else:
        print("ℹ️ Campo attachments já existe")

    # Índice GIN para queries em JSONB
    if not index_exists('ix_messages_attachments'):
        op.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_messages_attachments ON messages USING gin(attachments)"
        ))
        print("✅ Índice GIN ix_messages_attachments criado")


def downgrade() -> None:
    """
    Remove campo attachments.
    """
    if index_exists('ix_messages_attachments'):
        op.drop_index('ix_messages_attachments', 'messages')
        print("✅ Índice ix_messages_attachments removido")

    if column_exists('messages', 'attachments'):
        op.drop_column('messages', 'attachments')
        print("✅ Campo attachments removido")
