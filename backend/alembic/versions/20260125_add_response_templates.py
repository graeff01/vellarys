"""add response templates

Revision ID: 20260125_response_templates
Revises: 20260125_handoff_history
Create Date: 2026-01-25

Cria tabela de templates de respostas rápidas.
Permite corretores criar e reutilizar mensagens com variáveis.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '20260125_response_templates'
down_revision = '20260125_handoff_history'
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    conn = op.get_bind()
    result = conn.execute(text(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :name)"
    ), {"name": table_name})
    return result.scalar()


def index_exists(index_name: str) -> bool:
    """Check if an index exists in the database."""
    conn = op.get_bind()
    result = conn.execute(text(
        "SELECT EXISTS (SELECT FROM pg_indexes WHERE indexname = :name)"
    ), {"name": index_name})
    return result.scalar()


def upgrade() -> None:
    """
    Cria tabela de templates de respostas.
    """

    if not table_exists('response_templates'):
        op.create_table(
            'response_templates',
            # Primary Key
            sa.Column('id', sa.Integer(), nullable=False),

            # Foreign Keys
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('created_by_user_id', sa.Integer(), nullable=True),

            # Template data
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('shortcut', sa.String(20), nullable=True),  # Ex: /saudacao, /objecao
            sa.Column('content', sa.Text(), nullable=False),       # Com {{variables}}
            sa.Column('category', sa.String(50), nullable=True),   # Ex: saudacao, objecao, despedida

            # Metadata
            sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('usage_count', sa.Integer(), server_default='0', nullable=False),

            # Timestamps
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

            # Constraints
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )
        print("✅ Tabela response_templates criada")
    else:
        print("ℹ️ Tabela response_templates já existe")

    # Índices
    if not index_exists('ix_templates_tenant'):
        op.create_index('ix_templates_tenant', 'response_templates', ['tenant_id', 'is_active'])
        print("✅ Índice ix_templates_tenant criado")

    if not index_exists('ix_templates_shortcut'):
        op.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_templates_shortcut
            ON response_templates(tenant_id, shortcut)
            WHERE shortcut IS NOT NULL
        """))
        print("✅ Índice parcial ix_templates_shortcut criado")

    if not index_exists('ix_templates_category'):
        op.create_index('ix_templates_category', 'response_templates', ['tenant_id', 'category'])
        print("✅ Índice ix_templates_category criado")


def downgrade() -> None:
    """
    Remove tabela de response_templates.
    """
    if index_exists('ix_templates_category'):
        op.drop_index('ix_templates_category', 'response_templates')
        print("✅ Índice ix_templates_category removido")

    if index_exists('ix_templates_shortcut'):
        op.drop_index('ix_templates_shortcut', 'response_templates')
        print("✅ Índice ix_templates_shortcut removido")

    if index_exists('ix_templates_tenant'):
        op.drop_index('ix_templates_tenant', 'response_templates')
        print("✅ Índice ix_templates_tenant removido")

    if table_exists('response_templates'):
        op.drop_table('response_templates')
        print("✅ Tabela response_templates removida")
