"""add appointments table

Revision ID: 20260126_add_appointments
Revises: 20260125_performance_metrics
Create Date: 2026-01-26

Adiciona tabela de agendamentos (appointments) para vendedores marcarem
visitas, ligações, demonstrações e outros compromissos com leads.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260126_add_appointments'
down_revision = '20260125_performance_metrics'
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    conn = op.get_bind()
    result = conn.execute(text(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :table)"
    ), {"table": table_name})
    return result.scalar()


def index_exists(index_name: str) -> bool:
    """Check if an index exists in the database."""
    conn = op.get_bind()
    result = conn.execute(text(
        "SELECT EXISTS (SELECT FROM pg_indexes WHERE indexname = :index)"
    ), {"index": index_name})
    return result.scalar()


def upgrade() -> None:
    """Criar tabela appointments e índices."""

    # Criar tabela appointments se não existir
    if not table_exists('appointments'):
        op.create_table(
            'appointments',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('lead_id', sa.Integer(), nullable=False),
            sa.Column('seller_id', sa.Integer(), nullable=True),  # SET NULL se seller deletado
            sa.Column('created_by', sa.Integer(), nullable=True),  # SET NULL se user deletado

            # Dados do agendamento
            sa.Column('title', sa.String(length=200), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('appointment_type', sa.String(length=50), nullable=False, server_default='visit'),

            # Data e hora
            sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('duration_minutes', sa.Integer(), nullable=False, server_default='60'),
            sa.Column('timezone', sa.String(length=50), nullable=False, server_default='America/Sao_Paulo'),

            # Localização (visitas presenciais)
            sa.Column('location', sa.String(length=500), nullable=True),
            sa.Column('location_lat', sa.DECIMAL(precision=10, scale=8), nullable=True),
            sa.Column('location_lng', sa.DECIMAL(precision=11, scale=8), nullable=True),

            # Status e confirmação
            sa.Column('status', sa.String(length=20), nullable=False, server_default='scheduled'),
            sa.Column('confirmed_by_lead', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),

            # Resultado (após conclusão)
            sa.Column('outcome', sa.String(length=50), nullable=True),
            sa.Column('outcome_notes', sa.Text(), nullable=True),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),

            # Notificações
            sa.Column('reminded_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('reminder_sent', sa.Boolean(), nullable=False, server_default='false'),

            # Metadata
            sa.Column('custom_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),

            # Primary Key
            sa.PrimaryKeyConstraint('id'),

            # Foreign Keys
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['seller_id'], ['sellers.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        )
        print("✅ Tabela 'appointments' criada com sucesso")
    else:
        print("ℹ️  Tabela 'appointments' já existe, pulando criação")

    # Criar índices
    indices = [
        ('ix_appointments_tenant_id', 'appointments', ['tenant_id']),
        ('ix_appointments_lead_id', 'appointments', ['lead_id']),
        ('ix_appointments_seller_id', 'appointments', ['seller_id']),
        ('ix_appointments_status', 'appointments', ['status']),
        ('ix_appointments_scheduled_at', 'appointments', ['scheduled_at']),
    ]

    for index_name, table_name, columns in indices:
        if not index_exists(index_name):
            op.create_index(index_name, table_name, columns)
            print(f"✅ Índice '{index_name}' criado")
        else:
            print(f"ℹ️  Índice '{index_name}' já existe")

    # Criar índices compostos para queries de calendário
    composite_indices = [
        ('ix_appointments_tenant_scheduled', 'appointments', ['tenant_id', 'scheduled_at']),
        ('ix_appointments_seller_scheduled', 'appointments', ['seller_id', 'scheduled_at']),
    ]

    for index_name, table_name, columns in composite_indices:
        if not index_exists(index_name):
            op.create_index(index_name, table_name, columns)
            print(f"✅ Índice composto '{index_name}' criado")
        else:
            print(f"ℹ️  Índice composto '{index_name}' já existe")


def downgrade() -> None:
    """Remover tabela appointments e índices."""

    # Remover índices
    indices = [
        'ix_appointments_seller_scheduled',
        'ix_appointments_tenant_scheduled',
        'ix_appointments_scheduled_at',
        'ix_appointments_status',
        'ix_appointments_seller_id',
        'ix_appointments_lead_id',
        'ix_appointments_tenant_id',
    ]

    for index_name in indices:
        if index_exists(index_name):
            op.drop_index(index_name, table_name='appointments')
            print(f"✅ Índice '{index_name}' removido")

    # Remover tabela
    if table_exists('appointments'):
        op.drop_table('appointments')
        print("✅ Tabela 'appointments' removida")
