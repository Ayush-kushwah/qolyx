"""add_llm_providers_table

Revision ID: afe1b31035b2
Revises: 68f3042fae7a
Create Date: 2026-06-16 10:37:53.485952

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'afe1b31035b2'
down_revision: Union[str, Sequence[str], None] = '68f3042fae7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('user_llm_providers',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('provider_type', sa.String(length=100), nullable=False),
    sa.Column('base_url', sa.String(length=500), nullable=False),
    sa.Column('model_name', sa.String(length=255), nullable=False),
    sa.Column('encrypted_api_key', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('priority', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('user_llm_providers')

