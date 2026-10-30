import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import text
from app.core.database import engine
from scripts.seed_foundation import seed_foundation


def reset_database():
    print("=== STARTING ONE-COMMAND DATABASE RESET ===")
    
    # Drop all tables, views, types and alembic_version
    drop_sql = """
    DROP TABLE IF EXISTS alembic_version CASCADE;
    DROP TABLE IF EXISTS integration_log CASCADE;
    DROP TABLE IF EXISTS alert_priority_scores CASCADE;
    DROP TABLE IF EXISTS risk_score_snapshots CASCADE;
    DROP TABLE IF EXISTS committee_observations CASCADE;
    DROP TABLE IF EXISTS committee_assignments CASCADE;
    DROP TABLE IF EXISTS clock_segments CASCADE;
    DROP TABLE IF EXISTS holidays CASCADE;
    DROP TABLE IF EXISTS scheduler_runs CASCADE;
    DROP TABLE IF EXISTS email_outbox CASCADE;
    DROP TABLE IF EXISTS escalation_history CASCADE;
    DROP TABLE IF EXISTS undertaking_history CASCADE;
    DROP TABLE IF EXISTS undertaking_evidence CASCADE;
    DROP TABLE IF EXISTS undertakings CASCADE;
    DROP TABLE IF EXISTS documents CASCADE;
    DROP TABLE IF EXISTS evc_visits CASCADE;
    DROP TABLE IF EXISTS evc_experts CASCADE;
    DROP TABLE IF EXISTS uploaded_files CASCADE;
    DROP TABLE IF EXISTS audit_log CASCADE;
    DROP TABLE IF EXISTS case_summaries CASCADE;
    DROP TABLE IF EXISTS notifications CASCADE;
    DROP TABLE IF EXISTS application_communications CASCADE;
    DROP TABLE IF EXISTS alerts CASCADE;
    DROP TABLE IF EXISTS escalation_rules CASCADE;
    DROP TABLE IF EXISTS alert_rules CASCADE;
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

    with engine.begin() as conn:
        print("1. Dropping existing tables and enums...")
        conn.execute(text(drop_sql))

    # Read and apply db/schema.sql
    schema_sql_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', 'db', 'schema.sql')
    )
    with open(schema_sql_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    with engine.begin() as conn:
        print("2. Applying db/schema.sql...")
        conn.execute(text(schema_sql))
        
        # Stamp alembic version to head
        conn.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) PRIMARY KEY);"))
        conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('007_phase8_security') ON CONFLICT (version_num) DO NOTHING;"))

    print("3. Seeding foundation data...")
    seed_foundation()
    print("=== DATABASE RESET & SEED COMPLETE ===")


if __name__ == "__main__":
    reset_database()
