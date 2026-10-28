"""add phase 5 modules evc experts uploaded files undertakings and document versioning

Revision ID: 004_add_phase5_modules
Revises: 003_add_alert_watchers
Create Date: 2026-10-28 23:55:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '004_add_phase5_modules'
down_revision = '003_add_alert_watchers'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Update Enums with Phase 5 values
    # PostgreSQL requires each ALTER TYPE ADD VALUE outside a transaction or commit, or with IF NOT EXISTS
    op.execute("ALTER TYPE evc_status_enum ADD VALUE IF NOT EXISTS 'PENDING_ASSIGNMENT';")
    op.execute("ALTER TYPE evc_status_enum ADD VALUE IF NOT EXISTS 'ASSIGNED';")
    op.execute("ALTER TYPE evc_status_enum ADD VALUE IF NOT EXISTS 'VISIT_DONE';")
    op.execute("ALTER TYPE evc_status_enum ADD VALUE IF NOT EXISTS 'REPORT_RECEIVED';")
    op.execute("ALTER TYPE evc_status_enum ADD VALUE IF NOT EXISTS 'CLOSED';")

    op.execute("ALTER TYPE undertaking_status_enum ADD VALUE IF NOT EXISTS 'PENDING';")
    op.execute("ALTER TYPE undertaking_status_enum ADD VALUE IF NOT EXISTS 'SUBMITTED';")
    op.execute("ALTER TYPE undertaking_status_enum ADD VALUE IF NOT EXISTS 'VERIFIED';")
    op.execute("ALTER TYPE undertaking_status_enum ADD VALUE IF NOT EXISTS 'REJECTED';")
    op.execute("ALTER TYPE undertaking_status_enum ADD VALUE IF NOT EXISTS 'NEEDS_MORE_EVIDENCE';")
    op.execute("ALTER TYPE undertaking_status_enum ADD VALUE IF NOT EXISTS 'ESCALATED';")

    op.execute("ALTER TYPE document_status_enum ADD VALUE IF NOT EXISTS 'VALID';")
    op.execute("ALTER TYPE document_status_enum ADD VALUE IF NOT EXISTS 'EXPIRING';")
    op.execute("ALTER TYPE document_status_enum ADD VALUE IF NOT EXISTS 'RENEWED';")

    # 2. Create evc_experts table
    op.create_table(
        'evc_experts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(150), nullable=False),
        sa.Column('designation', sa.String(150), nullable=False),
        sa.Column('discipline', sa.String(100), nullable=False),
        sa.Column('region_id', sa.Integer(), sa.ForeignKey('regions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('home_institution', sa.String(200), nullable=False),
        sa.Column('city', sa.String(100), nullable=False),
        sa.Column('is_available', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
    )
    op.create_index('idx_evc_experts_region_id', 'evc_experts', ['region_id'])

    # 3. Create uploaded_files table
    op.create_table(
        'uploaded_files',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('stored_filename', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('checksum_sha256', sa.String(64), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('uploaded_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
    )
    op.create_index('idx_uploaded_files_entity', 'uploaded_files', ['entity_type', 'entity_id'])

    # 4. Enhance evc_visits
    op.add_column('evc_visits', sa.Column('assigned_experts', JSONB, server_default='[]', nullable=True))
    op.add_column('evc_visits', sa.Column('scheduled_time', sa.String(50), nullable=True))
    op.add_column('evc_visits', sa.Column('visit_summary', sa.Text(), nullable=True))
    op.add_column('evc_visits', sa.Column('report_file_id', sa.Integer(), sa.ForeignKey('uploaded_files.id', ondelete='SET NULL'), nullable=True))
    op.add_column('evc_visits', sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('evc_visits', sa.Column('closed_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True))

    # 5. Enhance undertakings
    op.add_column('undertakings', sa.Column('rejection_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('undertakings', sa.Column('escalated_to_tier', sa.Integer(), server_default='1', nullable=False))
    op.add_column('undertakings', sa.Column('escalation_reason', sa.Text(), nullable=True))

    # 6. Create undertaking_history table
    op.create_table(
        'undertaking_history',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('undertaking_id', sa.Integer(), sa.ForeignKey('undertakings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('from_status', sa.String(50), nullable=True),
        sa.Column('to_status', sa.String(50), nullable=False),
        sa.Column('action_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action_role', sa.String(50), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
    )
    op.create_index('idx_undertaking_history_undertaking_id', 'undertaking_history', ['undertaking_id'])

    # 7. Enhance undertaking_evidence with file_id
    op.add_column('undertaking_evidence', sa.Column('file_id', sa.Integer(), sa.ForeignKey('uploaded_files.id', ondelete='SET NULL'), nullable=True))

    # 8. Enhance documents with versioning & verification
    op.add_column('documents', sa.Column('version_number', sa.Integer(), server_default='1', nullable=False))
    op.add_column('documents', sa.Column('previous_version_id', sa.Integer(), sa.ForeignKey('documents.id', ondelete='SET NULL'), nullable=True))
    op.add_column('documents', sa.Column('renewal_file_id', sa.Integer(), sa.ForeignKey('uploaded_files.id', ondelete='SET NULL'), nullable=True))
    op.add_column('documents', sa.Column('verified_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True))
    op.add_column('documents', sa.Column('verification_remarks', sa.Text(), nullable=True))


def downgrade() -> None:
    pass
