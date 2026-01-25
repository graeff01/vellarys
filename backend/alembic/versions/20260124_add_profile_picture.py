"""add profile_picture_url to leads

Revision ID: 20260124_profile_picture
Revises: 20260124_fix_crm_inbox_columns
Create Date: 2026-01-24

Adiciona campo profile_picture_url para armazenar foto de perfil do WhatsApp.
Permite exibir avatares reais dos leads no CRM Inbox.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '20260124_profile_picture'
down_revision = '20260124_fix_crm_inbox_columns'
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
    Adiciona campo profile_picture_url na tabela leads.
    """

    # Adiciona profile_picture_url se não existir
    if not column_exists('leads', 'profile_picture_url'):
        op.add_column('leads', sa.Column('profile_picture_url', sa.String(500), nullable=True))
        print("✅ Campo profile_picture_url adicionado à tabela leads")
    else:
        print("ℹ️ Campo profile_picture_url já existe na tabela leads")


def downgrade() -> None:
    """
    Remove campo profile_picture_url.
    """
    if column_exists('leads', 'profile_picture_url'):
        op.drop_column('leads', 'profile_picture_url')
        print("✅ Campo profile_picture_url removido da tabela leads")
