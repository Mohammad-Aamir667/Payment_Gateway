"""create paymentstatus type

Revision ID: a1b2c3d4e5f6
Revises: 4bba8b572627
Create Date: 2026-08-09 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '4bba8b572627'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    paymentstatus = postgresql.ENUM('PROCESSING', 'SUCCESS', 'FAILED', name='paymentstatus')
    paymentstatus.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    """Downgrade schema."""
    paymentstatus = postgresql.ENUM('PROCESSING', 'SUCCESS', 'FAILED', name='paymentstatus')
    paymentstatus.drop(op.get_bind(), checkfirst=True)
