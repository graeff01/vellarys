"""add ai quality tables

Revision ID: 20251217_001
Revises:
Create Date: 2025-12-17 12:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

revision = '20251217_001'
down_revision = None
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
    if not table_exists('ai_quality_logs'):
        op.create_table('ai_quality_logs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('lead_id', sa.Integer(), nullable=False),
            sa.Column('user_message', sa.Text(), nullable=False),
            sa.Column('ai_response', sa.Text(), nullable=False),
            sa.Column('validation_passed', sa.Boolean(), nullable=False),
            sa.Column('confidence_score', sa.Integer(), nullable=False),
            sa.Column('issues_detected', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column('action_taken', sa.String(length=20), nullable=False),
            sa.Column('context_available', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('response_time_ms', sa.Integer(), nullable=True),
            sa.Column('tokens_used', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )

    if not index_exists('idx_ai_quality_tenant_created'):
        op.create_index('idx_ai_quality_tenant_created', 'ai_quality_logs', ['tenant_id', 'created_at'])
    if not index_exists('idx_ai_quality_validation'):
        op.create_index('idx_ai_quality_validation', 'ai_quality_logs', ['validation_passed'])

    if not table_exists('ai_quality_metrics'):
        op.create_table('ai_quality_metrics',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('date', sa.DateTime(timezone=True), nullable=False),
            sa.Column('total_interactions', sa.Integer(), nullable=False),
            sa.Column('issues_detected', sa.Integer(), nullable=False),
            sa.Column('forced_handoffs', sa.Integer(), nullable=False),
            sa.Column('hallucinated_price_count', sa.Integer(), nullable=False),
            sa.Column('repetition_count', sa.Integer(), nullable=False),
            sa.Column('frustration_count', sa.Integer(), nullable=False),
            sa.Column('avg_confidence', sa.Integer(), nullable=False),
            sa.Column('avg_response_time_ms', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )

    if not index_exists('idx_ai_quality_metrics_tenant_date'):
        op.create_index('idx_ai_quality_metrics_tenant_date', 'ai_quality_metrics', ['tenant_id', 'date'])


def downgrade():
    if table_exists('ai_quality_metrics'):
        op.drop_table('ai_quality_metrics')
    if table_exists('ai_quality_logs'):
        op.drop_table('ai_quality_logs')
