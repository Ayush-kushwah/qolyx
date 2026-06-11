"""add_lineage_tables

Revision ID: 03e4d60d721e
Revises: 334452378a87
Create Date: 2026-06-08 15:48:52.313347

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '03e4d60d721e'
down_revision: Union[str, Sequence[str], None] = '334452378a87'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create lineage_nodes table
    op.create_table(
        'lineage_nodes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('node_id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('schema', sa.String(length=255), nullable=False),
        sa.Column('database', sa.String(length=255), nullable=True),
        sa.Column('materialized_type', sa.String(length=50), nullable=True),
        sa.Column('owner', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('meta', sa.JSON(), nullable=True),
        sa.Column('trust_score', sa.Float(), nullable=True),
        sa.Column('last_updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lineage_nodes_node_id'), 'lineage_nodes', ['node_id'], unique=True)

    # 2. Create lineage_edges table
    op.create_table(
        'lineage_edges',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('source_node_id', sa.String(length=255), nullable=False),
        sa.Column('target_node_id', sa.String(length=255), nullable=False),
        sa.Column('edge_type', sa.String(length=50), nullable=False),
        sa.Column('valid_from', sa.DateTime(), nullable=False),
        sa.Column('valid_to', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['source_node_id'], ['lineage_nodes.node_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_node_id'], ['lineage_nodes.node_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_lineage_edges_source_target', 'lineage_edges', ['source_node_id', 'target_node_id'], unique=False)
    op.create_index('idx_lineage_edges_valid_from_to', 'lineage_edges', ['valid_from', 'valid_to'], unique=False)
    op.create_index(op.f('ix_lineage_edges_source_node_id'), 'lineage_edges', ['source_node_id'], unique=False)
    op.create_index(op.f('ix_lineage_edges_target_node_id'), 'lineage_edges', ['target_node_id'], unique=False)

    # 3. Create lineage_edge_history table
    op.create_table(
        'lineage_edge_history',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('source_node_id', sa.String(length=255), nullable=False),
        sa.Column('target_node_id', sa.String(length=255), nullable=False),
        sa.Column('edge_type', sa.String(length=50), nullable=False),
        sa.Column('valid_from', sa.DateTime(), nullable=False),
        sa.Column('valid_to', sa.DateTime(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_lineage_history_source_target', 'lineage_edge_history', ['source_node_id', 'target_node_id'], unique=False)
    op.create_index('idx_lineage_history_valid_from_to', 'lineage_edge_history', ['valid_from', 'valid_to'], unique=False)
    op.create_index(op.f('ix_lineage_edge_history_source_node_id'), 'lineage_edge_history', ['source_node_id'], unique=False)
    op.create_index(op.f('ix_lineage_edge_history_target_node_id'), 'lineage_edge_history', ['target_node_id'], unique=False)

    # 4. Conditional GIST index on PostgreSQL for temporal queries
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE INDEX gist_idx_lineage_history_range ON lineage_edge_history USING gist (tsrange(valid_from, valid_to))")


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS gist_idx_lineage_history_range")

    op.drop_index(op.f('ix_lineage_edge_history_target_node_id'), table_name='lineage_edge_history')
    op.drop_index(op.f('ix_lineage_edge_history_source_node_id'), table_name='lineage_edge_history')
    op.drop_index('idx_lineage_history_valid_from_to', table_name='lineage_edge_history')
    op.drop_index('idx_lineage_history_source_target', table_name='lineage_edge_history')
    op.drop_table('lineage_edge_history')

    op.drop_index(op.f('ix_lineage_edges_target_node_id'), table_name='lineage_edges')
    op.drop_index(op.f('ix_lineage_edges_source_node_id'), table_name='lineage_edges')
    op.drop_index('idx_lineage_edges_valid_from_to', table_name='lineage_edges')
    op.drop_index('idx_lineage_edges_source_target', table_name='lineage_edges')
    op.drop_table('lineage_edges')

    op.drop_index(op.f('ix_lineage_nodes_node_id'), table_name='lineage_nodes')
    op.drop_table('lineage_nodes')
