"""add_anomaly_tables

Revision ID: c99687724953
Revises: 1db07a29bbe2
Create Date: 2026-05-24 16:22:33.440475

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c99687724953'
down_revision: Union[str, Sequence[str], None] = '1db07a29bbe2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('anomaly_baselines',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('table_name', sa.String(length=255), nullable=False),
    sa.Column('metric_name', sa.String(length=255), nullable=False),
    sa.Column('feature_columns', sa.JSON(), nullable=False),
    sa.Column('mean', sa.Float(), nullable=False),
    sa.Column('std_dev', sa.Float(), nullable=False),
    sa.Column('model_name', sa.String(length=100), nullable=True),
    sa.Column('feature_importance', sa.JSON(), nullable=True),
    sa.Column('isolation_forest_params', sa.JSON(), nullable=True),
    sa.Column('training_run_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('last_trained_at', sa.DateTime(), nullable=False),
    sa.Column('decay_factor', sa.Float(), server_default='0.95', nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('anomaly_detections',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('pipeline_run_id', sa.UUID(), nullable=False),
    sa.Column('table_name', sa.String(length=255), nullable=False),
    sa.Column('anomaly_type', sa.String(length=50), nullable=False),
    sa.Column('anomaly_score', sa.Float(), nullable=False),
    sa.Column('anomaly_penalty', sa.Integer(), nullable=False),
    sa.Column('feature_values', sa.JSON(), nullable=True),
    sa.Column('explanation', sa.Text(), nullable=True),
    sa.Column('is_acknowledged', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('is_false_positive', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('last_alerted_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_anomaly_detections_pipeline_run_id'), 'anomaly_detections', ['pipeline_run_id'], unique=False)
    op.create_index('ix_anomaly_detections_table_created', 'anomaly_detections', ['table_name', 'created_at'], unique=False)
    
    op.create_table('anomaly_feedback',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('anomaly_detection_id', sa.UUID(), nullable=False),
    sa.Column('feedback_type', sa.String(length=20), nullable=False),
    sa.Column('user_notes', sa.Text(), nullable=True),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['anomaly_detection_id'], ['anomaly_detections.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_anomaly_feedback_detection_id', 'anomaly_feedback', ['anomaly_detection_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_anomaly_feedback_detection_id', table_name='anomaly_feedback')
    op.drop_table('anomaly_feedback')
    op.drop_index('ix_anomaly_detections_table_created', table_name='anomaly_detections')
    op.drop_index(op.f('ix_anomaly_detections_pipeline_run_id'), table_name='anomaly_detections')
    op.drop_table('anomaly_detections')
    op.drop_table('anomaly_baselines')
