"""create idempotency table

Revision ID: 34b9aa1ef579
Revises: c9e3a36cfce2
Create Date: 2026-08-08 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '34b9aa1ef579'
down_revision: Union[str, Sequence[str], None] = 'c9e3a36cfce2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # minimal placeholder: originally created idempotency table; left intentionally empty
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
