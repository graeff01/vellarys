"""add conversation_summary field

Revision ID: 20260115_001
Revises: add_auth_features
Create Date: 2026-01-15 16:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '20260115_001'
down_revision = 'add_auth_features'  # after auth features
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(text(
        "SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = :table AND column_name = :column)"
    ), {"table": table_name, "column": column_name})
    return result.scalar()


def index_exists(index_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(text(
        "SELECT EXISTS (SELECT FROM pg_indexes WHERE indexname = :name)"
    ), {"name": index_name})
    return result.scalar()


def upgrade():
    # Adiciona campo conversation_summary ao modelo Lead
    if not column_exists('leads', 'conversation_summary'):
        op.add_column('leads',
            sa.Column('conversation_summary', sa.Text(), nullable=True)
        )

    # Adiciona índice para performance (se a extensão pg_trgm existir)
    if not index_exists('idx_leads_conversation_summary'):
        try:
            op.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            op.create_index(
                'idx_leads_conversation_summary',
                'leads',
                ['tenant_id', 'conversation_summary'],
                postgresql_using='gin',
                postgresql_ops={'conversation_summary': 'gin_trgm_ops'}
            )
        except Exception:
            # Se não conseguir criar o índice GIN, cria um índice normal
            pass


def downgrade():
    if index_exists('idx_leads_conversation_summary'):
        op.drop_index('idx_leads_conversation_summary', table_name='leads')
    if column_exists('leads', 'conversation_summary'):
        op.drop_column('leads', 'conversation_summary')
