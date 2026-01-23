"""add seller_notified_at to leads

Revision ID: 20260123_seller_notified
Revises: 20260121_add_dashboard_config
Create Date: 2026-01-23

Adiciona campo seller_notified_at para controlar quando o vendedor foi notificado.
Isso permite notificação inteligente (esperar qualificação antes de notificar).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '20260123_seller_notified'
down_revision = '20260121_add_dashboard_config'
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
    Adiciona campo seller_notified_at na tabela leads.
    """

    # Adiciona seller_notified_at se não existir
    if not column_exists('leads', 'seller_notified_at'):
        op.add_column('leads', sa.Column('seller_notified_at', sa.DateTime(timezone=True), nullable=True))
        print("✅ Campo seller_notified_at adicionado à tabela leads")
    else:
        print("ℹ️ Campo seller_notified_at já existe na tabela leads")


def downgrade() -> None:
    """
    Remove campo seller_notified_at.
    """
    if column_exists('leads', 'seller_notified_at'):
        op.drop_column('leads', 'seller_notified_at')
        print("✅ Campo seller_notified_at removido da tabela leads")
