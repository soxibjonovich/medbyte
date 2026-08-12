"""add staff role

Revision ID: a1b2c3d4e5f6
Revises: 9f2b1c4e7d83
Create Date: 2026-08-12 08:55:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '9f2b1c4e7d83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'staff'")


def downgrade() -> None:
    """Downgrade schema."""
    pass
