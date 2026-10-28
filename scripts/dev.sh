#!/usr/bin/env bash
trap 'kill 0' SIGINT
(cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000) &
(cd frontend && npm run dev) &
wait
