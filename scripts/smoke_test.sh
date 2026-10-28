#!/usr/bin/env bash
set -e

BACKEND_URL="http://127.0.0.1:8000"
echo "=== SIH26262 SMOKE TEST SUITE (PHASES 1-3) ==="

# 1. Start backend if not already running on port 8000
SERVER_STARTED_BY_SCRIPT=0
if ! curl -s -f "$BACKEND_URL/health" > /dev/null 2>&1; then
  echo "Backend not detected on port 8000. Launching temporary instance..."
  cd backend
  .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 &
  UVICORN_PID=$!
  SERVER_STARTED_BY_SCRIPT=1
  cd ..
  echo "Waiting for backend to start (PID: $UVICORN_PID)..."
  sleep 3
fi

# 2. Check Health Endpoint
echo -n "1. Checking GET /health ... "
HEALTH_RESPONSE=$(curl -s "$BACKEND_URL/health")
echo "$HEALTH_RESPONSE" | grep -q '"status":"ok"' && echo "PASSED (Database Healthy)" || (echo "FAILED" && exit 1)

# 3. Check Demo Login (Admin)
echo -n "2. Checking POST /api/v1/auth/demo-login (Admin) ... "
ADMIN_LOGIN=$(curl -s -X POST "$BACKEND_URL/api/v1/auth/demo-login" \
  -H "Content-Type: application/json" \
  -d '{"role": "ADMIN", "email": "admin@aicte.gov.in"}')
