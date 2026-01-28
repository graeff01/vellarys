"""merge appointments and entitlements heads

Revision ID: 20260128_merge_heads
Revises: 20260126_add_appointments, 20260128_add_entitlements
Create Date: 2026-01-28 19:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260128_merge_heads'
down_revision: Union[str, Sequence[str], None] = ('20260126_add_appointments', '20260128_add_entitlements')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge two branches - no changes needed."""
    pass


def downgrade() -> None:
    """Merge downgrade - no changes needed."""
    pass
