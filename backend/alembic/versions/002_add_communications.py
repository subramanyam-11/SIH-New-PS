"""add communications table and approval order columns

Revision ID: 002_add_communications
Revises: 001_initial_schema
Create Date: 2026-10-27 20:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '002_add_communications'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add approval letter and escalation fields to applications
    op.add_column('applications', sa.Column('approval_letter_ref', sa.String(100), nullable=True))
    op.add_column('applications', sa.Column('approval_letter_data', JSONB, nullable=True))
    op.add_column('applications', sa.Column('escalation_required', sa.Boolean, server_default='false', nullable=False))
    op.add_column('applications', sa.Column('escalation_reason', sa.Text, nullable=True))

    # 2. Create application_communications table
    op.create_table(
        'application_communications',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('application_id', sa.Integer, sa.ForeignKey('applications.id', ondelete='CASCADE'), nullable=False),
        sa.Column('template_code', sa.String(50), nullable=False),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('body', sa.Text, nullable=False),
        sa.Column('recipient_email', sa.String(150), nullable=False),
        sa.Column('status', sa.String(20), server_default='DRAFT', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sent_by', sa.Integer, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('idx_app_comms_app_id', 'application_communications', ['application_id'])
    op.create_index('idx_app_comms_status', 'application_communications', ['status'])


def downgrade() -> None:
    op.drop_table('application_communications')
    op.drop_column('applications', 'escalation_reason')
    op.drop_column('applications', 'escalation_required')
    op.drop_column('applications', 'approval_letter_data')
    op.drop_column('applications', 'approval_letter_ref')
