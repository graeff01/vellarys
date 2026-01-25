"""add performance metrics

Revision ID: 20260125_performance_metrics
Revises: 20260125_response_templates
Create Date: 2026-01-25

Adiciona campos para métricas de performance e SLA.
Calcula tempo de resposta, conversão, engajamento.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '20260125_performance_metrics'
down_revision = '20260125_response_templates'
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in the database."""
    conn = op.get_bind()
    result = conn.execute(text(
        "SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = :table AND column_name = :column)"
    ), {"table": table_name, "column": column_name})
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
    Adiciona campos de métricas de performance.
    """

    # 1. Primeira resposta
    if not column_exists('leads', 'first_response_at'):
        op.add_column('leads',
            sa.Column('first_response_at', sa.DateTime(timezone=True), nullable=True))
        print("✅ Campo first_response_at adicionado")
    else:
        print("ℹ️ Campo first_response_at já existe")

    if not column_exists('leads', 'first_response_time_seconds'):
        op.add_column('leads',
            sa.Column('first_response_time_seconds', sa.Integer(), server_default='0', nullable=False))
        print("✅ Campo first_response_time_seconds adicionado")
    else:
        print("ℹ️ Campo first_response_time_seconds já existe")

    # 2. Última mensagem do vendedor
    if not column_exists('leads', 'last_seller_message_at'):
        op.add_column('leads',
            sa.Column('last_seller_message_at', sa.DateTime(timezone=True), nullable=True))
        print("✅ Campo last_seller_message_at adicionado")
    else:
        print("ℹ️ Campo last_seller_message_at já existe")

    # 3. Última mensagem do lead
    if not column_exists('leads', 'last_lead_message_at'):
        op.add_column('leads',
            sa.Column('last_lead_message_at', sa.DateTime(timezone=True), nullable=True))
        print("✅ Campo last_lead_message_at adicionado")
    else:
        print("ℹ️ Campo last_lead_message_at já existe")

    # 4. Contadores
    if not column_exists('leads', 'total_seller_messages'):
        op.add_column('leads',
            sa.Column('total_seller_messages', sa.Integer(), server_default='0', nullable=False))
        print("✅ Campo total_seller_messages adicionado")
    else:
        print("ℹ️ Campo total_seller_messages já existe")

    if not column_exists('leads', 'total_lead_messages'):
        op.add_column('leads',
            sa.Column('total_lead_messages', sa.Integer(), server_default='0', nullable=False))
        print("✅ Campo total_lead_messages adicionado")
    else:
        print("ℹ️ Campo total_lead_messages já existe")

    # 5. Início da conversa (quando lead enviou primeira mensagem)
    if not column_exists('leads', 'conversation_started_at'):
        op.add_column('leads',
            sa.Column('conversation_started_at', sa.DateTime(timezone=True), nullable=True))
        print("✅ Campo conversation_started_at adicionado")
    else:
        print("ℹ️ Campo conversation_started_at já existe")

    # 6. Índice para queries de SLA/performance
    if not index_exists('ix_leads_response_time'):
        op.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_leads_response_time
            ON leads(tenant_id, first_response_time_seconds)
            WHERE first_response_time_seconds IS NOT NULL AND first_response_time_seconds > 0
        """))
        print("✅ Índice parcial ix_leads_response_time criado")


def downgrade() -> None:
    """
    Remove campos de métricas.
    """
    if index_exists('ix_leads_response_time'):
        op.drop_index('ix_leads_response_time', 'leads')
        print("✅ Índice ix_leads_response_time removido")

    if column_exists('leads', 'conversation_started_at'):
        op.drop_column('leads', 'conversation_started_at')
        print("✅ Campo conversation_started_at removido")

    if column_exists('leads', 'total_lead_messages'):
        op.drop_column('leads', 'total_lead_messages')
        print("✅ Campo total_lead_messages removido")

    if column_exists('leads', 'total_seller_messages'):
        op.drop_column('leads', 'total_seller_messages')
        print("✅ Campo total_seller_messages removido")

    if column_exists('leads', 'last_lead_message_at'):
        op.drop_column('leads', 'last_lead_message_at')
        print("✅ Campo last_lead_message_at removido")

    if column_exists('leads', 'last_seller_message_at'):
        op.drop_column('leads', 'last_seller_message_at')
        print("✅ Campo last_seller_message_at removido")

    if column_exists('leads', 'first_response_time_seconds'):
        op.drop_column('leads', 'first_response_time_seconds')
        print("✅ Campo first_response_time_seconds removido")

    if column_exists('leads', 'first_response_at'):
        op.drop_column('leads', 'first_response_at')
        print("✅ Campo first_response_at removido")
