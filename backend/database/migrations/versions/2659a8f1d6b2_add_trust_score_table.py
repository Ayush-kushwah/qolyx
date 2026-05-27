"""add_trust_score_table

Revision ID: 2659a8f1d6b2
Revises: c99687724953
Create Date: 2026-05-25 15:19:47.252533

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2659a8f1d6b2'
down_revision: Union[str, Sequence[str], None] = 'c99687724953'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create table trust_scores
    op.create_table(
        'trust_scores',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('pipeline_run_id', sa.UUID(), nullable=False),
        sa.Column('table_name', sa.String(length=255), nullable=False),
        sa.Column('contract_penalty', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('freshness_penalty', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('volume_penalty', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('anomaly_penalty', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('dbt_penalty', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_penalty', sa.Integer(), nullable=False),
        sa.Column('trust_score', sa.Integer(), nullable=False),
        sa.Column('trust_score_status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. Add unique constraint on pipeline_run_id
    op.create_index(op.f('ix_trust_scores_pipeline_run_id'), 'trust_scores', ['pipeline_run_id'], unique=True)

    # 3. Add index on table_name
    op.create_index(op.f('ix_trust_scores_table_name'), 'trust_scores', ['table_name'], unique=False)

    # 4. Add index on created_at
    op.create_index(op.f('ix_trust_scores_created_at'), 'trust_scores', ['created_at'], unique=False)

    # 5. Add composite index on (table_name, created_at DESC)
    op.execute("CREATE INDEX idx_trust_scores_table_created ON trust_scores (table_name, created_at DESC)")


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Drop composite index idx_trust_scores_table_created
    op.execute("DROP INDEX idx_trust_scores_table_created")

    # 2. Drop other indexes
    op.drop_index(op.f('ix_trust_scores_created_at'), table_name='trust_scores')
    op.drop_index(op.f('ix_trust_scores_table_name'), table_name='trust_scores')
    op.drop_index(op.f('ix_trust_scores_pipeline_run_id'), table_name='trust_scores')

    # 3. Drop table
    op.drop_table('trust_scores')
