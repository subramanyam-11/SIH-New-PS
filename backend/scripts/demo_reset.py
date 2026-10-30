"""
SIH26262 Demo Reset Utility
One-command demo reset:
1. Drops and recreates database schema.
2. Seeds foundation data and 60 live demo applications.
3. Resets demo clock offset to 0.
4. Evaluates alert rules, delay risk snapshots, and priority rankings.
5. Prints demo credentials and the exact application numbers for the 8 demo steps.
"""
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.reset_db import reset_database
from scripts.seed_demo import seed_demo_applications
from app.services.clock import reset_clock


def demo_reset():
    print("=" * 70)
    print("  SIH26262: AICTE APPROVAL WORKFLOW AUTOMATION - DEMO RESET")
    print("=" * 70)
    
    # 1. Reset clock to real time FIRST so all seeds and rules evaluate at 0h offset
    print("\n[Step 1/4] Resetting simulated demo clock to real time (0h offset)...")
    curr_time = reset_clock()
    print(f"✓ Clock reset successfully to UTC: {curr_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # 2. Reset database & apply schema
    print("\n[Step 2/4] Dropping and recreating schema + foundation data...")
    reset_database()

    # 3. Seed 60 demo applications & Phase 5/6/7/8 entities
    print("\n[Step 3/4] Seeding 60 demo applications and operational data...")
    seed_demo_applications()

    # 4. Display Demo Walkthrough Matrix
    print("\n[Step 4/4] Demo Environment Ready!")
    print("=" * 70)
    print("  8-STEP DEMO STORY REFERENCE (Apex Institute Thread - Kanpur, North)")
    print("=" * 70)
    
    steps = [
        (
            "1. New Submission & Auto-Path",
            "principal@apexkanpur.demo.example",
            "Institution User",
            "APP-10001 (App #1)",
            "Automatic routing to NEW_INSTITUTION stage path with initial scrutiny assignment."
        ),
        (
            "2. Scrutiny to EVC Scheduling",
            "scrutiny1@demo.example / evc.coord@demo.example",
            "Scrutiny / EVC Lead",
            "APP-10021 (App #21)",
            "Scrutiny clearance moves to EVC queue; 3-member conflict-free panel selected & scheduled."
        ),
        (
            "3. Early Delay Risk Warning",
            "ro.north@demo.example",
            "Regional Head (North)",
            "APP-10033 (App #33)",
            "Score 70.7 (High Risk). 4-factor explainable breakdown warns before SLA breach."
        ),
        (
            "4. Clock Advance & Escalation",
            "ro.north@demo.example / chairman@demo.example",
            "Regional Head / CA",
            "APP-10006 (App #6)",
            "+7 days advance fires Tier 2/3 escalation with explainable rule drawer."
        ),
        (
            "5. Deficiency & Paused Clock",
            "scrutiny1@demo.example / principal@apexkanpur.demo.example",
            "Scrutiny / Institution",
            "APP-10011 (App #11)",
            "Return to institution switches holder to WITH_INSTITUTION & pauses clock; reply resumes."
        ),
        (
            "6. Undertaking Compliance",
            "principal@apexkanpur.demo.example / scrutiny1@demo.example",
            "Institution / Scrutiny",
            "Undertaking #1 (Apex)",
            "Institution uploads compliance evidence; officer audits and verifies in one click."
        ),
        (
            "7. Expiring Document Renewal",
            "principal@apexkanpur.demo.example / scrutiny1@demo.example",
            "Institution / Scrutiny",
            "Document #1 (Lease Deed)",
            "Pre-expiry warning (<=30d). Renewal v2 uploaded; officer audit resolves alert."
        ),
        (
            "8. Decision, Reports & Audit",
            "chairman@demo.example",
            "Competent Authority",
            "APP-10041 (App #41)",
            "Regional performance matrix, approval order (LoA) with SAMPLE watermark, immutable audit chain."
        )
    ]

    for title, email, role, app_num, summary in steps:
        print(f"\n{title}:")
        print(f"  Application / Target: {app_num}")
        print(f"  Login Persona:        {role} ({email})")
        print(f"  Demo Action:          {summary}")

    print("\n" + "=" * 70)
    print("  DEFAULT PASSWORD FOR ALL DEMO ACCOUNTS: Password@123")
    print("  PRESENTER GUIDE AVAILABLE AT:           http://localhost:3000/demo")
    print("=" * 70)


if __name__ == "__main__":
    demo_reset()
