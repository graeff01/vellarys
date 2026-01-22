"""add pgvector and property embeddings

Revision ID: 20260115_002
Revises: 20260115_001
Create Date: 2026-01-15 16:30:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

revision = '20260115_002'
down_revision = '20260115_001'
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


def upgrade():
    # 1. Ativa extensão pgvector
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # 2. Cria tabela de embeddings
    if not table_exists('property_embeddings'):
        op.create_table(
            'property_embeddings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('product_id', sa.Integer(), nullable=False),
            sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=False),
            sa.Column('content_hash', sa.String(64), nullable=False),
            sa.Column('embedding_metadata', postgresql.JSONB(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('product_id', name='uq_property_embeddings_product_id')
        )

    # 3. Índices para performance
    if not index_exists('idx_property_embeddings_tenant'):
        op.create_index('idx_property_embeddings_tenant', 'property_embeddings', ['tenant_id'])

    # 4. Índice HNSW para busca vetorial
    if not index_exists('idx_property_embeddings_vector'):
        op.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_property_embeddings_vector
            ON property_embeddings
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """))


def downgrade():
    if table_exists('property_embeddings'):
        op.drop_table('property_embeddings')
    op.execute('DROP EXTENSION IF EXISTS vector')
