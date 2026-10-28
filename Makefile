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

# 7. Start Development Servers (Backend & Frontend)
dev:
	@echo "Starting Backend on http://localhost:8000 and Frontend on http://localhost:3000..."
	(trap 'kill 0' SIGINT; \
		(cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000) & \
		(cd frontend && npm run dev) & \
		wait)
