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

# revision identifiers, used by Alembic.
revision = '20260121_knowledge_embeddings'
down_revision = '20260121_update_plans'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Cria tabela knowledge_embeddings para RAG de FAQ/documentos.

    Estrutura:
    - source_type: Tipo da fonte (faq, document, rule, policy)
    - source_id: ID da fonte original (para atualização/exclusão)
    - title: Título/Pergunta (para FAQ)
    - content: Conteúdo/Resposta
    - embedding: Vetor de 1536 dimensões (OpenAI text-embedding-3-small)
    - content_hash: Hash MD5 para detectar mudanças
    - metadata: Dados extras (categoria, tags, etc)
    """

    op.create_table(
        'knowledge_embeddings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),

        # Tipo e identificação da fonte
        sa.Column('source_type', sa.String(50), nullable=False),  # 'faq', 'document', 'rule', 'policy'
        sa.Column('source_id', sa.String(100), nullable=True),  # ID único da fonte

        # Conteúdo
        sa.Column('title', sa.String(500), nullable=True),  # Pergunta/Título
        sa.Column('content', sa.Text(), nullable=False),  # Resposta/Conteúdo

        # Embedding vetorial (1536 dimensões - OpenAI text-embedding-3-small)
        sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=False),

        # Hash para detectar mudanças (evita regenerar embedding desnecessariamente)
        sa.Column('content_hash', sa.String(64), nullable=False),

        # Metadata adicional (categoria, tags, prioridade, etc)
        sa.Column('metadata', postgresql.JSONB(), nullable=True),

        # Status
        sa.Column('active', sa.Boolean(), server_default='true', nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Foreign keys
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),

        # Primary key
        sa.PrimaryKeyConstraint('id'),
    )

    # Índice para buscar por tenant
    op.create_index(
        'idx_knowledge_embeddings_tenant',
        'knowledge_embeddings',
        ['tenant_id']
    )

    # Índice para buscar por tenant + tipo de fonte
    op.create_index(
        'idx_knowledge_embeddings_tenant_source',
        'knowledge_embeddings',
        ['tenant_id', 'source_type']
    )

    # Índice para buscar por tenant + source_id (para atualizações)
    op.create_index(
        'idx_knowledge_embeddings_tenant_source_id',
        'knowledge_embeddings',
        ['tenant_id', 'source_type', 'source_id']
    )

    # Índice HNSW para busca vetorial rápida
    # HNSW é muito mais rápido que IVFFlat para buscas (~1ms em 100k registros)
    # Parâmetros:
    # - m: número de conexões por nó (16 é bom para 1536 dimensões)
    # - ef_construction: qualidade da construção (64 é bom balanço)
    op.execute("""
        CREATE INDEX idx_knowledge_embeddings_vector
        ON knowledge_embeddings
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    """Remove tabela knowledge_embeddings."""
    op.drop_table('knowledge_embeddings')
