"""fix crm inbox columns

Revision ID: 20260124_fix_crm_inbox_columns
Revises: 20260124_handoff_mode
Create Date: 2026-01-24

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260124_fix_crm_inbox_columns'
down_revision = '20260124_handoff_mode'
branch_labels = None
depends_on = None


def upgrade():
    # Execute raw SQL to add all missing columns
    op.execute("""
        -- 1. Add attended_by column
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'leads' AND column_name = 'attended_by') THEN
                ALTER TABLE leads ADD COLUMN attended_by VARCHAR(20) DEFAULT 'ai';
            END IF;
        END $$;

        -- 2. Add seller_took_over_at column
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'leads' AND column_name = 'seller_took_over_at') THEN
                ALTER TABLE leads ADD COLUMN seller_took_over_at TIMESTAMPTZ;
            END IF;
        END $$;

        -- 3. Add sender_type column
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'messages' AND column_name = 'sender_type') THEN
                ALTER TABLE messages ADD COLUMN sender_type VARCHAR(20);
            END IF;
        END $$;

        -- 4. Add sender_user_id column
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'messages' AND column_name = 'sender_user_id') THEN
                ALTER TABLE messages ADD COLUMN sender_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
            END IF;
        END $$;

        -- 5. Add user_id column to sellers
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'sellers' AND column_name = 'user_id') THEN
                ALTER TABLE sellers ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
            END IF;
        END $$;

        -- 6. Backfill sender_type
        UPDATE messages
        SET sender_type = CASE
            WHEN role = 'assistant' THEN 'ai'
            WHEN role = 'system' THEN 'system'
            ELSE NULL
        END
        WHERE sender_type IS NULL;
    """)


def downgrade():
    # Remove columns in reverse order
    op.execute("""
        ALTER TABLE sellers DROP COLUMN IF EXISTS user_id;
        ALTER TABLE messages DROP COLUMN IF EXISTS sender_user_id;
        ALTER TABLE messages DROP COLUMN IF EXISTS sender_type;
        ALTER TABLE leads DROP COLUMN IF EXISTS seller_took_over_at;
        ALTER TABLE leads DROP COLUMN IF EXISTS attended_by;
    """)
