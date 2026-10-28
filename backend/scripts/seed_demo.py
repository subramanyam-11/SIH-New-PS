import os
import sys
from datetime import datetime, timedelta

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models import (
    Application, Institution, ApplicationCategory, StagePath, Stage,
    User, UserRoleEnum, ApplicationStatusEnum, StageStatusEnum, StageHistory,
    EvcVisit, EvcStatusEnum, Undertaking, UndertakingStatusEnum,
    Document, DocumentStatusEnum, DocumentTypeEnum, Alert, Notification, EmailOutbox
)
from app.services.clock import get_system_time, compute_stage_due_date
from app.services.workflow_engine import WorkflowEngine


def seed_demo_applications():
    db: Session = SessionLocal()
    try:
        print("=== SEEDING 60 DEMO APPLICATIONS (PHASE 3) ===")

        # Clean existing demo applications if re-running
        db.query(Application).delete()
        db.commit()

        # Fetch required reference data
        institutions = db.query(Institution).order_by(Institution.id).all()
        categories = db.query(ApplicationCategory).order_by(ApplicationCategory.id).all()
        paths = db.query(StagePath).order_by(StagePath.id).all()
        stages = db.query(Stage).all()
        stages_by_code = {s.code: s for s in stages}

        admin = db.query(User).filter(User.username == "admin@aicte.gov.in").first()
        chairman = db.query(User).filter(User.username == "chairman@aicte.gov.in").first()
        evc_coord = db.query(User).filter(User.username == "evc.coord@aicte.gov.in").first()

        scrutiny_map = {
            1: db.query(User).filter(User.username == "scrutiny1@aicte.gov.in").first(),
            2: db.query(User).filter(User.username == "scrutiny2@aicte.gov.in").first(),
            3: db.query(User).filter(User.username == "scrutiny3@aicte.gov.in").first(),
            4: db.query(User).filter(User.username == "scrutiny4@aicte.gov.in").first(),
            5: db.query(User).filter(User.username == "scrutiny5@aicte.gov.in").first(),
        }
        ro_map = {
            1: db.query(User).filter(User.username == "ro.north@aicte.gov.in").first(),
            2: db.query(User).filter(User.username == "ro.west@aicte.gov.in").first(),
            3: db.query(User).filter(User.username == "ro.south@aicte.gov.in").first(),
            4: db.query(User).filter(User.username == "ro.east@aicte.gov.in").first(),
            5: db.query(User).filter(User.username == "ro.central@aicte.gov.in").first(),
        }
        inst_user_map = {
            1: db.query(User).filter(User.username == "principal@apexkanpur.edu").first(),
            4: db.query(User).filter(User.username == "director@sahyadri.edu").first(),
            7: db.query(User).filter(User.username == "principal@kaveri.edu").first(),
            10: db.query(User).filter(User.username == "director@kalinga.edu").first(),
            13: db.query(User).filter(User.username == "principal@malwa.edu").first(),
        }

        now = get_system_time()

        # Pre-planned target distribution for 60 applications
        # (Target Stage, Count, Target SLA Buckets: [on_time, near_due, overdue])
        stage_targets = [
            ("SUBMITTED", 6, ["ON_TIME", "ON_TIME", "ON_TIME", "ON_TIME", "NEAR_DUE", "NEAR_DUE"]),
            ("SCRUTINY", 18, ["ON_TIME"] * 9 + ["NEAR_DUE"] * 5 + ["OVERDUE"] * 4),
            ("RE_SCRUTINY", 8, ["ON_TIME"] * 4 + ["NEAR_DUE"] * 2 + ["OVERDUE"] * 2),
            ("EVC_PENDING", 10, ["ON_TIME"] * 5 + ["NEAR_DUE"] * 3 + ["OVERDUE"] * 2),
            ("EVC_SCHEDULED", 6, ["ON_TIME"] * 3 + ["NEAR_DUE"] * 2 + ["OVERDUE"] * 1),
            ("SAC_SHC_REVIEW", 7, ["ON_TIME"] * 4 + ["NEAR_DUE"] * 1 + ["OVERDUE"] * 2),
            ("APPROVAL_GRANTED", 4, ["COMPLETED"] * 4),
            ("APPROVAL_REJECTED", 1, ["COMPLETED"] * 1),
        ]

        app_idx = 1
        created_count = 0

        for target_stage, count, bucket_list in stage_targets:
            for i in range(count):
                bucket = bucket_list[i]
                app_num = f"AICTE/2026/APP-{10000 + app_idx:05d}"
        def get_actor_for_stage(stage, inst):
            role = stage.responsible_role
            if role == UserRoleEnum.SCRUTINY_OFFICER:
                return scrutiny_map.get(inst.region_id, scrutiny_map[1])
            elif role == UserRoleEnum.REGIONAL_HEAD:
                return ro_map.get(inst.region_id, ro_map[1])
            elif role == UserRoleEnum.EVC_COORDINATOR:
                return evc_coord
            elif role == UserRoleEnum.COMPETENT_AUTHORITY:
                return chairman
            elif role == UserRoleEnum.INSTITUTION_USER:
                return inst_user_map.get(inst.id, admin)
            return admin

        app_idx = 1
        created_count = 0

        for target_stage, count, bucket_list in stage_targets:
            for i in range(count):
                bucket = bucket_list[i]
                app_num = f"AICTE/2026/APP-{10000 + app_idx:05d}"
                inst = institutions[(app_idx - 1) % len(institutions)]
                cat = categories[(app_idx - 1) % len(categories)]

                # Select an appropriate path containing target_stage
                if target_stage == "SUBMITTED":
                    path = paths[(app_idx - 1) % len(paths)]
                elif target_stage in ["SCRUTINY", "RE_SCRUTINY"]:
                    eligible_paths = [p for p in paths if "SCRUTINY" in p.stage_sequence]
                    path = eligible_paths[(app_idx - 1) % len(eligible_paths)]
                elif target_stage in ["EVC_PENDING", "EVC_SCHEDULED"]:
                    eligible_paths = [p for p in paths if target_stage in p.stage_sequence]
                    path = eligible_paths[(app_idx - 1) % len(eligible_paths)]
                elif target_stage == "SAC_SHC_REVIEW":
                    eligible_paths = [p for p in paths if "SAC_SHC_REVIEW" in p.stage_sequence]
                    path = eligible_paths[(app_idx - 1) % len(eligible_paths)]
                else:  # APPROVAL_GRANTED, APPROVAL_REJECTED
                    path = paths[(app_idx - 1) % len(paths)]

                # Base submission backdated
                sub_time = now - timedelta(days=25 + (app_idx % 10))

                inst_user = inst_user_map.get(inst.id, admin)
                assigned_officer = scrutiny_map.get(inst.region_id, scrutiny_map[1])

                # Submit application
                app = WorkflowEngine.submit_application(
                    db=db,
                    actor=inst_user,
                    institution_id=inst.id,
                    category_id=cat.id,
                    application_number=app_num,
                    stage_path_id=path.id,
                    submission_time=sub_time
                )

                app.assigned_officer_id = assigned_officer.id
                db.flush()

                # Advance through stages to reach target stage
                current_sim_time = sub_time

                if target_stage == "SUBMITTED":
                    pass

                elif target_stage == "RE_SCRUTINY":
                    current_sim_time += timedelta(days=2)
                    WorkflowEngine.complete_stage(
                        db=db, application_id=app.id, actor=assigned_officer,
                        remarks="Dossier scrutinized", transition_time=current_sim_time
                    )
                    current_sim_time += timedelta(days=4)

                    if app_idx == 27:
                        # Revert 1
                        WorkflowEngine.return_application(
                            db=db, application_id=app.id, actor=assigned_officer,
                            deficiency_tags=["DEF_LAND_TITLE", "DEF_FIRE_NOC"],
                            reason="Land title registry proof not provided; Fire safety certificate expired.",
                            revert_time=current_sim_time
                        )
                        current_sim_time += timedelta(days=3)
                        WorkflowEngine.complete_stage(
                            db=db, application_id=app.id, actor=inst_user,
                            remarks="Uploaded renewed Fire NOC and municipal deed.",
                            transition_time=current_sim_time
                        )
                        current_sim_time += timedelta(days=2)
                        WorkflowEngine.return_application(
                            db=db, application_id=app.id, actor=assigned_officer,
                            deficiency_tags=["DEF_FACULTY_CADRE", "DEF_OTHER"],
                            reason="Cadre ratio for Department of Mechanical Engineering has 0 Professors. Other: Affidavit format is incomplete.",
                            revert_time=current_sim_time
                        )
                    else:
                        WorkflowEngine.return_application(
                            db=db, application_id=app.id, actor=assigned_officer,
                            deficiency_tags=["DEF_FIRE_NOC"] if app_idx % 2 == 0 else ["DEF_LAND_TITLE", "DEF_INFRASTRUCTURE"],
                            reason="Fire safety certificate not renewed from local authority." if app_idx % 2 == 0 else "Instructional area deficient by 420 sq.m for requested intake.",
                            revert_time=current_sim_time
                        )

                elif target_stage in ["APPROVAL_GRANTED", "APPROVAL_REJECTED"]:
                    seq = app.stage_path.stage_sequence
                    forward_seq = [s for s in seq if s != "RE_SCRUTINY"]
                    final_pre_idx = len(forward_seq) - 2
                    for step_idx in range(final_pre_idx):
                        curr_stage_obj = stages_by_code[forward_seq[step_idx]]
                        actor = get_actor_for_stage(curr_stage_obj, inst)
                        current_sim_time += timedelta(days=3)
                        WorkflowEngine.complete_stage(
                            db=db, application_id=app.id, actor=actor,
                            remarks=f"Statutory requirements completed for {curr_stage_obj.name}",
                            transition_time=current_sim_time
                        )

                    # Now at final pre-decision stage, Competent Authority records decision
                    current_sim_time += timedelta(days=2)
                    dec = "APPROVE" if target_stage == "APPROVAL_GRANTED" else "REJECT"
                    rem = (
                        "All statutory norms verified in compliance with APH 2026. Extension of Approval granted."
                        if dec == "APPROVE"
                        else "Fatal non-compliance with APH Chapter I Clause 1.4: Title to campus land is encumbered and in dispute."
                    )
                    WorkflowEngine.record_decision(
                        db=db, application_id=app.id, actor=chairman,
                        decision=dec, remarks=rem, decision_time=current_sim_time
                    )

                else:
                    seq = app.stage_path.stage_sequence
                    forward_seq = [s for s in seq if s != "RE_SCRUTINY"]
                    target_idx = forward_seq.index(target_stage)
                    for step_idx in range(target_idx):
                        curr_stage_obj = stages_by_code[forward_seq[step_idx]]
                        actor = get_actor_for_stage(curr_stage_obj, inst)
                        current_sim_time += timedelta(days=3)
                        WorkflowEngine.complete_stage(
                            db=db, application_id=app.id, actor=actor,
                            remarks=f"Statutory review completed for stage {curr_stage_obj.name}",
                            transition_time=current_sim_time
                        )

                # Adjust current active stage timestamps to match target SLA bucket
                if target_stage not in ["APPROVAL_GRANTED", "APPROVAL_REJECTED"]:
                    sla_days = app.current_stage.default_sla_days
                    if bucket == "ON_TIME":
                        app.stage_entered_at = now - timedelta(days=1, hours=4)
                        app.stage_due_date = app.stage_entered_at + timedelta(days=sla_days)
                    elif bucket == "NEAR_DUE":
                        dwell_days = max(1.0, sla_days * 0.85)
                        app.stage_entered_at = now - timedelta(days=dwell_days)
                        app.stage_due_date = app.stage_entered_at + timedelta(days=sla_days)
                    elif bucket == "OVERDUE":
                        overdue_days = 2.5 + (app_idx % 3)
                        app.stage_entered_at = now - timedelta(days=sla_days + overdue_days)
                        app.stage_due_date = app.stage_entered_at + timedelta(days=sla_days)

                    # Dynamic delay risk score
                    if bucket == "OVERDUE":
                        app.delay_risk_score = min(0.95, round(0.75 + (app_idx % 5) * 0.04, 2))
                        app.risk_factors = ["Statutory stage SLA breached", "Pending desk action exceeds allowable window"]
                    elif bucket == "NEAR_DUE":
                        app.delay_risk_score = min(0.72, round(0.50 + (app_idx % 5) * 0.04, 2))
                        app.risk_factors = ["Approaching SLA threshold (within 48h)"]
                    else:
                        app.delay_risk_score = round(0.12 + (app_idx % 4) * 0.05, 2)
                        app.risk_factors = []

                    open_hist = db.query(StageHistory).filter(
                        StageHistory.application_id == app.id,
                        StageHistory.completed_at == None
                    ).order_by(StageHistory.id.desc()).first()
                    if open_hist:
                        open_hist.entered_at = app.stage_entered_at
                        open_hist.due_date = app.stage_due_date

                db.commit()
                created_count += 1
                app_idx += 1

        print(f"✓ Successfully seeded {created_count} applications (APP-10001 to APP-10060) across 5 regions!")

        # =========================================================================
        # 2. SEED EVC VISITS (~12 records in mixed states)
        # =========================================================================
        print("\n--- Seeding 12 EVC Inspection Visits ---")
        db.query(EvcVisit).delete()
        db.commit()

        # Find applications in EVC stages
        evc_pending_apps = db.query(Application).filter(Application.current_stage.has(code="EVC_PENDING")).all()
        evc_sched_apps = db.query(Application).filter(Application.current_stage.has(code="EVC_SCHEDULED")).all()
        evc_other_apps = db.query(Application).filter(Application.current_stage.has(code="SAC_SHC_REVIEW")).all()

        evc_records = [
            # 1-4: Unscheduled (Pending scheduling)
            (evc_pending_apps[0].id if len(evc_pending_apps) > 0 else 1, EvcStatusEnum.PENDING_SCHEDULE, None, "PHYSICAL", None, None, None),
            (evc_pending_apps[1].id if len(evc_pending_apps) > 1 else 2, EvcStatusEnum.PENDING_SCHEDULE, None, "PHYSICAL", None, None, None),
            (evc_pending_apps[2].id if len(evc_pending_apps) > 2 else 3, EvcStatusEnum.PENDING_SCHEDULE, None, "SURPRISE", None, None, None),
            (evc_pending_apps[3].id if len(evc_pending_apps) > 3 else 4, EvcStatusEnum.PENDING_SCHEDULE, None, "VIRTUAL", None, None, None),

            # 5-7: Scheduled soon (in next 3-7 days)
            (evc_sched_apps[0].id if len(evc_sched_apps) > 0 else 5, EvcStatusEnum.SCHEDULED, now.date() + timedelta(days=3), "PHYSICAL", "Prof. R. C. Sharma", [{"name": "Dr. P. Sen", "role": "Architectural Expert"}], None),
            (evc_sched_apps[1].id if len(evc_sched_apps) > 1 else 6, EvcStatusEnum.SCHEDULED, now.date() + timedelta(days=5), "PHYSICAL", "Dr. Anita Desai", [{"name": "Prof. S. K. Roy", "role": "Senior Cadre Expert"}], None),
            (evc_sched_apps[2].id if len(evc_sched_apps) > 2 else 7, EvcStatusEnum.SCHEDULED, now.date() + timedelta(days=7), "VIRTUAL", "Prof. M. K. Nair", [{"name": "Dr. G. Rao", "role": "Lab Evaluator"}], None),

            # 8-9: Overdue (Scheduled date was in past, but not completed yet)
            (evc_sched_apps[3].id if len(evc_sched_apps) > 3 else 8, EvcStatusEnum.SCHEDULED, now.date() - timedelta(days=4), "PHYSICAL", "Prof. V. Raman", [{"name": "Dr. A. Verma", "role": "Infrastructural Specialist"}], "Visit delayed due to local transit breakdown"),
            (evc_sched_apps[4].id if len(evc_sched_apps) > 4 else 9, EvcStatusEnum.SCHEDULED, now.date() - timedelta(days=6), "PHYSICAL", "Dr. Sunita Kapoor", [{"name": "Prof. B. Ghosh", "role": "Equipment Auditor"}], "Rescheduling requested by institution"),

            # 10-12: Completed / Report uploaded
            (evc_other_apps[0].id if len(evc_other_apps) > 0 else 10, EvcStatusEnum.REPORT_SUBMITTED, now.date() - timedelta(days=10), "PHYSICAL", "Prof. H. S. Chahal", [{"name": "Dr. R. Gupta", "role": "Civil Eng."}], "RECOMMENDED"),
            (evc_other_apps[1].id if len(evc_other_apps) > 1 else 11, EvcStatusEnum.REPORT_SUBMITTED, now.date() - timedelta(days=12), "PHYSICAL", "Prof. Y. K. Mehta", [{"name": "Dr. T. Joseph", "role": "Academic Dean"}], "DEFICIENCIES_FOUND"),
            (evc_other_apps[2].id if len(evc_other_apps) > 2 else 12, EvcStatusEnum.VISIT_COMPLETED, now.date() - timedelta(days=2), "PHYSICAL", "Prof. K. Venkatesh", [{"name": "Dr. M. Ali", "role": "Faculty Expert"}], "RECOMMENDED"),
        ]

        for app_id, st, sdate, vtype, chair, experts, outcome in evc_records:
            evc = EvcVisit(
                application_id=app_id,
                status=st,
                coordinator_id=evc_coord.id if evc_coord else None,
                scheduled_date=sdate,
                visit_type=vtype,
                committee_chair=chair,
                committee_experts=experts or [],
                outcome_recommendation=outcome if outcome in ["RECOMMENDED", "DEFICIENCIES_FOUND", "REJECTED"] else None,
                remarks=outcome if outcome and outcome not in ["RECOMMENDED", "DEFICIENCIES_FOUND", "REJECTED"] else None,
                report_uploaded_at=now - timedelta(days=8) if st == EvcStatusEnum.REPORT_SUBMITTED else None,
                report_file_url=f"/reports/evc_app_{app_id}.pdf" if st == EvcStatusEnum.REPORT_SUBMITTED else None,
            )
            db.add(evc)
        db.commit()
        print("✓ Seeded 12 EVC inspection records.")

        # =========================================================================
        # 3. SEED UNDERTAKINGS (~20 records across all states)
        # =========================================================================
        print("\n--- Seeding 20 Conditional Undertakings ---")
        db.query(Undertaking).delete()
        db.commit()

        undertaking_templates = [
            ("Barrier-Free Ramp & Divyangjan Lift Construction", "Complete construction of dedicated elevator and entrance ramps per Chapter VII accessibility standards.", 75, UndertakingStatusEnum.PENDING_SUBMISSION),
            ("Fire Suppression Hydrant System Installation", "Procure and commission overhead pressurized hydrant ring with NOC renewal.", 85, UndertakingStatusEnum.PENDING_SUBMISSION),
            ("Digital Library e-Subscription Bandwidth Augmentation", "Upgrade campus-wide high-speed internet lease line to 500 Mbps and renew IEEE access.", 60, UndertakingStatusEnum.PENDING_SUBMISSION),
            ("Cadre Ratio Rectification - Professor Cadre Appointment", "Recruit 2 regular Cadre Professors in Computer Science per AICTE 1:2:6 ratio.", 90, UndertakingStatusEnum.PENDING_SUBMISSION),
            ("Language Laboratory Software Licensing", "Install 60-seat interactive multimedia language lab licenses.", 70, UndertakingStatusEnum.PENDING_SUBMISSION),
            ("Sewage Treatment Plant & Rainwater Harvesting Pit", "Complete commissioning of 50 KLD STP unit and recharge ground water borewells.", 65, UndertakingStatusEnum.PENDING_SUBMISSION),

            # Due soon (<= 15 days) -> fires RULE_UNDERTAKING_DUE_15D
            ("Solar Rooftop PV Array 50kW Grid Interconnection", "Grid synchronisation certificate submission to Regional Office.", 8, UndertakingStatusEnum.PENDING_SUBMISSION),
            ("Girls Hostel CCTV Surveillance Ring Setup", "Install 32 IP cameras covering perimeter boundary wall.", 11, UndertakingStatusEnum.PENDING_SUBMISSION),
            ("Internal Complaint Committee (ICC) Compliance Report", "Submit annual ICC report and workshop completion registers.", 5, UndertakingStatusEnum.PENDING_SUBMISSION),
            ("Anti-Ragging Committee Statutory Undertaking", "Affidavit collection from 100% newly enrolled students.", 14, UndertakingStatusEnum.PENDING_SUBMISSION),
            ("Safety Glass Glazing in Chemistry Labs", "Replace window panes with reinforced toughened shatter-proof glass.", 4, UndertakingStatusEnum.PENDING_SUBMISSION),
            ("Bio-Waste Disposal MoU Renewal", "Execution of biomedical waste clearance MoU with municipal vendor.", 12, UndertakingStatusEnum.PENDING_SUBMISSION),

            # Overdue (past due date)
            ("CAD/CAM Simulator Lab Machinery Delivery", "Commissioning report for 5-axis CNC machining center.", -6, UndertakingStatusEnum.OVERDUE),
            ("Faculty Pay Scale Implementation 7th CPC", "Compliance certificate of 7th Pay Commission salary disbursement.", -12, UndertakingStatusEnum.OVERDUE),
            ("Girls Common Room Dedicated Facility Expansion", "Carpet area expansion from 50 sqm to 100 sqm with attached sanitised restrooms.", -4, UndertakingStatusEnum.OVERDUE),
            ("Backup Generator 125 kVA Silent DG Set Setup", "CPCB pollution clearance certificate for acoustic DG enclosure.", -18, UndertakingStatusEnum.OVERDUE),

            # Fulfilled (Complied)
            ("Smart Classroom Projector & AV Equipment", "Installation of 10 interactive smart boards in lecture theatre blocks.", -30, UndertakingStatusEnum.COMPLIED),
            ("Internet Protocol CCTV Integration with AICTE Portal", "Live streaming RTSP link integration with central AICTE server.", -45, UndertakingStatusEnum.COMPLIED),
            ("Alumni Endowment Fund Corpus Deposit", "Statutory deposit of INR 25 Lakh in scheduled commercial bank FDR.", -60, UndertakingStatusEnum.COMPLIED),
            ("Sports Complex Indoor Badminton Court Renovation", "Rubberized wooden flooring laid in multipurpose gymnasium.", -20, UndertakingStatusEnum.COMPLIED),
        ]

        all_apps = db.query(Application).order_by(Application.id).all()
        for i, (title, desc, day_offset, ustatus) in enumerate(undertaking_templates):
            app = all_apps[i % len(all_apps)]
            inst_id = app.institution_id
            ut = Undertaking(
                application_id=app.id,
                institution_id=inst_id,
                condition_title=title,
                description=desc,
                due_date=now.date() + timedelta(days=day_offset),
                status=ustatus,
                assigned_verifier_id=scrutiny_map.get(app.region_id, scrutiny_map[1]).id if scrutiny_map.get(app.region_id) else None,
                verified_at=now - timedelta(days=10) if ustatus == UndertakingStatusEnum.COMPLIED else None,
                verification_remarks="Documentary proof verified and found compliant per norms." if ustatus == UndertakingStatusEnum.COMPLIED else None,
            )
            db.add(ut)
        db.commit()
        print("✓ Seeded 20 conditional undertakings.")

        # =========================================================================
        # 4. SEED STATUTORY DOCUMENTS (~25 records across all expiry profiles)
        # =========================================================================
        print("\n--- Seeding 25 Statutory Documents (Leases, Fire NOCs, FDRs) ---")
        db.query(Document).delete()
        db.commit()

        doc_templates = [
            # Valid long term (> 180 days)
            (DocumentTypeEnum.LAND_LEASE_DEED, "Reg. Lease Deed Vol 429/18", "Registered 99-Year Land Lease Deed", "Sub-Registrar Office, Kanpur", -3650, 720, DocumentStatusEnum.ACTIVE),
            (DocumentTypeEnum.BUILDING_PLAN_APPROVAL, "KDA/BP/2021/881", "Sanctioned Master Plan & Structural Drawing", "Kanpur Development Authority", -1800, 1800, DocumentStatusEnum.ACTIVE),
            (DocumentTypeEnum.OCCUPANCY_CERTIFICATE, "PWD/OC/2022/410", "Final Occupancy Certificate - Main Academic Block", "Public Works Department (PWD)", -1200, 1500, DocumentStatusEnum.ACTIVE),
            (DocumentTypeEnum.AICTE_FDR_GUARANTEE, "SBI/FDR/2024/9912", "Joint FDR Deposit in Favor of AICTE (INR 35L)", "State Bank of India", -700, 400, DocumentStatusEnum.ACTIVE),
            (DocumentTypeEnum.AFFILIATING_UNIVERSITY_NOC, "AKTU/AFF/2025/11", "Annual Affiliation Continuation NOC", "Dr. A.P.J. Abdul Kalam Technical University", -300, 200, DocumentStatusEnum.ACTIVE),
            (DocumentTypeEnum.LAND_LEASE_DEED, "MU/LEASE/2019/55", "Perpetual Educational Land Lease Deed", "District Collectorate, Pune", -2500, 950, DocumentStatusEnum.ACTIVE),
            (DocumentTypeEnum.FIRE_SAFETY_NOC, "FS/BOM/2025/71", "Fire Safety Compliance Certificate", "Mumbai Fire Brigade HQ", -100, 265, DocumentStatusEnum.ACTIVE),

            # Expiring in 60-90 days -> triggers RULE_LEASE_90D
            (DocumentTypeEnum.LAND_LEASE_DEED, "REG/LEASE/1996/401", "30-Year Registered Land Lease Deed", "Sub-Registrar Sadar, Lucknow", -10800, 75, DocumentStatusEnum.ACTIVE),
            (DocumentTypeEnum.LAND_LEASE_DEED, "TN/CH/1996/1209", "30-Year Land Lease Deed - South Campus", "Sub-Registrar Guindy, Chennai", -10800, 80, DocumentStatusEnum.ACTIVE),
            (DocumentTypeEnum.LAND_LEASE_DEED, "WB/KOL/1996/89", "Educational Land Lease Agreement", "Registrar of Assurances, Kolkata", -10800, 70, DocumentStatusEnum.ACTIVE),
            (DocumentTypeEnum.AICTE_FDR_GUARANTEE, "PNB/FDR/2021/334", "Joint FDR Guarantee Certificate", "Punjab National Bank", -1800, 85, DocumentStatusEnum.ACTIVE),
            (DocumentTypeEnum.LAND_LEASE_DEED, "MP/IND/1996/711", "30-Year Registered Educational Lease", "District Registrar, Indore", -10800, 65, DocumentStatusEnum.ACTIVE),

            # Expiring in 15-30 days -> triggers RULE_LEASE_30D
            (DocumentTypeEnum.LAND_LEASE_DEED, "UP/NOIDA/1996/502", "30-Year Institutional Land Lease Deed", "Noida Authority Lease Office", -10920, 22, DocumentStatusEnum.ACTIVE),
            (DocumentTypeEnum.LAND_LEASE_DEED, "KA/BLR/1996/1101", "30-Year Registered Lease Agreement", "Sub-Registrar Jayanagar, Bengaluru", -10920, 18, DocumentStatusEnum.ACTIVE),
            (DocumentTypeEnum.FIRE_SAFETY_NOC, "FS/KAN/2025/309", "Annual Fire Safety Clearance Certificate", "Chief Fire Officer, Kanpur", -345, 20, DocumentStatusEnum.ACTIVE),
            (DocumentTypeEnum.AICTE_FDR_GUARANTEE, "BOB/FDR/2021/77", "Institutional FDR Guarantee Deposit", "Bank of Baroda", -1800, 25, DocumentStatusEnum.ACTIVE),
            (DocumentTypeEnum.LAND_LEASE_DEED, "MH/PUN/1996/331", "30-Year Land Title Lease Deed", "Sub-Registrar Haveli, Pune", -10920, 15, DocumentStatusEnum.ACTIVE),

            # Expired -> triggers RULE_FIRE_NOC_EXPIRED
            (DocumentTypeEnum.FIRE_SAFETY_NOC, "FS/LKO/2024/991", "Provisional Fire NOC", "Uttar Pradesh Fire Services", -400, -15, DocumentStatusEnum.EXPIRED),
            (DocumentTypeEnum.FIRE_SAFETY_NOC, "FS/CHN/2024/442", "Building Fire Protection Certificate", "Tamil Nadu Fire & Rescue Services", -420, -35, DocumentStatusEnum.EXPIRED),
            (DocumentTypeEnum.FIRE_SAFETY_NOC, "FS/KOL/2024/110", "Periodic Fire Safety NOC", "West Bengal Fire & Emergency Services", -380, -10, DocumentStatusEnum.EXPIRED),
            (DocumentTypeEnum.FIRE_SAFETY_NOC, "FS/BPL/2024/552", "Statutory Fire Clearance", "Bhopal Municipal Corporation Fire Dept", -410, -25, DocumentStatusEnum.EXPIRED),
            (DocumentTypeEnum.FIRE_SAFETY_NOC, "FS/MUM/2024/883", "Fire NOC - High Rise Academic Block", "Maharashtra Fire Service", -450, -45, DocumentStatusEnum.EXPIRED),

            # Renewed / Superseded
            (DocumentTypeEnum.FIRE_SAFETY_NOC, "FS/KAN/2024/101", "Expired Old Fire NOC", "Chief Fire Officer, Kanpur", -730, -365, DocumentStatusEnum.SUPERSEDED),
            (DocumentTypeEnum.FIRE_SAFETY_NOC, "FS/PUN/2025/999", "Fire NOC Renewal Application Docket", "Pune Municipal Fire Dept", -360, 5, DocumentStatusEnum.RENEWAL_SUBMITTED),
            (DocumentTypeEnum.LAND_LEASE_DEED, "OLD/LEASE/1990/01", "Archived First Land Lease Deed", "Sub-Registrar Sadar", -13000, -2000, DocumentStatusEnum.SUPERSEDED),
        ]

        for i, (dtype, dnum, title, auth, start_offset, expiry_offset, dstatus) in enumerate(doc_templates):
            inst_id = (i % 15) + 1
            app = db.query(Application).filter(Application.institution_id == inst_id).first()
            doc = Document(
                institution_id=inst_id,
                application_id=app.id if app else None,
                document_type=dtype,
                document_number=dnum,
                title=title,
                issuing_authority=auth,
                issue_date=now.date() + timedelta(days=start_offset),
                expiry_date=now.date() + timedelta(days=expiry_offset),
                status=dstatus,
                file_url=f"/documents/doc_{i+1}.pdf",
                last_verified_at=now - timedelta(days=30),
            )
            db.add(doc)
        db.commit()
        print("✓ Seeded 25 statutory documents (valid, near-expiry, expired).")

        # =========================================================================
        # 5. INITIALIZE ALERT RULES ENGINE EVALUATION (First Run)
        # =========================================================================
        print("\n--- Running Alert Rules Engine & Escalation Ladder ---")
        from app.services.scheduler import run_checks_now
        eval_result = run_checks_now(triggered_by="SEED_DEMO")
        print(f"✓ Initial alert evaluation finished in {eval_result.get('duration_ms')}ms")
        print(f"  Rules evaluated: {eval_result.get('rules_evaluated')}")
        print(f"  Alerts created:  {eval_result.get('alerts_created')}")
        print(f"  Alerts upgraded: {eval_result.get('alerts_upgraded')}")
        print(f"  Alerts resolved: {eval_result.get('alerts_resolved')}")
        print(f"  Escalations:     {eval_result.get('alerts_escalated')}")

        # Fetch and print alert summary breakdown
        from app.models import Alert
        open_alerts = db.query(Alert).filter(Alert.status.in_([
            "ACTIVE", "ACKNOWLEDGED", "SNOOZED", "ESCALATED"
        ])).all()
        print(f"\nTotal Open Alerts in Database: {len(open_alerts)}")

        sev_counts = {}
        rule_counts = {}
        tier_counts = {}
        for a in open_alerts:
            sev_counts[a.severity.value] = sev_counts.get(a.severity.value, 0) + 1
            rule_counts[a.rule.code if a.rule else a.alert_type.value] = rule_counts.get(a.rule.code if a.rule else a.alert_type.value, 0) + 1
            t_key = f"Tier {a.escalation_tier or 1}"
            tier_counts[t_key] = tier_counts.get(t_key, 0) + 1

        print(f"  By Severity: {sev_counts}")
        print(f"  By Tier:     {tier_counts}")
        print(f"  By Rule:     {rule_counts}")

        print("\n=== DEMO DATA SEED COMPLETED SUCCESSFULLY ===")

    except Exception as e:
        db.rollback()
        print(f"Error seeding demo applications: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_applications()
