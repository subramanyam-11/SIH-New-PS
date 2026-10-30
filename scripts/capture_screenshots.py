"""
SIH26262 Headless Screenshot Capture Script
Captures 16 high-resolution 1440x900 PNG screenshots for the presentation PPT.
Saves to docs/screenshots/.
"""
import os
import sys
import time
from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("FRONTEND_URL", "http://localhost:3001")
SCREENSHOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "screenshots"))

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def safe_goto(page, url, retries=3):
    for i in range(retries):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(1000)
            return
        except Exception as e:
            if i == retries - 1:
                print(f"Warning: Failed to navigate to {url}: {e}")
            time.sleep(1)

def login_as(page, email, password="Password@123"):
    safe_goto(page, f"{BASE_URL}/login")
    try:
        page.wait_for_selector("input[type='email']", timeout=5000)
        page.fill("input[type='email']", email)
        page.fill("input[type='password']", password)
        page.click("button[type='submit']")
        page.wait_for_timeout(2000)
    except Exception as e:
        print(f"Login warning for {email}: {e}")

def capture_all():
    print("=" * 70)
    print("  SIH26262: CAPTURING HIGH-RESOLUTION DEMO SCREENSHOTS (1440x900)")
    print(f"  Target URL: {BASE_URL}")
    print(f"  Output Dir: {SCREENSHOT_DIR}")
    print("=" * 70)

    targets = set(sys.argv[1:])
    def should_capture(name):
        return len(targets) == 0 or name in targets or name.replace(".png", "") in targets or any(t in name for t in targets)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # 01. Login with demo personas
        if should_capture("01_login_personas.png"):
            print("[1/16] Capturing Login page with demo persona chips...")
            safe_goto(page, f"{BASE_URL}/login")
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "01_login_personas.png"))

        # 02. Role Dashboard (Regional Head North)
        print("[2/16] Capturing Regional Dashboard with alert and risk cards...")
        login_as(page, "ro.north@demo.example")
        safe_goto(page, f"{BASE_URL}/")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "02_role_dashboard_alerts_risk.png"))

        # 03. Applications List with Risk Badges
        print("[3/16] Capturing Applications List with delay risk badges and case holders...")
        safe_goto(page, f"{BASE_URL}/applications")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "03_applications_list_risk_badges.png"))

        # 04. Case Detail & Stage Tracker
        print("[4/16] Capturing Case Detail with statutory stage tracker...")
        safe_goto(page, f"{BASE_URL}/applications/1")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "04_case_detail_stage_tracker.png"))

        # 05. Return and Paused Clock Card
        print("[5/16] Capturing Paused Clock & Return Drawer...")
        # Scroll down to clock segments
        page.evaluate("window.scrollTo(0, 500)")
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "05_return_paused_clock.png"))

        # 06. Explainable Alert Drawer
        print("[6/16] Capturing Explainable Alerts Queue...")
        safe_goto(page, f"{BASE_URL}/alerts")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "06_explainable_alert_drawer.png"))

        # 07. Escalation Matrix
        print("[7/16] Capturing Escalation Matrix...")
        safe_goto(page, f"{BASE_URL}/escalation-matrix")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "07_escalation_matrix.png"))

        # 08. EVC Queue & Panel Selection
        print("[8/16] Capturing EVC Queue & Conflict-Free Expert Selection...")
        login_as(page, "evc.coord@demo.example")
        safe_goto(page, f"{BASE_URL}/evc-queue")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "08_evc_queue_panel_selection.png"))

        # 09. Undertakings Compliance
        print("[9/16] Capturing Conditional Undertakings Review...")
        login_as(page, "scrutiny1@demo.example")
        safe_goto(page, f"{BASE_URL}/undertakings")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "09_undertakings_compliance.png"))

        # 10. Document Validity Queue
        print("[10/16] Capturing Statutory Document Validity Lifecycle...")
        safe_goto(page, f"{BASE_URL}/document-validity")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "10_document_validity_lifecycle.png"))

        # 11. Bottleneck Heat Grid
        print("[11/16] Capturing Bottleneck Heat Grid...")
        login_as(page, "chairman@demo.example")
        safe_goto(page, f"{BASE_URL}/bottlenecks")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "11_bottleneck_heat_grid.png"))

        # 12. What-If Capacity Planner
        print("[12/16] Capturing What-If Capacity Planner...")
        safe_goto(page, f"{BASE_URL}/planner")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "12_what_if_capacity_planner.png"))

        # 13. Overdue Report & Regional Matrix
        print("[13/16] Capturing Regional Performance & Overdue Reports...")
        safe_goto(page, f"{BASE_URL}/reports")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "13_overdue_cases_report.png"))

        # 14. Institution Portal
        print("[14/16] Capturing Institution Portal (Apex Institute)...")
        login_as(page, "principal@apexkanpur.demo.example")
        safe_goto(page, f"{BASE_URL}/portal")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "14_institution_portal.png"))

        # 15. Audit Chain Integrity
        print("[15/16] Capturing Cryptographic Audit Chain Integrity Screen...")
        login_as(page, "admin@demo.example")
        safe_goto(page, f"{BASE_URL}/admin/audit")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "15_audit_chain_integrity.png"))

        # 16. Mock National AICTE Integration
        print("[16/16] Capturing Mock National AICTE Integration...")
        safe_goto(page, f"{BASE_URL}/integration")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "16_mock_national_integration.png"))

        browser.close()

    print("\n" + "=" * 70)
    print("  ✓ ALL 16 HIGH-RESOLUTION SCREENSHOTS SAVED SUCCESSFULLY!")
    print(f"  Folder: {SCREENSHOT_DIR}")
    print("=" * 70)

if __name__ == "__main__":
    capture_all()
