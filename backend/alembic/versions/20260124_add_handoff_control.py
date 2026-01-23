"""add handoff control fields

Revision ID: 20260124_handoff_control
Revises: 20260124_seller_user
Create Date: 2026-01-24

Adiciona campos para controle de handoff IA → Humano:
- attended_by: quem está atendendo (ai, seller, manager)
- seller_took_over_at: quando corretor assumiu conversa
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '20260124_handoff_control'
down_revision = '20260124_seller_user'
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
    Adiciona campos de controle de handoff.
    """

    # 1. Adiciona campo attended_by
    if not column_exists('leads', 'attended_by'):
        op.add_column('leads',
            sa.Column('attended_by', sa.String(20), nullable=True, server_default='ai'))
        print("✅ Campo attended_by adicionado à tabela leads")
    else:
        print("ℹ️ Campo attended_by já existe na tabela leads")

    # 2. Adiciona campo seller_took_over_at
    if not column_exists('leads', 'seller_took_over_at'):
        op.add_column('leads',
            sa.Column('seller_took_over_at', sa.DateTime(timezone=True), nullable=True))
        print("✅ Campo seller_took_over_at adicionado à tabela leads")
    else:
        print("ℹ️ Campo seller_took_over_at já existe na tabela leads")


def downgrade() -> None:
    """
    Remove campos de controle de handoff.
    """
    if column_exists('leads', 'seller_took_over_at'):
        op.drop_column('leads', 'seller_took_over_at')
        print("✅ Campo seller_took_over_at removido")

    if column_exists('leads', 'attended_by'):
        op.drop_column('leads', 'attended_by')
        print("✅ Campo attended_by removido")
