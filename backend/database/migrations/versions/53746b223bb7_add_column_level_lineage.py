"""add_column_level_lineage

Revision ID: 53746b223bb7
Revises: 03e4d60d721e
Create Date: 2026-06-13 17:06:02.481789

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '53746b223bb7'
down_revision: Union[str, Sequence[str], None] = '03e4d60d721e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'lineage_column_edges',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('source_node_id', sa.String(length=255), nullable=False),
        sa.Column('source_column', sa.String(length=255), nullable=False),
        sa.Column('target_node_id', sa.String(length=255), nullable=False),
        sa.Column('target_column', sa.String(length=255), nullable=False),
        sa.Column('edge_type', sa.String(length=50), nullable=False),
        sa.Column('valid_from', sa.DateTime(), nullable=False),
        sa.Column('valid_to', sa.DateTime(), nullable=True),
        sa.Column('transformation_rule', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['source_node_id'], ['lineage_nodes.node_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_node_id'], ['lineage_nodes.node_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_col_edges_source', 'lineage_column_edges', ['source_node_id', 'source_column'], unique=False)
    op.create_index('idx_col_edges_target', 'lineage_column_edges', ['target_node_id', 'target_column'], unique=False)
    op.create_index('idx_col_edges_valid_from_to', 'lineage_column_edges', ['valid_from', 'valid_to'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_col_edges_valid_from_to', table_name='lineage_column_edges')
    op.drop_index('idx_col_edges_target', table_name='lineage_column_edges')
    op.drop_index('idx_col_edges_source', table_name='lineage_column_edges')
    op.drop_table('lineage_column_edges')
