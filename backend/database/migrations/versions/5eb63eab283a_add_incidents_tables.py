"""add_incidents_tables

Revision ID: 5eb63eab283a
Revises: 2659a8f1d6b2
Create Date: 2026-05-27 18:55:11.544268

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5eb63eab283a'
down_revision: Union[str, Sequence[str], None] = '2659a8f1d6b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create config, policy, and rotation tables
    op.create_table('alert_configs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('channel_type', sa.String(length=20), nullable=False),
    sa.Column('webhook_url', sa.String(length=500), nullable=True),
    sa.Column('email_config', sa.JSON(), nullable=True),
    sa.Column('telegram_bot_token', sa.String(length=255), nullable=True),
    sa.Column('telegram_chat_id', sa.String(length=255), nullable=True),
    sa.Column('severity_threshold', sa.String(length=20), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('escalation_policies',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('severity', sa.String(length=20), nullable=False),
    sa.Column('timeout_minutes', sa.Integer(), nullable=False),
    sa.Column('target_type', sa.String(length=20), nullable=False),
    sa.Column('target_identifier', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('severity')
    )
    op.create_table('oncall_rotations',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('team_name', sa.String(length=255), nullable=False),
    sa.Column('members', sa.JSON(), nullable=False),
    sa.Column('current_index', sa.Integer(), nullable=False),
    sa.Column('rotation_type', sa.String(length=20), nullable=False),
    sa.Column('last_rotated_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    
    # Create incidents table
    op.create_table('incidents',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('trust_score_id', sa.UUID(), nullable=True),
    sa.Column('pipeline_run_id', sa.UUID(), nullable=False),
    sa.Column('table_name', sa.String(length=255), nullable=False),
    sa.Column('severity', sa.String(length=20), nullable=False),
    sa.Column('state', sa.String(length=20), nullable=False),
    sa.Column('assigned_to', sa.String(length=255), nullable=True),
    sa.Column('assigned_team', sa.String(length=255), nullable=True),
    sa.Column('title', sa.String(length=500), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
    sa.Column('resolved_at', sa.DateTime(), nullable=True),
    sa.Column('closed_at', sa.DateTime(), nullable=True),
    sa.Column('resolution_notes', sa.Text(), nullable=True),
    sa.Column('escalated_at', sa.DateTime(), nullable=True),
    sa.Column('escalation_level', sa.Integer(), nullable=False),
    sa.Column('muted_until', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['trust_score_id'], ['trust_scores.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    
    # Indexes on incidents
    op.create_index('idx_incidents_severity_state_created', 'incidents', ['severity', 'state', 'created_at'], unique=False)
    op.create_index(op.f('ix_incidents_created_at'), 'incidents', ['created_at'], unique=False)
    op.create_index(op.f('ix_incidents_pipeline_run_id'), 'incidents', ['pipeline_run_id'], unique=False)
    op.create_index(op.f('ix_incidents_severity'), 'incidents', ['severity'], unique=False)
    op.create_index(op.f('ix_incidents_state'), 'incidents', ['state'], unique=False)
    op.create_index(op.f('ix_incidents_table_name'), 'incidents', ['table_name'], unique=False)
    op.create_index(op.f('ix_incidents_trust_score_id'), 'incidents', ['trust_score_id'], unique=False)
    
    # Create incident comments
    op.create_table('incident_comments',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('incident_id', sa.UUID(), nullable=False),
    sa.Column('comment', sa.Text(), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['incident_id'], ['incidents.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_incident_comments_incident_id'), 'incident_comments', ['incident_id'], unique=False)
    
    # Create incident RCAs
    op.create_table('incident_rcas',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('incident_id', sa.UUID(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('summary', sa.Text(), nullable=False),
    sa.Column('root_cause', sa.Text(), nullable=False),
    sa.Column('contributing_factors', sa.JSON(), nullable=True),
    sa.Column('recommendation', sa.Text(), nullable=True),
    sa.Column('primary_penalty', sa.String(length=50), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('generated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['incident_id'], ['incidents.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('incident_id', 'version', name='uq_incident_rca_incident_version')
    )
    op.create_index(op.f('ix_incident_rcas_incident_id'), 'incident_rcas', ['incident_id'], unique=False)
    
    # Create incident timeline
    op.create_table('incident_timeline',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('incident_id', sa.UUID(), nullable=False),
    sa.Column('event_type', sa.String(length=50), nullable=False),
    sa.Column('event_data', sa.JSON(), nullable=True),
    sa.Column('created_by', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['incident_id'], ['incidents.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_incident_timeline_id_created', 'incident_timeline', ['incident_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_incident_timeline_incident_id'), 'incident_timeline', ['incident_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop timeline
    op.drop_index(op.f('ix_incident_timeline_incident_id'), table_name='incident_timeline')
    op.drop_index('idx_incident_timeline_id_created', table_name='incident_timeline')
    op.drop_table('incident_timeline')
    
    # Drop RCAs
    op.drop_index(op.f('ix_incident_rcas_incident_id'), table_name='incident_rcas')
    op.drop_table('incident_rcas')
    
    # Drop comments
    op.drop_index(op.f('ix_incident_comments_incident_id'), table_name='incident_comments')
    op.drop_table('incident_comments')
    
    # Drop incidents table and indexes
    op.drop_index(op.f('ix_incidents_trust_score_id'), table_name='incidents')
    op.drop_index(op.f('ix_incidents_table_name'), table_name='incidents')
    op.drop_index(op.f('ix_incidents_state'), table_name='incidents')
    op.drop_index(op.f('ix_incidents_severity'), table_name='incidents')
    op.drop_index(op.f('ix_incidents_pipeline_run_id'), table_name='incidents')
    op.drop_index(op.f('ix_incidents_created_at'), table_name='incidents')
    op.drop_index('idx_incidents_severity_state_created', table_name='incidents')
    op.drop_table('incidents')
    
    # Drop remaining tables
    op.drop_table('oncall_rotations')
    op.drop_table('escalation_policies')
    op.drop_table('alert_configs')
