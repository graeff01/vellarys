"""add message sender type tracking

Revision ID: 20260124_message_sender
Revises: 20260124_handoff_control
Create Date: 2026-01-24

Adiciona campos para rastrear tipo de remetente:
- sender_type: ai, seller, manager, system
- sender_user_id: ID do user que enviou (se humano)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '20260124_message_sender'
down_revision = '20260124_handoff_control'
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in the database."""
    conn = op.get_bind()
    result = conn.execute(text(
        "SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = :table AND column_name = :column)"
    ), {"table": table_name, "column": column_name})
    return result.scalar()


def upgrade() -> None:
    """
    Adiciona campos de rastreamento de remetente.
    """

    # 1. Adiciona campo sender_type
    if not column_exists('messages', 'sender_type'):
        op.add_column('messages',
            sa.Column('sender_type', sa.String(20), nullable=True))
        print("✅ Campo sender_type adicionado à tabela messages")

        # Popula mensagens existentes
        op.execute("""
            UPDATE messages
            SET sender_type = CASE
                WHEN role = 'assistant' THEN 'ai'
                WHEN role = 'system' THEN 'system'
                ELSE NULL
            END
        """)
        print("✅ Mensagens existentes populadas com sender_type")
    else:
        print("ℹ️ Campo sender_type já existe na tabela messages")

    # 2. Adiciona campo sender_user_id
    if not column_exists('messages', 'sender_user_id'):
        op.add_column('messages',
            sa.Column('sender_user_id', sa.Integer(),
                      sa.ForeignKey('users.id', ondelete='SET NULL'),
                      nullable=True))
        op.create_index('ix_messages_sender_user_id', 'messages', ['sender_user_id'])
        print("✅ Campo sender_user_id adicionado à tabela messages")
    else:
        print("ℹ️ Campo sender_user_id já existe na tabela messages")


def downgrade() -> None:
    """
    Remove campos de rastreamento.
    """
    if column_exists('messages', 'sender_user_id'):
        op.drop_index('ix_messages_sender_user_id', 'messages')
        op.drop_column('messages', 'sender_user_id')
        print("✅ Campo sender_user_id removido")

    if column_exists('messages', 'sender_type'):
        op.drop_column('messages', 'sender_type')
        print("✅ Campo sender_type removido")
