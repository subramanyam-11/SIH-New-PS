"""phase 8: security hardening, tamper-evident audit log, integration log

Revision ID: 007_phase8_security
Revises: 006_phase7_innovation
Create Date: 2026-10-30 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
import hashlib


# revision identifiers
revision = '007_phase8_security'
down_revision = '006_phase7_innovation'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Audit Log: Add prev_hash and hash columns
    op.add_column('audit_log', sa.Column('prev_hash', sa.String(64), nullable=True))
    op.add_column('audit_log', sa.Column('hash', sa.String(64), nullable=True))
    op.create_index('ix_audit_log_hash', 'audit_log', ['hash'])

    # 2. Uploaded Files: Add encryption columns
    op.add_column('uploaded_files', sa.Column('is_encrypted', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('uploaded_files', sa.Column('encryption_key_id', sa.String(50), nullable=True))
    op.add_column('uploaded_files', sa.Column('encryption_iv', sa.String(64), nullable=True))

    # 3. Create integration_log table
    op.create_table(
        'integration_log',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('direction', sa.String(20), nullable=False),  # INBOUND, OUTBOUND
        sa.Column('operation', sa.String(100), nullable=False),
        sa.Column('adapter_type', sa.String(50), nullable=False, server_default='MOCK_AICTE'),
        sa.Column('status', sa.String(20), nullable=False),      # SUCCESS, FAILED, REJECTED
        sa.Column('idempotency_key', sa.String(100), nullable=True, index=True),
        sa.Column('request_summary', JSONB, nullable=True),
        sa.Column('response_summary', JSONB, nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )

    # 4. Backfill existing audit_log hash chain
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, table_name, record_id, action, actor_id, created_at FROM audit_log ORDER BY id ASC")
    ).fetchall()

    if rows:
        prev_hash = "GENESIS"
        update_stmt = sa.text("UPDATE audit_log SET prev_hash = :prev_hash, hash = :hash WHERE id = :id")
        batch = []
        for r in rows:
            actor_str = str(r.actor_id) if r.actor_id is not None else "NONE"
            iso_dt = r.created_at.isoformat() if r.created_at else ""
            content = f"{r.id}:{r.table_name}:{r.record_id}:{r.action}:{actor_str}:{iso_dt}:{prev_hash}"
            row_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            batch.append({"id": r.id, "prev_hash": prev_hash, "hash": row_hash})
            prev_hash = row_hash
            if len(batch) >= 1000:
                conn.execute(update_stmt, batch)
                batch = []
        if batch:
            conn.execute(update_stmt, batch)

    # 5. Database-level trigger to strictly block UPDATE and DELETE on audit_log
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'audit_log is append-only: UPDATE and DELETE statements are strictly blocked at the database level.';
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS trg_audit_log_prevent_modify ON audit_log;
        CREATE TRIGGER trg_audit_log_prevent_modify
        BEFORE UPDATE OR DELETE ON audit_log
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_log_modification();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_audit_log_prevent_modify ON audit_log;")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_log_modification();")
    op.drop_table('integration_log')
    op.drop_column('uploaded_files', 'encryption_iv')
    op.drop_column('uploaded_files', 'encryption_key_id')
    op.drop_column('uploaded_files', 'is_encrypted')
    op.drop_index('ix_audit_log_hash', 'audit_log')
    op.drop_column('audit_log', 'hash')
    op.drop_column('audit_log', 'prev_hash')
