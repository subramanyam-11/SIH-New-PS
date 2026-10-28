"""phase 6 v2 alignment: bureau officer, committee member, clock segments, holidays, closed stage

Revision ID: 005_phase6_v2_alignment
Revises: 004_add_phase5_modules
Create Date: 2026-10-29 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '005_phase6_v2_alignment'
down_revision = '004_add_phase5_modules'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Update PostgreSQL Enums
    # PostgreSQL requires each ALTER TYPE ADD VALUE to be committed before being referenced
    op.execute("COMMIT;")
    op.execute("ALTER TYPE user_role_enum ADD VALUE IF NOT EXISTS 'BUREAU_OFFICER';")
    op.execute("ALTER TYPE user_role_enum ADD VALUE IF NOT EXISTS 'COMMITTEE_MEMBER';")
    op.execute("ALTER TYPE application_status_enum ADD VALUE IF NOT EXISTS 'CLOSED';")
    op.execute("COMMIT;")

    # 2. Alter existing tables
    # applications: add case_holder, closed_at, closure_reason, closure_remarks
    op.add_column('applications', sa.Column('case_holder', sa.String(30), server_default='WITH_AICTE', nullable=False))
    op.add_column('applications', sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('applications', sa.Column('closure_reason', sa.String(50), nullable=True))
    op.add_column('applications', sa.Column('closure_remarks', sa.Text(), nullable=True))
    op.create_index('ix_applications_case_holder', 'applications', ['case_holder'])

    # alert_rules: add day_basis
    op.add_column('alert_rules', sa.Column('day_basis', sa.String(20), server_default='WORKING', nullable=False))

    # 3. Create clock_segments table
    op.create_table(
        'clock_segments',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('application_id', sa.Integer(), sa.ForeignKey('applications.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('stage_id', sa.Integer(), sa.ForeignKey('stages.id'), nullable=False),
        sa.Column('holder', sa.String(30), nullable=False, index=True), # 'WITH_AICTE' or 'WITH_INSTITUTION'
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, index=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_hours', sa.Float(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    op.create_index('ix_clock_segments_app_started', 'clock_segments', ['application_id', 'started_at'])

    # 4. Create holidays table
    op.create_table(
        'holidays',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('date', sa.Date(), nullable=False, index=True),
        sa.Column('name', sa.String(150), nullable=False),
        sa.Column('region_id', sa.Integer(), sa.ForeignKey('regions.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('holiday_type', sa.String(50), server_default='NATIONAL', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )

    # 5. Create committee_assignments table
    op.create_table(
        'committee_assignments',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('application_id', sa.Integer(), sa.ForeignKey('applications.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('committee_type', sa.String(20), nullable=False, index=True), # 'EVC', 'SAC', 'SHC'
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('status', sa.String(20), server_default='ASSIGNED', nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
    )

    # 6. Create committee_observations table
    op.create_table(
        'committee_observations',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('application_id', sa.Integer(), sa.ForeignKey('applications.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('committee_type', sa.String(20), nullable=False, index=True), # 'EVC', 'SAC', 'SHC'
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('member_name', sa.String(150), nullable=False),
        sa.Column('observation_text', sa.Text(), nullable=False),
        sa.Column('recommendation', sa.String(50), nullable=False), # 'RECOMMEND_APPROVAL', etc.
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )

    # 7. Insert the two new roles if not existing
    op.execute("""
        INSERT INTO roles (code, title, description)
        VALUES 
            ('BUREAU_OFFICER', 'Bureau Officer', 'Cross-region read view of pendency, bottlenecks and escalations for bureau'),
            ('COMMITTEE_MEMBER', 'Committee Member', 'Member of EVC, SAC, or SHC committee recording observations and recommendations')
        ON CONFLICT (code) DO NOTHING;
    """)

    # 8. Insert CLOSED stage if not existing
    op.execute("""
        INSERT INTO stages (code, name, default_sla_days, responsible_role, description)
        VALUES ('CLOSED', 'Case Closed', 0, 'COMPETENT_AUTHORITY', 'Application lifecycle completed and archived with recorded closure reason')
        ON CONFLICT (code) DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_table('committee_observations')
    op.drop_table('committee_assignments')
    op.drop_table('holidays')
    op.drop_table('clock_segments')
    op.drop_column('alert_rules', 'day_basis')
    op.drop_column('applications', 'closure_remarks')
    op.drop_column('applications', 'closure_reason')
    op.drop_column('applications', 'closed_at')
    op.drop_column('applications', 'case_holder')
