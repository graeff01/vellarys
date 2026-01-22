"""add conversation_summary field

Revision ID: 20260115_001
Revises: 20251217_001
Create Date: 2026-01-15 16:00:00

"""
from alembic import op
import sqlalchemy as sa

revision = '20260115_001'
down_revision = 'add_auth_features'  # after auth features
branch_labels = None
depends_on = None


def upgrade():
    # Adiciona campo conversation_summary ao modelo Lead
    op.add_column('leads', 
        sa.Column('conversation_summary', sa.Text(), nullable=True)
    )
    
    # Adiciona índice para performance
    op.create_index(
        'idx_leads_conversation_summary',
        'leads',
        ['tenant_id', 'conversation_summary'],
        postgresql_using='gin',
        postgresql_ops={'conversation_summary': 'gin_trgm_ops'}
    )


def downgrade():
    op.drop_index('idx_leads_conversation_summary', table_name='leads')
    op.drop_column('leads', 'conversation_summary')
