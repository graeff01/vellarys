"""add commercial proposals for real estate

Revision ID: 20260129_add_proposals
Revises: 20260128_merge_heads
Create Date: 2026-01-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260129_add_proposals'
down_revision: Union[str, None] = '20260128_merge_heads'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create commercial_proposals table."""

    op.create_table(
        'commercial_proposals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('lead_id', sa.Integer(), nullable=False),
        sa.Column('seller_id', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),

        # Property Info (JSONB)
        sa.Column('property_info', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        # {
        #   "type": "apartamento",  # casa, apartamento, sobrado, terreno, sala_comercial
        #   "address": "Rua X, 123 - Zona Sul",
        #   "size": "80m²",
        #   "rooms": 3,
        #   "bathrooms": 2,
        #   "parking": 1,
        #   "features": ["piscina", "churrasqueira"],
        #   "images": ["url1", "url2"]
        # }

        # Values
        sa.Column('asked_value', sa.Numeric(15, 2), nullable=False),  # Valor pedido
        sa.Column('offered_value', sa.Numeric(15, 2), nullable=False),  # Valor oferecido
        sa.Column('final_value', sa.Numeric(15, 2), nullable=True),  # Valor final (se aceito)

        # Status
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        # pending, owner_analysis, owner_rejected, owner_accepted,
        # negotiating, closed, expired

        # Deadline
        sa.Column('deadline', sa.DateTime(timezone=True), nullable=True),

        # Timeline (JSONB array)
        sa.Column('timeline', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        # [
        #   {"date": "2026-01-15T10:30:00", "event": "lead_offered", "value": 450000, "note": "..."},
        #   {"date": "2026-01-15T14:20:00", "event": "owner_rejected", "note": "..."},
        #   {"date": "2026-01-15T15:00:00", "event": "lead_raised", "value": 460000},
        #   {"date": "2026-01-16T09:00:00", "event": "owner_accepted", "value": 460000}
        # ]

        # Notes
        sa.Column('notes', sa.Text(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),

        # Constraints
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['seller_id'], ['sellers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes
    op.create_index('ix_proposals_tenant_id', 'commercial_proposals', ['tenant_id'])
    op.create_index('ix_proposals_lead_id', 'commercial_proposals', ['lead_id'])
    op.create_index('ix_proposals_seller_id', 'commercial_proposals', ['seller_id'])
    op.create_index('ix_proposals_status', 'commercial_proposals', ['status'])
    op.create_index('ix_proposals_tenant_status', 'commercial_proposals', ['tenant_id', 'status'])
    op.create_index('ix_proposals_created_at', 'commercial_proposals', ['created_at'])


def downgrade() -> None:
    """Drop commercial_proposals table."""
    op.drop_index('ix_proposals_created_at', table_name='commercial_proposals')
    op.drop_index('ix_proposals_tenant_status', table_name='commercial_proposals')
    op.drop_index('ix_proposals_status', table_name='commercial_proposals')
    op.drop_index('ix_proposals_seller_id', table_name='commercial_proposals')
    op.drop_index('ix_proposals_lead_id', table_name='commercial_proposals')
    op.drop_index('ix_proposals_tenant_id', table_name='commercial_proposals')
    op.drop_table('commercial_proposals')
