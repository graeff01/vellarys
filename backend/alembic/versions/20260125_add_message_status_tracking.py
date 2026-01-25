"""add message status tracking

Revision ID: 20260125_message_status
Revises: 20260124_profile_picture
Create Date: 2026-01-25

Adiciona rastreamento de status de mensagens (enviada, entregue, lida).
Permite feedback visual igual WhatsApp (✓✓).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '20260125_message_status'
down_revision = '20260124_profile_picture'
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
    Adiciona rastreamento de status de mensagens.
    """

    # 1. Campo status
    if not column_exists('messages', 'status'):
        op.add_column('messages',
            sa.Column('status', sa.String(20), server_default='sent', nullable=False))
        print("✅ Campo status adicionado à tabela messages")
    else:
        print("ℹ️ Campo status já existe na tabela messages")

    # 2. Campo delivered_at
    if not column_exists('messages', 'delivered_at'):
        op.add_column('messages',
            sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True))
        print("✅ Campo delivered_at adicionado")
    else:
        print("ℹ️ Campo delivered_at já existe")

    # 3. Campo read_at
    if not column_exists('messages', 'read_at'):
        op.add_column('messages',
            sa.Column('read_at', sa.DateTime(timezone=True), nullable=True))
        print("✅ Campo read_at adicionado")
    else:
        print("ℹ️ Campo read_at já existe")

    # 4. Campo whatsapp_message_id (para correlacionar com webhooks)
    if not column_exists('messages', 'whatsapp_message_id'):
        op.add_column('messages',
            sa.Column('whatsapp_message_id', sa.String(100), nullable=True))
        print("✅ Campo whatsapp_message_id adicionado")
    else:
        print("ℹ️ Campo whatsapp_message_id já existe")

    # 5. Índice para queries de status
    if not index_exists('ix_messages_status'):
        op.create_index('ix_messages_status', 'messages', ['status'])
        print("✅ Índice ix_messages_status criado")

    # 6. Índice para buscar por whatsapp_message_id
    if not index_exists('ix_messages_whatsapp_id'):
        op.create_index('ix_messages_whatsapp_id', 'messages', ['whatsapp_message_id'])
        print("✅ Índice ix_messages_whatsapp_id criado")


def downgrade() -> None:
    """
    Remove campos de status.
    """
    if index_exists('ix_messages_whatsapp_id'):
        op.drop_index('ix_messages_whatsapp_id', 'messages')
        print("✅ Índice ix_messages_whatsapp_id removido")

    if index_exists('ix_messages_status'):
        op.drop_index('ix_messages_status', 'messages')
        print("✅ Índice ix_messages_status removido")

    if column_exists('messages', 'whatsapp_message_id'):
        op.drop_column('messages', 'whatsapp_message_id')
        print("✅ Campo whatsapp_message_id removido")

    if column_exists('messages', 'read_at'):
        op.drop_column('messages', 'read_at')
        print("✅ Campo read_at removido")

    if column_exists('messages', 'delivered_at'):
        op.drop_column('messages', 'delivered_at')
        print("✅ Campo delivered_at removido")

    if column_exists('messages', 'status'):
        op.drop_column('messages', 'status')
        print("✅ Campo status removido")
