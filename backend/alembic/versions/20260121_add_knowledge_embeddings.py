"""add knowledge embeddings table for RAG

Revision ID: 20260121_knowledge_embeddings
Revises: 20260121_update_plans
Create Date: 2026-01-21

Adiciona tabela para armazenar embeddings de FAQ, documentos e regras de negócio.
Permite busca semântica (RAG) na base de conhecimento do tenant.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '20260121_knowledge_embeddings'
down_revision = '20260121_update_plans'
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(text(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :name)"
    ), {"name": table_name})
    return result.scalar()


def index_exists(index_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(text(
        "SELECT EXISTS (SELECT FROM pg_indexes WHERE indexname = :name)"
    ), {"name": index_name})
    return result.scalar()


def upgrade() -> None:
    """
    Cria tabela knowledge_embeddings para RAG de FAQ/documentos.
    """
    if not table_exists('knowledge_embeddings'):
        op.create_table(
            'knowledge_embeddings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('source_type', sa.String(50), nullable=False),
            sa.Column('source_id', sa.String(100), nullable=True),
            sa.Column('title', sa.String(500), nullable=True),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=False),
            sa.Column('content_hash', sa.String(64), nullable=False),
            sa.Column('embedding_metadata', postgresql.JSONB(), nullable=True),
            sa.Column('active', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )

    # Índices
    if not index_exists('idx_knowledge_embeddings_tenant'):
        op.create_index('idx_knowledge_embeddings_tenant', 'knowledge_embeddings', ['tenant_id'])

    if not index_exists('idx_knowledge_embeddings_tenant_source'):
        op.create_index('idx_knowledge_embeddings_tenant_source', 'knowledge_embeddings', ['tenant_id', 'source_type'])

    if not index_exists('idx_knowledge_embeddings_tenant_source_id'):
        op.create_index('idx_knowledge_embeddings_tenant_source_id', 'knowledge_embeddings', ['tenant_id', 'source_type', 'source_id'])

    # Índice HNSW para busca vetorial
    if not index_exists('idx_knowledge_embeddings_vector'):
        op.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_knowledge_embeddings_vector
            ON knowledge_embeddings
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """))


def downgrade() -> None:
    """Remove tabela knowledge_embeddings."""
    if table_exists('knowledge_embeddings'):
        op.drop_table('knowledge_embeddings')
