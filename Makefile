.PHONY: setup db-up db-reset seed dev test smoke

# 1. Full Environment Setup
setup:
	@echo "--- Setting up Backend ---"
	python3 -m venv backend/.venv
	backend/.venv/bin/pip install --upgrade pip
	backend/.venv/bin/pip install -r backend/requirements.txt
	@echo "--- Setting up Frontend ---"
	cd frontend && npm install
	@echo "Setup complete. Run 'make db-reset' to initialize database."

# 2. Start PostgreSQL (Docker Compose or Native)
db-up:
	@if command -v docker > /dev/null 2>&1; then \
		echo "Starting PostgreSQL via Docker Compose..."; \
		docker compose up -d; \
	else \
		echo "Docker not found; starting PostgreSQL via Homebrew..."; \
		brew services start postgresql@15 2>/dev/null || true; \
	fi

# 3. Drop, Apply Schema and Seed Foundation Data
db-reset:
	backend/.venv/bin/python backend/scripts/reset_db.py

# 4. Seed Foundation Data Only
seed:
	backend/.venv/bin/python backend/scripts/seed_foundation.py

# 5. Seed 60 Demo Applications (Phase 3 Core Engine)
seed-demo:
	backend/.venv/bin/python backend/scripts/seed_demo.py

# 6. Run Backend Unit & RBAC Tests
test:
	cd backend && .venv/bin/pytest -v

# 6. Run End-to-End Smoke Test
smoke:
	./scripts/smoke_test.sh

# 7. Verify Audit Hash Chain Integrity
verify-audit:
	PYTHONPATH=backend backend/.venv/bin/python backend/scripts/verify_audit_chain.py

# 8. Export OpenAPI Specification JSON
openapi:
	PYTHONPATH=backend backend/.venv/bin/python backend/scripts/export_openapi.py

# 9. Generate Traceability Test Report (docs/16_test_report.md)
test-report:
	PYTHONPATH=backend backend/.venv/bin/python backend/scripts/generate_test_report.py

# 10. Demo Reset & Clock Zeroing
demo-reset:
	backend/.venv/bin/python backend/scripts/demo_reset.py

# 11. Demo Check 8-Step Continuous Story Runner
demo-check:
	backend/.venv/bin/python backend/scripts/demo_check.py

# 12. Cross-System Consistency Check
consistency-check:
	backend/.venv/bin/python backend/scripts/check_consistency.py

# 13. Unlock Demo Accounts
unlock-demo-accounts:
	backend/.venv/bin/python backend/scripts/unlock_demo_accounts.py

# 14. Scan Codebase for Leaked Secrets
scan-secrets:
	backend/.venv/bin/python backend/scripts/scan_secrets.py

# 15. Capture High-Resolution Headless Screenshots
screenshots:
	backend/.venv/bin/python scripts/capture_screenshots.py

# 16. Comprehensive Final Release Check
final-check:
	@echo "======================================================================"
	@echo "             SIH26262 COMPREHENSIVE FINAL RELEASE CHECK             "
	@echo "======================================================================"
	@echo "\n[Step 1/7] Running Pytest Test Suite (96 tests)..."
	cd backend && .venv/bin/pytest -v
	@echo "\n[Step 2/7] Scanning Codebase for Secrets..."
	backend/.venv/bin/python backend/scripts/scan_secrets.py
	@echo "\n[Step 3/7] Performing Demo Reset (0h offset, seeds, rule eval)..."
	backend/.venv/bin/python backend/scripts/demo_reset.py
	@echo "\n[Step 4/7] Executing 8-Step Demo Check Continuous Story..."
	backend/.venv/bin/python backend/scripts/demo_check.py
	@echo "\n[Step 5/7] Executing 7-Point Cross-System Consistency Audit..."
	backend/.venv/bin/python backend/scripts/check_consistency.py
	@echo "\n[Step 6/7] Verifying Cryptographic Audit Chain Integrity..."
	PYTHONPATH=backend backend/.venv/bin/python backend/scripts/verify_audit_chain.py
	@echo "\n[Step 7/7] Validating Frontend Production Build..."
	cd frontend && npm run build
	@echo "\n======================================================================"
	@echo "  ✓ ALL 7 FINAL CHECKS PASSED WITH ZERO ERRORS (RELEASE READY v1.0)  "
	@echo "======================================================================"

# 17. Safe Git-Based Release Packaging
package:
	git archive --format=zip --output=sih26262_release.zip HEAD
	@echo "Created sih26262_release.zip via git archive"
	backend/.venv/bin/python scripts/verify_package.py sih26262_release.zip

# 18. Start Development Servers (Backend & Frontend)
dev:
	@echo "Starting Backend on http://localhost:8000 and Frontend on http://localhost:3001..."
	(trap 'kill 0' SIGINT; \
		(cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000) & \
		(cd frontend && npm run dev) & \
		wait)

