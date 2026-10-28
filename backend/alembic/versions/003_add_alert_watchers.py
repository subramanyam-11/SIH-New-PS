"""add alert watchers escalation history email outbox and scheduler logs

Revision ID: 003_add_alert_watchers
Revises: 002_add_communications
Create Date: 2026-10-28 23:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '003_add_alert_watchers'
down_revision = '002_add_communications'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add 'SNOOZED' to alert_status_enum
    op.execute("ALTER TYPE alert_status_enum ADD VALUE IF NOT EXISTS 'SNOOZED';")

    # 2. Add snooze, acknowledgement and resolution columns to alerts table
    op.add_column('alerts', sa.Column('snoozed_until', sa.DateTime(timezone=True), nullable=True))
    op.add_column('alerts', sa.Column('snooze_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('alerts', sa.Column('snooze_reason', sa.Text(), nullable=True))
    op.add_column('alerts', sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('alerts', sa.Column('acknowledged_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True))
    op.add_column('alerts', sa.Column('acknowledgement_remarks', sa.Text(), nullable=True))
    op.add_column('alerts', sa.Column('resolved_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True))
    op.add_column('alerts', sa.Column('resolution_remarks', sa.Text(), nullable=True))

    # 3. Create escalation_history table
    op.create_table(
        'escalation_history',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('alert_id', sa.Integer(), sa.ForeignKey('alerts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('from_tier', sa.Integer(), nullable=False),
        sa.Column('to_tier', sa.Integer(), nullable=False),
        sa.Column('target_role', sa.String(50), nullable=False),
        sa.Column('recipient_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('escalated_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
    )
    op.create_index('idx_escalation_history_alert_id', 'escalation_history', ['alert_id'])

    # 4. Create email_outbox table
    op.create_table(
        'email_outbox',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('recipient_email', sa.String(150), nullable=False),
        sa.Column('recipient_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), server_default='QUEUED', nullable=False),
        sa.Column('template_code', sa.String(50), nullable=True),
        sa.Column('entity_type', sa.String(50), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
    )
    op.create_index('idx_email_outbox_status', 'email_outbox', ['status'])

    # 5. Create scheduler_runs table
    op.create_table(
        'scheduler_runs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('rules_evaluated', sa.Integer(), server_default='0', nullable=False),
        sa.Column('alerts_created', sa.Integer(), server_default='0', nullable=False),
        sa.Column('alerts_upgraded', sa.Integer(), server_default='0', nullable=False),
        sa.Column('alerts_resolved', sa.Integer(), server_default='0', nullable=False),
        sa.Column('status', sa.String(20), server_default='SUCCESS', nullable=False),
        sa.Column('triggered_by', sa.String(50), server_default='SCHEDULER', nullable=False),
        sa.Column('details', JSONB, server_default='{}', nullable=False),
    )
    op.create_index('idx_scheduler_runs_started_at', 'scheduler_runs', ['started_at'])


def downgrade() -> None:
    op.drop_table('scheduler_runs')
    op.drop_table('email_outbox')
    op.drop_table('escalation_history')
    op.drop_column('alerts', 'resolution_remarks')
    op.drop_column('alerts', 'resolved_by')
    op.drop_column('alerts', 'acknowledgement_remarks')
    op.drop_column('alerts', 'acknowledged_by')
    op.drop_column('alerts', 'acknowledged_at')
    op.drop_column('alerts', 'snooze_reason')
    op.drop_column('alerts', 'snooze_count')
    op.drop_column('alerts', 'snoozed_until')
