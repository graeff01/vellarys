"""add properties table for real estate

Revision ID: 20260129_add_properties
Revises: 20260129_add_proposals
Create Date: 2026-01-29 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260129_add_properties'
down_revision: Union[str, None] = '20260129_add_proposals'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create properties table for property matching."""

    op.create_table(
        'properties',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),

        # Basic Info
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('property_type', sa.String(50), nullable=False),
        # casa, apartamento, sobrado, terreno, sala_comercial, galpao

        # Location
        sa.Column('address', sa.String(500), nullable=False),
        sa.Column('neighborhood', sa.String(100), nullable=True),
        sa.Column('city', sa.String(100), nullable=False),
        sa.Column('state', sa.String(2), nullable=False),
        sa.Column('zip_code', sa.String(10), nullable=True),
        sa.Column('latitude', sa.Numeric(10, 8), nullable=True),
        sa.Column('longitude', sa.Numeric(11, 8), nullable=True),

        # Details
        sa.Column('size_sqm', sa.Numeric(10, 2), nullable=True),  # Tamanho em m²
        sa.Column('rooms', sa.Integer(), nullable=True),
        sa.Column('bathrooms', sa.Integer(), nullable=True),
        sa.Column('parking_spots', sa.Integer(), nullable=True),
        sa.Column('floor', sa.Integer(), nullable=True),  # Andar (para aptos)
        sa.Column('total_floors', sa.Integer(), nullable=True),  # Total de andares do prédio

        # Features (JSONB array)
        sa.Column('features', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        # ["piscina", "churrasqueira", "ar_condicionado", "varanda", "suite", "elevador"]

        # Values
        sa.Column('sale_price', sa.Numeric(15, 2), nullable=True),
        sa.Column('rent_price', sa.Numeric(15, 2), nullable=True),
        sa.Column('condo_fee', sa.Numeric(10, 2), nullable=True),
        sa.Column('iptu', sa.Numeric(10, 2), nullable=True),

        # Media
        sa.Column('images', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        # ["url1", "url2", "url3"]
        sa.Column('video_url', sa.String(500), nullable=True),
        sa.Column('virtual_tour_url', sa.String(500), nullable=True),

        # Status
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_available', sa.Boolean(), nullable=False, server_default='true'),

        # Metadata
        sa.Column('custom_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Constraints
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes for fast searching
    op.create_index('ix_properties_tenant_id', 'properties', ['tenant_id'])
    op.create_index('ix_properties_property_type', 'properties', ['property_type'])
    op.create_index('ix_properties_city', 'properties', ['city'])
    op.create_index('ix_properties_neighborhood', 'properties', ['neighborhood'])
    op.create_index('ix_properties_rooms', 'properties', ['rooms'])
    op.create_index('ix_properties_sale_price', 'properties', ['sale_price'])
    op.create_index('ix_properties_rent_price', 'properties', ['rent_price'])
    op.create_index('ix_properties_is_active', 'properties', ['is_active'])
    op.create_index('ix_properties_is_available', 'properties', ['is_available'])

    # Composite indexes for common queries
    op.create_index(
        'ix_properties_tenant_active_available',
        'properties',
        ['tenant_id', 'is_active', 'is_available']
    )
    op.create_index(
        'ix_properties_type_rooms_price',
        'properties',
        ['property_type', 'rooms', 'sale_price']
    )


def downgrade() -> None:
    """Drop properties table."""
    op.drop_index('ix_properties_type_rooms_price', table_name='properties')
    op.drop_index('ix_properties_tenant_active_available', table_name='properties')
    op.drop_index('ix_properties_is_available', table_name='properties')
    op.drop_index('ix_properties_is_active', table_name='properties')
    op.drop_index('ix_properties_rent_price', table_name='properties')
    op.drop_index('ix_properties_sale_price', table_name='properties')
    op.drop_index('ix_properties_rooms', table_name='properties')
    op.drop_index('ix_properties_neighborhood', table_name='properties')
    op.drop_index('ix_properties_city', table_name='properties')
    op.drop_index('ix_properties_property_type', table_name='properties')
    op.drop_index('ix_properties_tenant_id', table_name='properties')
    op.drop_table('properties')