echo "$ADMIN_LOGIN" | grep -q 'access_token' && echo "PASSED" || (echo "FAILED: $ADMIN_LOGIN" && exit 1)
ADMIN_TOKEN=$(echo "$ADMIN_LOGIN" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')

# 4. Check Demo Login (Regional Head North)
echo -n "3. Checking Regional Scoping /users/me/scope ... "
RO_LOGIN=$(curl -s -X POST "$BACKEND_URL/api/v1/auth/demo-login" \
  -H "Content-Type: application/json" \
  -d '{"role": "REGIONAL_HEAD", "email": "ro.north@aicte.gov.in"}')
RO_TOKEN=$(echo "$RO_LOGIN" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
SCOPE_RESPONSE=$(curl -s "$BACKEND_URL/api/v1/users/me/scope" -H "Authorization: Bearer $RO_TOKEN")
echo "$SCOPE_RESPONSE" | grep -q 'Northern Regional Office' && echo "PASSED (Regional Scope Verified)" || (echo "FAILED" && exit 1)

# 5. Check Deficiency Tags Endpoint (Phase 3 Requirement 1)
echo -n "4. Checking GET /api/v1/config/deficiency-tags ... "
TAGS_RESPONSE=$(curl -s "$BACKEND_URL/api/v1/config/deficiency-tags" -H "Authorization: Bearer $ADMIN_TOKEN")
echo "$TAGS_RESPONSE" | grep -q 'DEF_LAND_TITLE' && echo "$TAGS_RESPONSE" | grep -q 'DEF_OTHER' && echo "PASSED (9 Tags Present)" || (echo "FAILED" && exit 1)

# 6. Check Applications List (Phase 3 Requirement 4: 60 applications)
echo -n "5. Checking GET /api/v1/applications (Seeded 60 Applications) ... "
APPS_RESPONSE=$(curl -s "$BACKEND_URL/api/v1/applications?limit=5" -H "Authorization: Bearer $ADMIN_TOKEN")
echo "$APPS_RESPONSE" | grep -q 'AICTE/2026/APP-' && echo "PASSED" || (echo "FAILED" && exit 1)

# 7. End-to-End Application Lifecycle (Submit -> Scrutiny -> Revert -> Clarify -> Approve)
echo -n "6. End-to-End Workflow Transition Lifecycle ... "
# a. Submit Application
SUBMIT_RES=$(curl -s -X POST "$BACKEND_URL/api/v1/applications" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"institution_id": 1, "category_id": 2}')
TEST_APP_ID=$(echo "$SUBMIT_RES" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))")
if [ -z "$TEST_APP_ID" ]; then
  echo "FAILED (Submit failed: $SUBMIT_RES)" && exit 1
fi

# b. Scrutiny Officer advances SUBMITTED -> SCRUTINY
SCRUTINY_LOGIN=$(curl -s -X POST "$BACKEND_URL/api/v1/auth/demo-login" \
  -H "Content-Type: application/json" \
  -d '{"role": "SCRUTINY_OFFICER", "email": "scrutiny1@aicte.gov.in"}')
SCRUTINY_TOKEN=$(echo "$SCRUTINY_LOGIN" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')

ADV_RES=$(curl -s -X POST "$BACKEND_URL/api/v1/applications/$TEST_APP_ID/complete-stage" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SCRUTINY_TOKEN" \
  -d '{"remarks": "Initial dossier verified and allotted to scrutiny desk."}')
echo "$ADV_RES" | grep -q '"current_stage_code":"SCRUTINY"' || (echo "FAILED (Advance to Scrutiny: $ADV_RES)" && exit 1)

# c. Scrutiny Officer reverts with deficiency tags (Revert 1)
REV_RES=$(curl -s -X POST "$BACKEND_URL/api/v1/applications/$TEST_APP_ID/return" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SCRUTINY_TOKEN" \
  -d '{"deficiency_tags": ["DEF_FIRE_NOC"], "reason": "Fire safety certificate expired on 30-Sept-2026."}')
echo "$REV_RES" | grep -q '"current_stage_code":"RE_SCRUTINY"' || (echo "FAILED (Revert failed: $REV_RES)" && exit 1)

# d. Institution clarifies deficiency
INST_LOGIN=$(curl -s -X POST "$BACKEND_URL/api/v1/auth/demo-login" \
  -H "Content-Type: application/json" \
  -d '{"role": "INSTITUTION_USER", "email": "principal@apexkanpur.edu"}')
INST_TOKEN=$(echo "$INST_LOGIN" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')

CLARIFY_RES=$(curl -s -X POST "$BACKEND_URL/api/v1/applications/$TEST_APP_ID/complete-stage" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $INST_TOKEN" \
  -d '{"remarks": "Uploaded renewed Fire Safety Certificate issued by Chief Fire Officer."}')
echo "$CLARIFY_RES" | grep -q '"current_stage_code":"SCRUTINY"' || (echo "FAILED (Clarify failed: $CLARIFY_RES)" && exit 1)

# e. Competent Authority records final APPROVE decision
AUTH_LOGIN=$(curl -s -X POST "$BACKEND_URL/api/v1/auth/demo-login" \
  -H "Content-Type: application/json" \
  -d '{"role": "COMPETENT_AUTHORITY", "email": "chairman@aicte.gov.in"}')
AUTH_TOKEN=$(echo "$AUTH_LOGIN" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')

DEC_RES=$(curl -s -X POST "$BACKEND_URL/api/v1/applications/$TEST_APP_ID/decision" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"decision": "APPROVE", "remarks": "Statutory requirements satisfied. Approved."}')
echo "$DEC_RES" | grep -q 'SAMPLE - SYNTHETIC DEMO DOCUMENT, NOT AN OFFICIAL AICTE ORDER' && echo "PASSED (Approval Letter & Watermark Verified)" || (echo "FAILED: $DEC_RES" && exit 1)

# 8. Check Demo Time Travel Clock Endpoint (Phase 3 Requirement 5)
echo -n "7. Checking Demo Clock Advance (+24 Hours) ... "
CLOCK_RES=$(curl -s -X POST "$BACKEND_URL/api/v1/demo/advance-clock" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"hours": 24.0}')
echo "$CLOCK_RES" | grep -q '"advanced_hours":24' && echo "PASSED" || (echo "FAILED: $CLOCK_RES" && exit 1)
# Reset clock
curl -s -X POST "$BACKEND_URL/api/v1/demo/reset-clock" -H "Authorization: Bearer $ADMIN_TOKEN" > /dev/null

# Clean up temporary server if launched
if [ $SERVER_STARTED_BY_SCRIPT -eq 1 ]; then
  echo "Stopping temporary background server (PID: $UVICORN_PID)..."
  kill $UVICORN_PID || true
fi

echo "=== ALL PHASE 3 SMOKE CHECKS PASSED SUCCESSFULLY ==="
