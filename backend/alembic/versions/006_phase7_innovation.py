"""phase 7 innovation layer: risk snapshots, enhanced summaries, alert ranking

Revision ID: 006_phase7_innovation
Revises: 005_phase6_v2_alignment
Create Date: 2026-10-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers
revision = '006_phase7_innovation'
down_revision = '005_phase6_v2_alignment'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Add new AlertTypeEnum values ---
    op.execute("COMMIT;")
    op.execute("ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'EVC_VISIT_OVERDUE';")
    op.execute("ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'UNDERTAKING_OVERDUE';")
    op.execute("ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'DOCUMENT_RENEWAL_OVERDUE';")
    op.execute("ALTER TYPE alert_type_enum ADD VALUE IF NOT EXISTS 'RISK_HIGH';")
    op.execute("BEGIN;")

    # --- Add new AlertSeverityEnum value ---
    op.execute("COMMIT;")
    op.execute("ALTER TYPE alert_severity_enum ADD VALUE IF NOT EXISTS 'INFO';")
    op.execute("BEGIN;")

    # --- risk_score_snapshots table ---
    op.create_table(
        'risk_score_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('application_id', sa.Integer(), sa.ForeignKey('applications.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('band', sa.String(20), nullable=False),  # LOW, MEDIUM, HIGH
        sa.Column('factor_age', sa.Float(), nullable=False, server_default='0'),
        sa.Column('factor_returns', sa.Float(), nullable=False, server_default='0'),
        sa.Column('factor_workload', sa.Float(), nullable=False, server_default='0'),
        sa.Column('factor_stage', sa.Float(), nullable=False, server_default='0'),
        sa.Column('raw_age', sa.Float(), nullable=True),
        sa.Column('raw_returns', sa.Float(), nullable=True),
        sa.Column('raw_workload', sa.Float(), nullable=True),
        sa.Column('raw_stage', sa.Float(), nullable=True),
        sa.Column('weights', JSONB, nullable=False, server_default='{}'),
        sa.Column('config_version', sa.String(50), nullable=True),
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # --- alert_priority_scores table ---
    op.create_table(
        'alert_priority_scores',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('alert_id', sa.Integer(), sa.ForeignKey('alerts.id', ondelete='CASCADE'), nullable=False, unique=True, index=True),
        sa.Column('priority_score', sa.Float(), nullable=False),
        sa.Column('factor_severity', sa.Float(), nullable=False, server_default='0'),
        sa.Column('factor_overdue_days', sa.Float(), nullable=False, server_default='0'),
        sa.Column('factor_escalation', sa.Float(), nullable=False, server_default='0'),
        sa.Column('factor_risk_impact', sa.Float(), nullable=False, server_default='0'),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # --- Enhance case_summaries table for v2 ---
    op.add_column('case_summaries', sa.Column('source_label', sa.String(50), server_default='template', nullable=True))
    op.add_column('case_summaries', sa.Column('input_hash', sa.String(64), nullable=True))
    op.add_column('case_summaries', sa.Column('timeline_highlights', JSONB, server_default='[]', nullable=True))
    op.add_column('case_summaries', sa.Column('pending_items', JSONB, server_default='[]', nullable=True))
    op.add_column('case_summaries', sa.Column('upcoming_deadlines', JSONB, server_default='[]', nullable=True))
    op.add_column('case_summaries', sa.Column('suggested_next_steps', JSONB, server_default='[]', nullable=True))
    op.add_column('case_summaries', sa.Column('risk_score_at_generation', sa.Float(), nullable=True))
    op.add_column('case_summaries', sa.Column('top_risk_factors', JSONB, server_default='[]', nullable=True))

    # --- Add risk_band to applications for quick filtering ---
    op.add_column('applications', sa.Column('risk_band', sa.String(20), server_default='LOW', nullable=True))


def downgrade() -> None:
    op.drop_column('applications', 'risk_band')
    op.drop_column('case_summaries', 'top_risk_factors')
    op.drop_column('case_summaries', 'risk_score_at_generation')
    op.drop_column('case_summaries', 'suggested_next_steps')
    op.drop_column('case_summaries', 'upcoming_deadlines')
    op.drop_column('case_summaries', 'pending_items')
    op.drop_column('case_summaries', 'timeline_highlights')
    op.drop_column('case_summaries', 'input_hash')
    op.drop_column('case_summaries', 'source_label')
    op.drop_table('alert_priority_scores')
    op.drop_table('risk_score_snapshots')
