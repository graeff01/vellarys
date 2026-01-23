"""add seller user link

Revision ID: 20260124_seller_user
Revises: 20260123_seller_notified
Create Date: 2026-01-24

Adiciona:
- Campo user_id em sellers (link para users)
- Permite corretor fazer login no CRM
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '20260124_seller_user'
down_revision = '20260123_seller_notified'
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
    Adiciona user_id em sellers para link com users.
    """

    # 1. Adiciona role "corretor" no enum UserRole se não existir
    try:
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'corretor'")
        print("✅ Role 'corretor' adicionado ao enum UserRole")
    except Exception as e:
        print(f"ℹ️ Role 'corretor' já existe ou erro: {e}")

    # 2. Adiciona coluna user_id em sellers
    if not column_exists('sellers', 'user_id'):
        op.add_column('sellers',
            sa.Column('user_id', sa.Integer(),
                      sa.ForeignKey('users.id', ondelete='SET NULL'),
                      nullable=True))
        op.create_index('ix_sellers_user_id', 'sellers', ['user_id'])
        print("✅ Campo user_id adicionado à tabela sellers")
    else:
        print("ℹ️ Campo user_id já existe na tabela sellers")


def downgrade() -> None:
    """
    Remove user_id de sellers.
    """
    if column_exists('sellers', 'user_id'):
        op.drop_index('ix_sellers_user_id', 'sellers')
        op.drop_column('sellers', 'user_id')
        print("✅ Campo user_id removido da tabela sellers")
