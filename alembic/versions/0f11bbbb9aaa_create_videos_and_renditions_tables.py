"""create videos and renditions tables

Revision ID: 0f11bbbb9aaa
Revises: 455d974ed295
Create Date: 2026-06-11 20:23:58.476411

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0f11bbbb9aaa"
down_revision: Union[str, Sequence[str], None] = "455d974ed295"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
