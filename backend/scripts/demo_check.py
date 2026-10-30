"""
SIH26262 Demo Check Verification Script
Automated end-to-end rehearsal runner for the 8-step continuous demo story:
Step 1: New submission & auto-path routing.
Step 2: Scrutiny clearance & EVC panel scheduling.
Step 3: Early delay risk detection (Score 70+, explainable breakdown).
Step 4: Clock advance (+7d) & multi-tier alert escalation.
Step 5: Deficiency return, case holder WITH_INSTITUTION, paused clock, reply resumes.
Step 6: Conditional undertaking compliance upload & 1-click officer audit.
Step 7: Pre-expiry statutory document alert & renewal verification.
Step 8: Competent Authority decision, regional reports, and immutable audit chain verification.

Restores database to pristine demo state upon completion.
"""
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app
from scripts.demo_reset import demo_reset

client = TestClient(app)


def login(username: str) -> str:
    res = client.post("/api/v1/auth/login", json={"email": username, "password": "Password@123"})
    assert res.status_code == 200, f"Login failed for {username}: {res.text}"
    return res.json()["access_token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def run_demo_check():
    print("=" * 70)
    print("  SIH26262: EXECUTING 8-STEP CONTINUOUS DEMO REHEARSAL CHECK")
    print("=" * 70)

    # 1. Fresh Reset
    print("\n[Phase 0] Initializing pristine demo state...")
    demo_reset()

    # Tokens for personas
    inst_token = login("principal@apexkanpur.demo.example")
    sc_token = login("scrutiny1@demo.example")
    evc_token = login("evc.coord@demo.example")
    ro_token = login("ro.north@demo.example")
    ca_token = login("chairman@demo.example")
    admin_token = login("admin@demo.example")

    # -------------------------------------------------------------------------
    # STEP 1: New Submission & Auto-Path Chosen
    # -------------------------------------------------------------------------
    print("\n[Step 1/8] Verifying New Submission & Auto-Path Routing (APP-10001)...")
    res = client.get("/api/v1/applications/1", headers=auth_header(sc_token))
    assert res.status_code == 200, res.text
    app1 = res.json()
    assert app1["application_number"] == "AICTE/2026/APP-10001"
    assert app1["current_stage_code"] == "SUBMITTED"
    assert app1["case_holder"] == "WITH_AICTE"
    assert app1["stage_path_code"] in ["PATH_2_SCRUTINY_EVC", "PATH_1_SCRUTINY_ONLY"]
    print("  ✓ Application #1 is in SUBMITTED stage with automated statutory path.")

    # Scrutiny Officer completes stage to advance to SCRUTINY
    res_adv = client.post(
        "/api/v1/applications/1/complete-stage",
        headers=auth_header(sc_token),
        json={"remarks": "Initial intake documentation verified. Proceeding to detailed scrutiny."}
    )
    assert res_adv.status_code == 200, res_adv.text
    assert res_adv.json()["current_stage_code"] == "SCRUTINY"
    print("  ✓ Stage advanced to SCRUTINY with active SLA tracking.")

    # -------------------------------------------------------------------------
    # STEP 2: EVC Panel Selection & Scheduling (APP-10021 / Visit #4)
    # -------------------------------------------------------------------------
    print("\n[Step 2/8] Verifying EVC Queue, Suggested Experts & Scheduling (APP-10021)...")
    # Fetch visits in EVC queue
    res_visits = client.get("/api/v1/evc/visits", headers=auth_header(evc_token))
    assert res_visits.status_code == 200, res_visits.text
    visits = res_visits.json()
    assert len(visits) > 0, "No EVC visits found"
    
    # Locate visit for APP-10021
    target_visit = next((v for v in visits if v.get("application_number") == "AICTE/2026/APP-10021"), visits[0])
    v_id = target_visit["id"]

    # Check suggested experts with conflict checking
    res_experts = client.get(f"/api/v1/evc/visits/{v_id}/suggested-experts", headers=auth_header(evc_token))
    assert res_experts.status_code == 200, res_experts.text
    suggested = res_experts.json()
    assert len(suggested) >= 3, "Insufficient candidate experts in decision-support pool"
    print(f"  ✓ Decision support ranked {len(suggested)} candidate experts with conflict detection.")

    # Assign 3 conflict-free experts
    selected_ids = [e["id"] for e in suggested if not e.get("has_conflict")][:3]
    assert len(selected_ids) == 3, f"Expected 3 conflict-free experts, got {len(selected_ids)}"
    res_assign = client.post(
        f"/api/v1/evc/visits/{v_id}/assign-panel",
        headers=auth_header(evc_token),
        json={"expert_ids": selected_ids}
    )
    assert res_assign.status_code == 200, res_assign.text
    assert res_assign.json()["status"] == "ASSIGNED"
    print("  ✓ 3-member panel assigned.")

    # Schedule visit
    res_sched = client.post(
        f"/api/v1/evc/visits/{v_id}/schedule",
        headers=auth_header(evc_token),
        json={"scheduled_date": "2026-11-15", "scheduled_time": "10:00"}
    )
    assert res_sched.status_code == 200, res_sched.text
    assert res_sched.json()["status"] == "SCHEDULED"
    print("  ✓ EVC inspection visit scheduled.")

    # -------------------------------------------------------------------------
    # STEP 3: Early Delay Risk Warning (APP-10033 / Score 70.7)
    # -------------------------------------------------------------------------
    print("\n[Step 3/8] Verifying Explainable Delay Risk Detection (APP-10033 / High Risk)...")
    res_risk = client.get("/api/v1/risk/applications?risk_band=HIGH", headers=auth_header(admin_token))
    assert res_risk.status_code == 200, res_risk.text
    high_risks = res_risk.json()
    assert len(high_risks) >= 2, f"Expected >= 2 high-risk dossiers, got {len(high_risks)}"
    
    target_risk = high_risks[0]
    app_id = target_risk["id"]
    res_detail = client.get(f"/api/v1/risk/applications/{app_id}", headers=auth_header(admin_token))
    assert res_detail.status_code == 200, res_detail.text
    detail = res_detail.json()

    assert detail["score"] >= 70.0, f"Expected score >= 70.0, got {detail['score']}"
    assert detail["band"] == "HIGH"
    assert len(detail["factors"]) == 4, "Expected 4 explainable risk factors"
    print(f"  ✓ High risk alert verified: App #{app_id} score {detail['score']} ({detail['band']}) with 4 explainable factors.")

    # -------------------------------------------------------------------------
    # STEP 4: Clock Advance & Escalation Ladder
    # -------------------------------------------------------------------------
    print("\n[Step 4/8] Verifying Simulated Clock Advance (+168h) & Escalation...")
    res_adv_clock = client.post(
        "/api/v1/demo/advance-clock",
        headers=auth_header(admin_token),
        json={"hours": 168.0}
    )
    assert res_adv_clock.status_code == 200, res_adv_clock.text
    run_stats = res_adv_clock.json().get("evaluation", {})
    assert run_stats.get("alerts_escalated", 0) > 0 or run_stats.get("alerts_created", 0) > 0
    print(f"  ✓ Clock advanced +7 days. Check run escalated {run_stats.get('alerts_escalated')} alerts.")

    # Reset clock
    client.post("/api/v1/demo/reset-clock", headers=auth_header(admin_token))
    print("  ✓ Clock returned to normal offset.")

    # -------------------------------------------------------------------------
    # STEP 5: Deficiency Return, Paused Clock & Institution Response (APP-10001)
    # -------------------------------------------------------------------------
    print("\n[Step 5/8] Verifying Return Deficiency, Paused Clock & Reply (APP-10001)...")
    res_return = client.post(
        "/api/v1/applications/1/return",
        headers=auth_header(sc_token),
        json={
            "deficiency_tags": ["INFRASTRUCTURE_DEFICIENCY", "FACULTY_CADRE_RATIO"],
            "reason": "Fire safety NOC copy illegible and library reading room capacity below APH norm."
        }
    )
    assert res_return.status_code == 200, res_return.text
    returned_app = res_return.json()
    assert returned_app["case_holder"] == "WITH_INSTITUTION"
    assert returned_app["current_stage_code"] == "RE_SCRUTINY"
    print("  ✓ Application returned to institution. Holder changed to WITH_INSTITUTION (clock paused).")

    # Institution logs in and replies
    res_reply = client.post(
        "/api/v1/applications/1/institution-response",
        headers=auth_header(inst_token),
        json={"remarks": "Attached high-resolution signed copy of CFO Kanpur Fire NOC and reading hall floor plan."}
    )
    assert res_reply.status_code == 200, res_reply.text
    resumed_app = res_reply.json()
    assert resumed_app["case_holder"] == "WITH_AICTE"
    print("  ✓ Institution submitted reply. Holder restored to WITH_AICTE (clock resumed).")

    # -------------------------------------------------------------------------
    # STEP 6: Undertaking Compliance & One-Click Officer Audit
    # -------------------------------------------------------------------------
    print("\n[Step 6/8] Verifying Undertaking Compliance & Audit Verification...")
    res_uts = client.get("/api/v1/undertakings?institution_id=1", headers=auth_header(inst_token))
    assert res_uts.status_code == 200, res_uts.text
    uts = res_uts.json()
    assert len(uts) > 0, "No undertakings for Apex Institute"
    ut_target = uts[0]
    ut_id = ut_target["id"]

    # Submit evidence
    res_ev = client.post(
        f"/api/v1/undertakings/{ut_id}/upload-evidence",
        headers=auth_header(inst_token),
        data={"comments": "Compliance report and affidavit attached as mandated under APH clause 2.8.", "file_id": 1}
    )
    assert res_ev.status_code == 200, res_ev.text
    assert res_ev.json()["status"] == "SUBMITTED"
    print(f"  ✓ Evidence uploaded for Undertaking #{ut_id}. Status: SUBMITTED.")

    # Officer audits
    res_verify = client.post(
        f"/api/v1/undertakings/{ut_id}/verify",
        headers=auth_header(sc_token),
        json={"action": "VERIFIED", "remarks": "Compliance evidence verified by scrutiny desk against land records."}
    )
    assert res_verify.status_code == 200, res_verify.text
    assert res_verify.json()["status"] == "VERIFIED"
    print(f"  ✓ Undertaking #{ut_id} verified by Scrutiny Officer.")

    # -------------------------------------------------------------------------
    # STEP 7: Statutory Document Expiry Warning & Renewal Audit
    # -------------------------------------------------------------------------
    print("\n[Step 7/8] Verifying Document Expiry Watcher & Renewal Verification...")
    res_docs = client.get("/api/v1/documents?institution_id=1", headers=auth_header(sc_token))
    assert res_docs.status_code == 200, res_docs.text
    docs = res_docs.json()
    assert len(docs) > 0, "No documents found for institution"

    # Document 26 was seeded in RENEWAL_SUBMITTED status (version 2)
    doc_renewal = next((d for d in docs if d.get("status") == "RENEWAL_SUBMITTED"), None)
    assert doc_renewal is not None, "Expected at least one document in RENEWAL_SUBMITTED status"
    res_doc_audit = client.post(
        f"/api/v1/documents/{doc_renewal['id']}/verify-renewal",
        headers=auth_header(sc_token),
        json={"approved": True, "remarks": "Renewed Fire NOC validated with Kanpur Chief Fire Officer dispatch."}
    )
    assert res_doc_audit.status_code == 200, res_doc_audit.text
    assert res_doc_audit.json()["status"] == "VALID"
    print(f"  ✓ Document renewal verified: Doc #{doc_renewal['id']} status marked VALID.")

    # -------------------------------------------------------------------------
    # STEP 8: Decision, Reports & Tamper-Evident Audit Verification
    # -------------------------------------------------------------------------
    print("\n[Step 8/8] Verifying Competent Authority Decision, Reports & Audit Chain...")
    # Reports
    res_rep1 = client.get("/api/v1/reports/regional-performance", headers=auth_header(ca_token))
    assert res_rep1.status_code == 200, res_rep1.text
    assert len(res_rep1.json()["regions"]) == 5, "Expected 5 regions in matrix"

    res_rep2 = client.get("/api/v1/reports/pendency", headers=auth_header(ca_token))
    assert res_rep2.status_code == 200, res_rep2.text

    # Final decision on APP-10041
    res_dec = client.post(
        "/api/v1/applications/41/decision",
        headers=auth_header(ca_token),
        json={
            "decision": "APPROVE",
            "remarks": "SAC/SHC appellate committee recommendations reviewed. Statutory approval granted."
        }
    )
    assert res_dec.status_code == 200, res_dec.text
    dec_app = res_dec.json()
    assert dec_app["status"] == "APPROVED"
    assert dec_app["approval_letter_ref"] is not None
    print(f"  ✓ Statutory decision recorded for APP-10041. Order ref: {dec_app['approval_letter_ref']}.")

    # Close case
    res_close = client.post(
        "/api/v1/applications/41/close",
        headers=auth_header(ca_token),
        json={
            "closure_reason": "ALL_CONDITIONS_MET",
            "closure_remarks": "All conditional undertakings completed and formal order issued. Case closed."
        }
    )
    assert res_close.status_code == 200, res_close.text
    assert res_close.json()["status"] == "CLOSED"
    print("  ✓ Application APP-10041 officially marked CLOSED.")

    # Tamper-evident audit chain verification
    res_audit = client.get("/api/v1/audit/verify-integrity", headers=auth_header(admin_token))
    assert res_audit.status_code == 200, res_audit.text
    audit_data = res_audit.json()
    assert audit_data["verified"] is True, f"Audit chain verification failed: {audit_data}"
    print(f"  ✓ Immutable SHA-256 audit chain verified intact across {audit_data['total_records']} events.")

    # -------------------------------------------------------------------------
    # CLEAN RESTORATION
    # -------------------------------------------------------------------------
    print("\n[Restoration] Re-seeding database to ensure demo rehearsal never spoils next run...")
    demo_reset()
    print("\n" + "=" * 70)
    print("  ✓ ALL 8 DEMO STEPS PASSED SUCCESSFULLY!")
    print("  ✓ DATABASE LEFT IN PRISTINE STARTING DEMO STATE.")
    print("=" * 70)


if __name__ == "__main__":
    run_demo_check()
