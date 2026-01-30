"""add phoenix engine fields to leads

Revision ID: 20260130_phoenix_fields
Revises: 20260128_merge_heads
Create Date: 2026-01-30

Adiciona campos do Phoenix Engine para reativação inteligente de leads inativos.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '20260130_phoenix_fields'
down_revision = '20260128_merge_heads'
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
    Adiciona campos do Phoenix Engine na tabela leads.
    """

    # phoenix_status
    if not column_exists('leads', 'phoenix_status'):
        op.add_column('leads', sa.Column('phoenix_status', sa.String(20), nullable=True, server_default='none'))
        print("✅ Campo phoenix_status adicionado à tabela leads")
    else:
        print("ℹ️ Campo phoenix_status já existe na tabela leads")

    # phoenix_attempts
    if not column_exists('leads', 'phoenix_attempts'):
        op.add_column('leads', sa.Column('phoenix_attempts', sa.Integer(), nullable=False, server_default='0'))
        print("✅ Campo phoenix_attempts adicionado à tabela leads")
    else:
        print("ℹ️ Campo phoenix_attempts já existe na tabela leads")

    # last_phoenix_at
    if not column_exists('leads', 'last_phoenix_at'):
        op.add_column('leads', sa.Column('last_phoenix_at', sa.DateTime(timezone=True), nullable=True))
        print("✅ Campo last_phoenix_at adicionado à tabela leads")
    else:
        print("ℹ️ Campo last_phoenix_at já existe na tabela leads")

    # phoenix_interest_score
    if not column_exists('leads', 'phoenix_interest_score'):
        op.add_column('leads', sa.Column('phoenix_interest_score', sa.Integer(), nullable=False, server_default='0'))
        print("✅ Campo phoenix_interest_score adicionado à tabela leads")
    else:
        print("ℹ️ Campo phoenix_interest_score já existe na tabela leads")

    # phoenix_potential_commission
    if not column_exists('leads', 'phoenix_potential_commission'):
        op.add_column('leads', sa.Column('phoenix_potential_commission', sa.Float(), nullable=True))
        print("✅ Campo phoenix_potential_commission adicionado à tabela leads")
    else:
        print("ℹ️ Campo phoenix_potential_commission já existe na tabela leads")

    # phoenix_ai_analysis
    if not column_exists('leads', 'phoenix_ai_analysis'):
        op.add_column('leads', sa.Column('phoenix_ai_analysis', sa.Text(), nullable=True))
        print("✅ Campo phoenix_ai_analysis adicionado à tabela leads")
    else:
        print("ℹ️ Campo phoenix_ai_analysis já existe na tabela leads")

    # phoenix_original_seller_id
    if not column_exists('leads', 'phoenix_original_seller_id'):
        op.add_column('leads', sa.Column('phoenix_original_seller_id', sa.Integer(), nullable=True))
        # Adiciona foreign key
        op.create_foreign_key(
            'fk_leads_phoenix_original_seller',
            'leads',
            'sellers',
            ['phoenix_original_seller_id'],
            ['id'],
            ondelete='SET NULL'
        )
        print("✅ Campo phoenix_original_seller_id adicionado à tabela leads")
    else:
        print("ℹ️ Campo phoenix_original_seller_id já existe na tabela leads")


def downgrade() -> None:
    """
    Remove campos do Phoenix Engine.
    """

    # Remove foreign key primeiro
    if column_exists('leads', 'phoenix_original_seller_id'):
        op.drop_constraint('fk_leads_phoenix_original_seller', 'leads', type_='foreignkey')
        op.drop_column('leads', 'phoenix_original_seller_id')
        print("✅ Campo phoenix_original_seller_id removido da tabela leads")

    if column_exists('leads', 'phoenix_ai_analysis'):
        op.drop_column('leads', 'phoenix_ai_analysis')
        print("✅ Campo phoenix_ai_analysis removido da tabela leads")

    if column_exists('leads', 'phoenix_potential_commission'):
        op.drop_column('leads', 'phoenix_potential_commission')
        print("✅ Campo phoenix_potential_commission removido da tabela leads")

    if column_exists('leads', 'phoenix_interest_score'):
        op.drop_column('leads', 'phoenix_interest_score')
        print("✅ Campo phoenix_interest_score removido da tabela leads")

    if column_exists('leads', 'last_phoenix_at'):
        op.drop_column('leads', 'last_phoenix_at')
        print("✅ Campo last_phoenix_at removido da tabela leads")

    if column_exists('leads', 'phoenix_attempts'):
        op.drop_column('leads', 'phoenix_attempts')
        print("✅ Campo phoenix_attempts removido da tabela leads")

    if column_exists('leads', 'phoenix_status'):
        op.drop_column('leads', 'phoenix_status')
        print("✅ Campo phoenix_status removido da tabela leads")
