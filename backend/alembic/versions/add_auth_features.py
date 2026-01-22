"""add refresh tokens and password reset

Revision ID: add_auth_features
Revises: 20251217_001
Create Date: 2026-01-14 12:50:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = 'add_auth_features'
down_revision = '20251217_001'  # after base migration
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
    # Criar tabela refresh_tokens
    if not table_exists('refresh_tokens'):
        op.create_table(
            'refresh_tokens',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('token', sa.String(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('revoked', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        print("Created table: refresh_tokens")

    if not index_exists('ix_refresh_tokens_token'):
        op.create_index(op.f('ix_refresh_tokens_token'), 'refresh_tokens', ['token'], unique=True)
    if not index_exists('ix_refresh_tokens_user_id'):
        op.create_index(op.f('ix_refresh_tokens_user_id'), 'refresh_tokens', ['user_id'], unique=False)

    # Criar tabela password_reset_tokens
    if not table_exists('password_reset_tokens'):
        op.create_table(
            'password_reset_tokens',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('token', sa.String(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('used', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        print("Created table: password_reset_tokens")

    if not index_exists('ix_password_reset_tokens_token'):
        op.create_index(op.f('ix_password_reset_tokens_token'), 'password_reset_tokens', ['token'], unique=True)
    if not index_exists('ix_password_reset_tokens_user_id'):
        op.create_index(op.f('ix_password_reset_tokens_user_id'), 'password_reset_tokens', ['user_id'], unique=False)

    # Criar tabela message_templates
    if not table_exists('message_templates'):
        op.create_table(
            'message_templates',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('shortcut', sa.String(length=50), nullable=True),
            sa.Column('category', sa.String(length=50), nullable=True),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        print("Created table: message_templates")

    if not index_exists('ix_message_templates_tenant_id'):
        op.create_index(op.f('ix_message_templates_tenant_id'), 'message_templates', ['tenant_id'], unique=False)
    if not index_exists('ix_message_templates_shortcut'):
        op.create_index(op.f('ix_message_templates_shortcut'), 'message_templates', ['shortcut'], unique=False)


def downgrade() -> None:
    if index_exists('ix_message_templates_shortcut'):
        op.drop_index(op.f('ix_message_templates_shortcut'), table_name='message_templates')
    if index_exists('ix_message_templates_tenant_id'):
        op.drop_index(op.f('ix_message_templates_tenant_id'), table_name='message_templates')
    if table_exists('message_templates'):
        op.drop_table('message_templates')

    if index_exists('ix_password_reset_tokens_user_id'):
        op.drop_index(op.f('ix_password_reset_tokens_user_id'), table_name='password_reset_tokens')
    if index_exists('ix_password_reset_tokens_token'):
        op.drop_index(op.f('ix_password_reset_tokens_token'), table_name='password_reset_tokens')
    if table_exists('password_reset_tokens'):
        op.drop_table('password_reset_tokens')

    if index_exists('ix_refresh_tokens_user_id'):
        op.drop_index(op.f('ix_refresh_tokens_user_id'), table_name='refresh_tokens')
    if index_exists('ix_refresh_tokens_token'):
        op.drop_index(op.f('ix_refresh_tokens_token'), table_name='refresh_tokens')
    if table_exists('refresh_tokens'):
        op.drop_table('refresh_tokens')
