"""add_system_settings_table

Revision ID: 8442682cd3a8
Revises: 5eb63eab283a
Create Date: 2026-05-28 22:24:07.045320

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8442682cd3a8'
down_revision: Union[str, Sequence[str], None] = '5eb63eab283a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('system_settings',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('key', sa.String(length=255), nullable=False),
    sa.Column('value', sa.Text(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    # Add index on key column for faster lookups
    op.create_index('ix_system_settings_key', 'system_settings', ['key'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_system_settings_key', table_name='system_settings')
    op.drop_table('system_settings')
