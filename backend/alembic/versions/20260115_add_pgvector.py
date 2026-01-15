"""add pgvector and property embeddings

Revision ID: 20260115_002
Revises: 20260115_001
Create Date: 2026-01-15 16:30:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260115_002'
down_revision = '20260115_001'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Ativa extensão pgvector
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # 2. Cria tabela de embeddings
    op.create_table(
        'property_embeddings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=False),  # 1536 dimensões (OpenAI)
        sa.Column('content_hash', sa.String(64), nullable=False),  # MD5/SHA do conteúdo
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_id', name='uq_property_embeddings_product_id')
    )
    
    # 3. Índices para performance
    op.create_index('idx_property_embeddings_tenant', 'property_embeddings', ['tenant_id'])
    
    # 4. Índice HNSW para busca vetorial (muito mais rápido que IVFFlat)
    # Sintaxe: CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)
    op.execute("""
        CREATE INDEX idx_property_embeddings_vector 
        ON property_embeddings 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade():
    op.drop_table('property_embeddings')
    op.execute('DROP EXTENSION IF EXISTS vector')
