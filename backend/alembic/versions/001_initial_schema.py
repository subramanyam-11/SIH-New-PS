"""initial schema matching schema.sql exactly

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-27 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import os

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Path to db/schema.sql
    schema_sql_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', '..', 'db', 'schema.sql')
    )
    with open(schema_sql_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # Execute schema.sql directly in the connection
    op.execute(sql_content)


def downgrade() -> None:
    # Drop all created tables and types
    drop_sql = """
    DROP TABLE IF EXISTS audit_log CASCADE;
    DROP TABLE IF EXISTS case_summaries CASCADE;
    DROP TABLE IF EXISTS notifications CASCADE;
    DROP TABLE IF EXISTS alerts CASCADE;
    DROP TABLE IF EXISTS escalation_rules CASCADE;
    DROP TABLE IF EXISTS alert_rules CASCADE;
    DROP TABLE IF EXISTS undertaking_evidence CASCADE;
    DROP TABLE IF EXISTS undertakings CASCADE;
    DROP TABLE IF EXISTS documents CASCADE;
    DROP TABLE IF EXISTS evc_visits CASCADE;
    DROP TABLE IF EXISTS stage_history CASCADE;
    DROP TABLE IF EXISTS applications CASCADE;
    DROP TABLE IF EXISTS stage_paths CASCADE;
    DROP TABLE IF EXISTS stages CASCADE;
    DROP TABLE IF EXISTS application_categories CASCADE;
    DROP TABLE IF EXISTS users CASCADE;
    DROP TABLE IF EXISTS roles CASCADE;
    DROP TABLE IF EXISTS institutions CASCADE;
    DROP TABLE IF EXISTS regions CASCADE;
    DROP TABLE IF EXISTS communication_templates CASCADE;
    DROP TABLE IF EXISTS system_config CASCADE;

    DROP TYPE IF EXISTS user_role_enum CASCADE;
    DROP TYPE IF EXISTS application_status_enum CASCADE;
    DROP TYPE IF EXISTS stage_status_enum CASCADE;
    DROP TYPE IF EXISTS evc_status_enum CASCADE;
    DROP TYPE IF EXISTS undertaking_status_enum CASCADE;
    DROP TYPE IF EXISTS document_type_enum CASCADE;
    DROP TYPE IF EXISTS document_status_enum CASCADE;
    DROP TYPE IF EXISTS alert_type_enum CASCADE;
    DROP TYPE IF EXISTS alert_severity_enum CASCADE;
    DROP TYPE IF EXISTS alert_status_enum CASCADE;
    DROP TYPE IF EXISTS notification_channel_enum CASCADE;
    """
    op.execute(drop_sql)
