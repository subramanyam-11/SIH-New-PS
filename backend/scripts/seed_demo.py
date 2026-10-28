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
    EvcVisit, EvcStatusEnum, EvcExpert, Undertaking, UndertakingStatusEnum,
    UndertakingEvidence, UndertakingHistory, Document, DocumentStatusEnum,
    DocumentTypeEnum, Alert, Notification, EmailOutbox, UploadedFile,
    Role, Holiday, ClockSegment, CommitteeAssignment, CommitteeObservation
)
from app.core.security import get_password_hash
from app.services.clock import get_system_time, compute_stage_due_date, normalize_dt
from app.services.workflow_engine import WorkflowEngine
from datetime import date


def seed_demo_applications():
    db: Session = SessionLocal()
    try:
        print("=== SEEDING 60 DEMO APPLICATIONS & V2 EXTENSIONS (PHASE 6) ===")

        # Clean existing demo applications and committee/clock data if re-running
        db.query(CommitteeObservation).delete()
        db.query(CommitteeAssignment).delete()
        db.query(ClockSegment).delete()
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

        default_pwd_hash = get_password_hash("Password@123")
        bureau_role = db.query(Role).filter(Role.code == UserRoleEnum.BUREAU_OFFICER).first()
        comm_role = db.query(Role).filter(Role.code == UserRoleEnum.COMMITTEE_MEMBER).first()

        bureau_user = db.query(User).filter(User.email == "bureau.officer@aicte.gov.in").first()
        if not bureau_user and bureau_role:
            bureau_user = User(
                username="bureau.officer@aicte.gov.in", email="bureau.officer@aicte.gov.in",
                full_name="Dr. Alok Verma (Bureau Officer)", password_hash=default_pwd_hash,
                role_id=bureau_role.id, is_active=True
            )
            db.add(bureau_user)

        evc_member = db.query(User).filter(User.email == "evc.member@aicte.gov.in").first()
        if not evc_member and comm_role:
            evc_member = User(
                username="evc.member@aicte.gov.in", email="evc.member@aicte.gov.in",
                full_name="Dr. Ramesh Sharma (EVC Member)", password_hash=default_pwd_hash,
                role_id=comm_role.id, is_active=True
            )
            db.add(evc_member)

        shc_member = db.query(User).filter(User.email == "shc.member@aicte.gov.in").first()
        if not shc_member and comm_role:
            shc_member = User(
                username="shc.member@aicte.gov.in", email="shc.member@aicte.gov.in",
                full_name="Prof. Sunita Rao (SHC Member)", password_hash=default_pwd_hash,
                role_id=comm_role.id, is_active=True
            )
            db.add(shc_member)
        db.flush()

        # Seed sample fixed-date national holidays
        sample_holidays = [
            (date(2026, 1, 26), "Republic Day (sample holiday list, to be replaced by the official AICTE calendar)", None, "NATIONAL"),
            (date(2026, 8, 15), "Independence Day (sample holiday list, to be replaced by the official AICTE calendar)", None, "NATIONAL"),
            (date(2026, 10, 2), "Mahatma Gandhi Jayanti (sample holiday list, to be replaced by the official AICTE calendar)", None, "NATIONAL"),
            (date(2026, 12, 25), "Christmas Day (sample holiday list, to be replaced by the official AICTE calendar)", None, "NATIONAL"),
        ]
        for h_date, h_name, h_reg, h_type in sample_holidays:
            if not db.query(Holiday).filter(Holiday.date == h_date, Holiday.region_id == h_reg).first():
                db.add(Holiday(date=h_date, name=h_name, region_id=h_reg, holiday_type=h_type))
        db.flush()

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
            ("EVC_PENDING", 8, ["ON_TIME"] * 4 + ["NEAR_DUE"] * 2 + ["OVERDUE"] * 2),
            ("EVC_SCHEDULED", 5, ["ON_TIME"] * 3 + ["NEAR_DUE"] * 1 + ["OVERDUE"] * 1),
            ("SAC_SHC_REVIEW", 5, ["ON_TIME"] * 3 + ["NEAR_DUE"] * 1 + ["OVERDUE"] * 1),
            ("APPROVAL_GRANTED", 4, ["COMPLETED"] * 4),
            ("APPROVAL_REJECTED", 1, ["COMPLETED"] * 1),
            ("CLOSED", 5, ["COMPLETED"] * 5),
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

                elif target_stage in ["APPROVAL_GRANTED", "APPROVAL_REJECTED", "CLOSED"]:
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
                    dec = "REJECT" if (target_stage == "APPROVAL_REJECTED" or (target_stage == "CLOSED" and app_idx == 60)) else "APPROVE"
                    rem = (
                        "All statutory norms verified in compliance with APH 2026. Extension of Approval granted."
                        if dec == "APPROVE"
                        else "Fatal non-compliance with APH Chapter I Clause 1.4: Title to campus land is encumbered and in dispute."
                    )
                    WorkflowEngine.record_decision(
                        db=db, application_id=app.id, actor=chairman,
                        decision=dec, remarks=rem, decision_time=current_sim_time
                    )

                    # For CLOSED stage, Competent Authority closes the case
                    if target_stage == "CLOSED":
                        current_sim_time += timedelta(days=1)
                        closure_configs = [
                            ("ALL_CONDITIONS_MET", "All regulatory conditions fulfilled and verified by regional desk."),
                            ("ALL_CONDITIONS_MET", "Extension of Approval order issued and docket archived."),
                            ("SUPERSEDED", "Superseded by merged campus consolidation dossier."),
                            ("WITHDRAWN_BY_INSTITUTION", "Institution management formally withdrew the application."),
                            ("REJECTED_FINAL", "Final statutory rejection upheld by Competent Authority Council."),
                        ]
                        c_reason, c_remarks = closure_configs[(app_idx - 56) % len(closure_configs)]
                        WorkflowEngine.close_application(
                            db=db,
                            application_id=app.id,
                            actor=chairman,
                            closure_reason=c_reason,
                            closure_remarks=c_remarks,
                            close_time=current_sim_time
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
                if target_stage not in ["APPROVAL_GRANTED", "APPROVAL_REJECTED", "CLOSED"]:
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

                    # Phase 6 Fair Pendency Clock: For RE_SCRUTINY, case is WITH_INSTITUTION and paused
                    if target_stage == "RE_SCRUTINY":
                        pause_days = 2.0 + float((app_idx - 25) % 5) # Paused for 2 to 6 days
                        app.case_holder = "WITH_INSTITUTION"
                        app.stage_entered_at = now - timedelta(days=pause_days)
                        app.stage_due_date = app.stage_entered_at + timedelta(days=sla_days)
                        if open_hist:
                            open_hist.entered_at = app.stage_entered_at
                            open_hist.due_date = app.stage_due_date

                    # Synchronize active clock segment
                    open_seg = db.query(ClockSegment).filter(
                        ClockSegment.application_id == app.id,
                        ClockSegment.ended_at == None
                    ).order_by(ClockSegment.id.desc()).first()
                    if open_seg:
                        open_seg.started_at = app.stage_entered_at
                        open_seg.holder = app.case_holder

                db.commit()
                created_count += 1
                app_idx += 1

        print(f"✓ Successfully seeded {created_count} applications (APP-10001 to APP-10060) across 5 regions!")

        # Phase 6: Seed Committee Assignments & Observations
        print("\n--- Phase 6: Seeding Committee Assignments & Advisory Observations ---")
        comm_cases = [
            ("AICTE/2026/APP-10041", "EVC", evc_member.id, [
                ("Physical barrier and compound wall verified with geotagged imagery. Instructional space meets APH Chapter II guidelines.", "RECOMMEND_APPROVAL")
            ]),
            ("AICTE/2026/APP-10042", "EVC", evc_member.id, [
                ("Computer center requires 15 additional workstations to meet APH student-terminal ratio.", "NEEDS_CLARIFICATION")
            ]),
            ("AICTE/2026/APP-10043", "EVC", evc_member.id, [
                ("Workshop layout violates safety clearance norms. Heavy machinery unanchored.", "RECOMMEND_RE_INSPECTION")
            ]),
            ("AICTE/2026/APP-10046", "SAC_SHC", shc_member.id, [
                ("Appellate hearing evaluated land title conveyance deed. Registered sale deed verified without encumbrance.", "RECOMMEND_APPROVAL")
            ]),
            ("AICTE/2026/APP-10047", "SAC_SHC", shc_member.id, [
                ("Deficiency in faculty cadre ratio persists after representation. Insufficient professors in core departments.", "RECOMMEND_REJECTION")
            ]),
        ]
        for app_num, comm_type, user_id, obs_list in comm_cases:
            c_app = db.query(Application).filter(Application.application_number == app_num).first()
            if c_app:
                assign = CommitteeAssignment(
                    application_id=c_app.id,
                    committee_type=comm_type,
                    user_id=user_id,
                    assigned_at=now - timedelta(days=4),
                    status="ACTIVE",
                    notes="Statutory committee evaluation assignment (decision support only)."
                )
                db.add(assign)
                db.flush()
                m_user = db.query(User).filter(User.id == user_id).first()
                for obs_text, rec in obs_list:
                    obs = CommitteeObservation(
                        application_id=c_app.id,
                        committee_type=comm_type,
                        user_id=user_id,
                        member_name=m_user.full_name if m_user else "Committee Member",
                        observation_text=obs_text,
                        recommendation=rec,
                        created_at=now - timedelta(days=2)
                    )
                    db.add(obs)
        db.commit()
        print("✓ Seeded committee assignments and decision-support observations.")

        # =========================================================================
        # 2. SEED SYNTHETIC EVC EXPERTS (Phase 5: 15 experts across 5 regions)
        # =========================================================================
        print("\n--- Seeding 15 Synthetic EVC Experts Pool ---")
        db.query(EvcExpert).delete()
        db.commit()

        experts_data = [
            # Region 1: North (Kanpur HQ)
            ("Dr. Arvind Saxena", "Professor & Head", "Computer Science & Engineering", 1, "Indian Institute of Technology Kanpur", "Kanpur"),
            ("Prof. Meenakshi Sundaram", "Dean of Academic Affairs", "Mechanical Engineering", 1, "Harcourt Butler Technical University", "Kanpur"),
            ("Dr. Rajeshwari Prasad", "Principal", "Civil Engineering", 1, "Motilal Nehru National Institute of Technology", "Prayagraj"),

            # Region 2: West (Mumbai HQ)
            ("Dr. Suresh Kulkarni", "Professor", "Electronics & Telecomm", 2, "College of Engineering Pune", "Pune"),
            ("Prof. Vandana Patil", "Director", "Information Technology", 2, "Veermata Jijabai Technological Institute", "Mumbai"),
            ("Dr. Hemant Joshi", "Dean Research", "Electrical Engineering", 2, "Sardar Patel College of Engineering", "Mumbai"),

            # Region 3: South (Chennai HQ)
            ("Dr. K. Ramanathan", "Senior Professor", "Mechanical Engineering", 3, "Anna University Guindy Campus", "Chennai"),
            ("Prof. Subhashini Nair", "Dean Architecture", "Architecture & Planning", 3, "National Institute of Technology Calicut", "Kozhikode"),
            ("Dr. G. Balachandran", "Principal", "Management Studies", 3, "PSG College of Technology", "Coimbatore"),

            # Region 4: East (Kolkata HQ)
            ("Dr. Debashis Sen", "Professor", "Computer Science & Engg", 4, "Jadavpur University", "Kolkata"),
            ("Prof. Anupam Mukherjee", "Director", "Metallurgical Engineering", 4, "National Institute of Technology Durgapur", "Durgapur"),
            ("Dr. Suniti Soren", "Dean Academic", "Civil Engineering", 4, "IIEST Shibpur", "Howrah"),

            # Region 5: Central (Bhopal HQ)
            ("Dr. Raghuvir Chouhan", "Professor", "Electrical Engineering", 5, "MANIT Bhopal", "Bhopal"),
            ("Prof. Archana Trivedi", "Dean Student Affairs", "Pharmacy & Life Sciences", 5, "SGSITS Indore", "Indore"),
            ("Dr. Naresh Solanki", "Principal", "Mechanical Engineering", 5, "SVNIT Surat", "Surat"),
        ]

        seeded_experts = []
        for name, desig, disc, reg_id, home_inst, city in experts_data:
            exp = EvcExpert(
                name=name,
                designation=desig,
                discipline=disc,
                region_id=reg_id,
                home_institution=home_inst,
                city=city,
                is_available=True,
            )
            db.add(exp)
            seeded_experts.append(exp)
        db.commit()
        print(f"✓ Seeded {len(seeded_experts)} synthetic EVC experts pool across 5 regions.")

        # =========================================================================
        # 3. SEED SYNTHETIC UPLOADED FILES (Phase 5 Local Storage)
        # =========================================================================
        print("\n--- Seeding Uploaded File Records ---")
        db.query(UploadedFile).delete()
        db.commit()

        sample_file_defs = [
            ("sample_fire_noc.pdf", "Fire Safety NOC Clearance Certificate.pdf", 45000, "application/pdf", "DOCUMENT", 1),
            ("sample_land_lease_deed.pdf", "Land Lease Agreement 99-Year Registered.pdf", 52000, "application/pdf", "DOCUMENT", 2),
            ("sample_undertaking_evidence.pdf", "Divyangjan Lift Ramp Completion Proof.pdf", 38000, "application/pdf", "UNDERTAKING", 1),
            ("sample_evc_report.pdf", "EVC Inspection Report Apex Campus.pdf", 61000, "application/pdf", "EVC_REPORT", 1),
        ]
        seeded_files = {}
        for fname, orig_name, fsize, mtype, etype, eid in sample_file_defs:
            f = UploadedFile(
                original_filename=orig_name,
                stored_filename=fname,
                file_path=f"backend/uploads/samples/{fname}",
                file_size_bytes=fsize,
                mime_type=mtype,
                checksum_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                entity_type=etype,
                entity_id=eid,
                uploaded_by=admin.id,
            )
            db.add(f)
            seeded_files[fname] = f
        db.commit()
        print(f"✓ Seeded {len(seeded_files)} uploaded file metadata records.")

        # =========================================================================
        # 4. SEED EVC VISITS (~12 records covering all lifecycle states)
        # =========================================================================
        print("\n--- Seeding 12 EVC Inspection Visits Across All States ---")
        db.query(EvcVisit).delete()
        db.commit()

        # Find applications in EVC stages
        evc_pending_apps = db.query(Application).filter(Application.current_stage.has(code="EVC_PENDING")).all()
        evc_sched_apps = db.query(Application).filter(Application.current_stage.has(code="EVC_SCHEDULED")).all()
        evc_other_apps = db.query(Application).filter(Application.current_stage.has(code="SAC_SHC_REVIEW")).all()

        exp_objs = db.query(EvcExpert).all()
        exp_dict = {e.id: e for e in exp_objs}

        def make_panel(e1_id, e2_id, e3_id):
            return [
                {
                    "id": exp_dict[eid].id,
                    "name": exp_dict[eid].name,
                    "designation": exp_dict[eid].designation,
                    "discipline": exp_dict[eid].discipline,
                    "home_institution": exp_dict[eid].home_institution,
                    "city": exp_dict[eid].city,
                }
                for eid in [e1_id, e2_id, e3_id] if eid in exp_dict
            ]

        evc_records = [
            # 1-2: PENDING_ASSIGNMENT (Queue table)
            (evc_pending_apps[0].id if len(evc_pending_apps) > 0 else 1, EvcStatusEnum.PENDING_ASSIGNMENT, None, "PHYSICAL", None, [], None, None, None),
            (evc_pending_apps[1].id if len(evc_pending_apps) > 1 else 2, EvcStatusEnum.PENDING_ASSIGNMENT, None, "PHYSICAL", None, [], None, None, None),

            # 3-4: ASSIGNED (Panel picked, waiting for date/time schedule)
            (evc_pending_apps[2].id if len(evc_pending_apps) > 2 else 3, EvcStatusEnum.ASSIGNED, None, "PHYSICAL", "Dr. Arvind Saxena", make_panel(1, 4, 7), None, None, None),
            (evc_pending_apps[3].id if len(evc_pending_apps) > 3 else 4, EvcStatusEnum.ASSIGNED, None, "PHYSICAL", "Prof. Vandana Patil", make_panel(5, 8, 11), None, None, None),

            # 5-7: SCHEDULED (Upcoming in next 3-7 days)
            (evc_sched_apps[0].id if len(evc_sched_apps) > 0 else 5, EvcStatusEnum.SCHEDULED, now.date() + timedelta(days=3), "PHYSICAL", "Dr. K. Ramanathan", make_panel(7, 2, 10), None, None, None),
            (evc_sched_apps[1].id if len(evc_sched_apps) > 1 else 6, EvcStatusEnum.SCHEDULED, now.date() + timedelta(days=5), "PHYSICAL", "Dr. Debashis Sen", make_panel(10, 13, 1), None, None, None),
            (evc_sched_apps[2].id if len(evc_sched_apps) > 2 else 7, EvcStatusEnum.SCHEDULED, now.date() + timedelta(days=7), "VIRTUAL", "Dr. Raghuvir Chouhan", make_panel(13, 6, 9), None, None, None),

            # 8-9: Overdue SCHEDULED (Scheduled date in past -> triggers RULE_EVC_VISIT_OVERDUE)
            (evc_sched_apps[3].id if len(evc_sched_apps) > 3 else 8, EvcStatusEnum.SCHEDULED, now.date() - timedelta(days=4), "PHYSICAL", "Dr. Suresh Kulkarni", make_panel(4, 14, 3), None, "Transit delay in regional highway", None),
            (evc_sched_apps[4].id if len(evc_sched_apps) > 4 else 9, EvcStatusEnum.SCHEDULED, now.date() - timedelta(days=6), "PHYSICAL", "Prof. Meenakshi Sundaram", make_panel(2, 12, 15), None, "Reschedule requested by institution", None),

            # 10: VISIT_DONE (Inspection completed, report being drafted)
            (evc_other_apps[0].id if len(evc_other_apps) > 0 else 10, EvcStatusEnum.VISIT_DONE, now.date() - timedelta(days=2), "PHYSICAL", "Dr. Arvind Saxena", make_panel(1, 5, 8), None, "Physical campus inspection concluded successfully.", None),

            # 11: REPORT_RECEIVED (Report uploaded, awaiting human officer stage transition)
            (evc_other_apps[1].id if len(evc_other_apps) > 1 else 11, EvcStatusEnum.REPORT_RECEIVED, now.date() - timedelta(days=10), "PHYSICAL", "Prof. Subhashini Nair", make_panel(8, 11, 14), "RECOMMENDED", "Clear compliance observed. Full intake recommended.", seeded_files["sample_evc_report.pdf"].id),

            # 12: CLOSED (Finished lifecycle)
            (evc_other_apps[2].id if len(evc_other_apps) > 2 else 12, EvcStatusEnum.CLOSED, now.date() - timedelta(days=20), "PHYSICAL", "Dr. G. Balachandran", make_panel(9, 3, 6), "RECOMMENDED", "EVC process completed and approved by Regional Committee.", seeded_files["sample_evc_report.pdf"].id),
        ]

        for app_id, st, sdate, vtype, chair, panel, outcome, remarks, rep_id in evc_records:
            evc = EvcVisit(
                application_id=app_id,
                status=st,
                coordinator_id=evc_coord.id if evc_coord else None,
                scheduled_date=sdate,
                scheduled_time="10:30 AM" if sdate else None,
                visit_type=vtype,
                committee_chair=chair,
                committee_experts=panel,
                assigned_experts=panel,
                outcome_recommendation=outcome,
                remarks=remarks,
                visit_summary=remarks if st in [EvcStatusEnum.VISIT_DONE, EvcStatusEnum.REPORT_RECEIVED, EvcStatusEnum.CLOSED] else None,
                visit_completed_at=now - timedelta(days=2) if st in [EvcStatusEnum.VISIT_DONE, EvcStatusEnum.REPORT_RECEIVED, EvcStatusEnum.CLOSED] else None,
                report_file_id=rep_id,
                report_uploaded_at=now - timedelta(days=1) if st in [EvcStatusEnum.REPORT_RECEIVED, EvcStatusEnum.CLOSED] else None,
                closed_at=now - timedelta(days=1) if st == EvcStatusEnum.CLOSED else None,
                closed_by=ro_map[1].id if st == EvcStatusEnum.CLOSED else None,
            )
            db.add(evc)
        db.commit()
        print("✓ Seeded 12 EVC inspection records with 3-member panels.")

        # =========================================================================
        # 5. SEED UNDERTAKINGS (~20 records with evidence, history, and escalation)
        # =========================================================================
        print("\n--- Seeding 20 Conditional Undertakings with Evidence & History ---")
        db.query(UndertakingHistory).delete()
        db.query(UndertakingEvidence).delete()
        db.query(Undertaking).delete()
        db.commit()

        undertaking_templates = [
            ("Barrier-Free Ramp & Divyangjan Lift Construction", "Complete construction of dedicated elevator and entrance ramps per Chapter VII accessibility standards.", 75, UndertakingStatusEnum.PENDING, 0, 1),
            ("Fire Suppression Hydrant System Installation", "Procure and commission overhead pressurized hydrant ring with NOC renewal.", 85, UndertakingStatusEnum.PENDING, 0, 1),
            ("Digital Library e-Subscription Bandwidth Augmentation", "Upgrade campus-wide high-speed internet lease line to 500 Mbps and renew IEEE access.", 60, UndertakingStatusEnum.PENDING, 0, 1),
            ("Cadre Ratio Rectification - Professor Cadre Appointment", "Recruit 2 regular Cadre Professors in Computer Science per AICTE 1:2:6 ratio.", 90, UndertakingStatusEnum.PENDING, 0, 1),
            ("Language Laboratory Software Licensing", "Install 60-seat interactive multimedia language lab licenses.", 70, UndertakingStatusEnum.PENDING, 0, 1),

            # Due soon (<= 15 days) -> fires RULE_UNDERTAKING_DUE_15D
            ("Solar Rooftop PV Array 50kW Grid Interconnection", "Grid synchronisation certificate submission to Regional Office.", 8, UndertakingStatusEnum.PENDING, 0, 1),
            ("Girls Hostel CCTV Surveillance Ring Setup", "Install 32 IP cameras covering perimeter boundary wall.", 11, UndertakingStatusEnum.PENDING, 0, 1),
            ("Internal Complaint Committee (ICC) Compliance Report", "Submit annual ICC report and workshop completion registers.", 5, UndertakingStatusEnum.PENDING, 0, 1),
            ("Anti-Ragging Committee Statutory Undertaking", "Affidavit collection from 100% newly enrolled students.", 14, UndertakingStatusEnum.PENDING, 0, 1),

            # SUBMITTED (Evidence uploaded by Institution, awaiting regional officer verification)
            ("Safety Glass Glazing in Chemistry Labs", "Replace window panes with reinforced toughened shatter-proof glass.", 4, UndertakingStatusEnum.SUBMITTED, 0, 1),
            ("Bio-Waste Disposal MoU Renewal", "Execution of biomedical waste clearance MoU with municipal vendor.", 12, UndertakingStatusEnum.SUBMITTED, 0, 1),

            # NEEDS_MORE_EVIDENCE
            ("Rainwater Harvesting Borewell Recharging Pit", "Construction of 3 recharge wells with geotagged photographic proof.", 20, UndertakingStatusEnum.NEEDS_MORE_EVIDENCE, 1, 1),

            # Overdue (past due date)
            ("CAD/CAM Simulator Lab Machinery Delivery", "Commissioning report for 5-axis CNC machining center.", -6, UndertakingStatusEnum.OVERDUE, 0, 1),
            ("Faculty Pay Scale Implementation 7th CPC", "Compliance certificate of 7th Pay Commission salary disbursement.", -12, UndertakingStatusEnum.OVERDUE, 0, 1),
            ("Backup Generator 125 kVA Silent DG Set Setup", "CPCB pollution clearance certificate for acoustic DG enclosure.", -18, UndertakingStatusEnum.OVERDUE, 0, 1),

            # ESCALATED (Rejected 2 times -> escalated to Competent Authority)
            ("Girls Common Room Dedicated Facility Expansion", "Carpet area expansion from 50 sqm to 100 sqm with attached sanitised restrooms.", -4, UndertakingStatusEnum.ESCALATED, 2, 3),

            # VERIFIED (Complied)
            ("Smart Classroom Projector & AV Equipment", "Installation of 10 interactive smart boards in lecture theatre blocks.", -30, UndertakingStatusEnum.VERIFIED, 0, 1),
            ("Internet Protocol CCTV Integration with AICTE Portal", "Live streaming RTSP link integration with central AICTE server.", -45, UndertakingStatusEnum.VERIFIED, 0, 1),
            ("Alumni Endowment Fund Corpus Deposit", "Statutory deposit of INR 25 Lakh in scheduled commercial bank FDR.", -60, UndertakingStatusEnum.VERIFIED, 0, 1),
            ("Sports Complex Indoor Badminton Court Renovation", "Rubberized wooden flooring laid in multipurpose gymnasium.", -20, UndertakingStatusEnum.VERIFIED, 0, 1),
        ]

        all_apps = db.query(Application).order_by(Application.id).all()
        for i, (title, desc, day_offset, ustatus, rej_count, tier) in enumerate(undertaking_templates):
            app = all_apps[i % len(all_apps)]
            inst_id = app.institution_id
            ut = Undertaking(
                application_id=app.id,
                institution_id=inst_id,
                condition_title=title,
                description=desc,
                due_date=now.date() + timedelta(days=day_offset),
                status=ustatus,
                rejection_count=rej_count,
                escalated_to_tier=tier,
                escalation_reason="Rejected twice by Scrutiny Desk; escalated for Apex determination." if ustatus == UndertakingStatusEnum.ESCALATED else None,
                assigned_verifier_id=scrutiny_map.get(app.region_id, scrutiny_map[1]).id if scrutiny_map.get(app.region_id) else None,
                verified_at=now - timedelta(days=10) if ustatus == UndertakingStatusEnum.VERIFIED else None,
                verification_remarks="Documentary proof verified and found compliant per norms." if ustatus == UndertakingStatusEnum.VERIFIED else ("Incomplete geo-tagged photos submitted" if ustatus == UndertakingStatusEnum.NEEDS_MORE_EVIDENCE else None),
            )
            db.add(ut)
            db.flush()

            # Add evidence if SUBMITTED, VERIFIED, or ESCALATED
            if ustatus in [UndertakingStatusEnum.SUBMITTED, UndertakingStatusEnum.VERIFIED, UndertakingStatusEnum.ESCALATED, UndertakingStatusEnum.NEEDS_MORE_EVIDENCE]:
                ev = UndertakingEvidence(
                    undertaking_id=ut.id,
                    submitted_by=inst_user_map.get(inst_id, admin).id,
                    file_name="Compliance_Execution_Proof.pdf",
                    file_url=f"/api/v1/files/{seeded_files['sample_undertaking_evidence.pdf'].id}/download",
                    file_id=seeded_files["sample_undertaking_evidence.pdf"].id,
                    comments="Geo-tagged photographic evidence and contractor completion certificate attached.",
                    submitted_at=now - timedelta(days=3),
                )
                db.add(ev)

            # Add History entry
            hist = UndertakingHistory(
                undertaking_id=ut.id,
                from_status="PENDING",
                to_status=ustatus.value,
                action_by=scrutiny_map.get(app.region_id, scrutiny_map[1]).id if ustatus == UndertakingStatusEnum.VERIFIED else inst_user_map.get(inst_id, admin).id,
                action_role="SCRUTINY_OFFICER" if ustatus == UndertakingStatusEnum.VERIFIED else "INSTITUTION_USER",
                remarks=f"Initial seed status set to {ustatus.value}",
                created_at=now - timedelta(days=2),
            )
            db.add(hist)

        db.commit()
        print("✓ Seeded 20 conditional undertakings with evidence and history.")

        # =========================================================================
        # 6. SEED STATUTORY DOCUMENTS (~25 records with multi-version chains)
        # =========================================================================
        print("\n--- Seeding 25 Statutory Documents (Versioned Leases, Fire NOCs, FDRs) ---")
        db.query(Document).delete()
        db.commit()

        doc_templates = [
            # Valid long term (> 180 days)
            (DocumentTypeEnum.LAND_LEASE_DEED, "Reg. Lease Deed Vol 429/18", "Registered 99-Year Land Lease Deed", "Sub-Registrar Office, Kanpur", -3650, 720, DocumentStatusEnum.VALID, 1),
            (DocumentTypeEnum.BUILDING_PLAN_APPROVAL, "KDA/BP/2021/881", "Sanctioned Master Plan & Structural Drawing", "Kanpur Development Authority", -1800, 1800, DocumentStatusEnum.VALID, 1),
            (DocumentTypeEnum.OCCUPANCY_CERTIFICATE, "PWD/OC/2022/410", "Final Occupancy Certificate - Main Academic Block", "Public Works Department (PWD)", -1200, 1500, DocumentStatusEnum.VALID, 1),
            (DocumentTypeEnum.AICTE_FDR_GUARANTEE, "SBI/FDR/2024/9912", "Joint FDR Deposit in Favor of AICTE (INR 35L)", "State Bank of India", -700, 400, DocumentStatusEnum.VALID, 1),
            (DocumentTypeEnum.AFFILIATING_UNIVERSITY_NOC, "AKTU/AFF/2025/11", "Annual Affiliation Continuation NOC", "Dr. A.P.J. Abdul Kalam Technical University", -300, 200, DocumentStatusEnum.VALID, 1),
            (DocumentTypeEnum.LAND_LEASE_DEED, "MU/LEASE/2019/55", "Perpetual Educational Land Lease Deed", "District Collectorate, Pune", -2500, 950, DocumentStatusEnum.VALID, 1),
            (DocumentTypeEnum.FIRE_SAFETY_NOC, "FS/BOM/2025/71", "Fire Safety Compliance Certificate", "Mumbai Fire Brigade HQ", -100, 265, DocumentStatusEnum.VALID, 1),

            # Expiring in 60-90 days -> triggers RULE_LEASE_90D
            (DocumentTypeEnum.LAND_LEASE_DEED, "REG/LEASE/1996/401", "30-Year Registered Land Lease Deed", "Sub-Registrar Sadar, Lucknow", -10800, 75, DocumentStatusEnum.EXPIRING, 1),
            (DocumentTypeEnum.LAND_LEASE_DEED, "TN/CH/1996/1209", "30-Year Land Lease Deed - South Campus", "Sub-Registrar Guindy, Chennai", -10800, 80, DocumentStatusEnum.EXPIRING, 1),
            (DocumentTypeEnum.LAND_LEASE_DEED, "WB/KOL/1996/89", "Educational Land Lease Agreement", "Registrar of Assurances, Kolkata", -10800, 70, DocumentStatusEnum.EXPIRING, 1),
            (DocumentTypeEnum.AICTE_FDR_GUARANTEE, "PNB/FDR/2021/334", "Joint FDR Guarantee Certificate", "Punjab National Bank", -1800, 85, DocumentStatusEnum.EXPIRING, 1),
            (DocumentTypeEnum.LAND_LEASE_DEED, "MP/IND/1996/711", "30-Year Registered Educational Lease", "District Registrar, Indore", -10800, 65, DocumentStatusEnum.EXPIRING, 1),

            # Expiring in 15-30 days -> triggers RULE_LEASE_30D
            (DocumentTypeEnum.LAND_LEASE_DEED, "UP/NOIDA/1996/502", "30-Year Institutional Land Lease Deed", "Noida Authority Lease Office", -10920, 22, DocumentStatusEnum.EXPIRING, 1),
            (DocumentTypeEnum.LAND_LEASE_DEED, "KA/BLR/1996/1101", "30-Year Registered Lease Agreement", "Sub-Registrar Jayanagar, Bengaluru", -10920, 18, DocumentStatusEnum.EXPIRING, 1),
            (DocumentTypeEnum.FIRE_SAFETY_NOC, "FS/KAN/2025/309", "Annual Fire Safety Clearance Certificate", "Chief Fire Officer, Kanpur", -345, 20, DocumentStatusEnum.EXPIRING, 1),
            (DocumentTypeEnum.AICTE_FDR_GUARANTEE, "BOB/FDR/2021/77", "Institutional FDR Guarantee Deposit", "Bank of Baroda", -1800, 25, DocumentStatusEnum.EXPIRING, 1),
            (DocumentTypeEnum.LAND_LEASE_DEED, "MH/PUN/1996/331", "30-Year Land Title Lease Deed", "Sub-Registrar Haveli, Pune", -10920, 15, DocumentStatusEnum.EXPIRING, 1),

            # Expired -> triggers RULE_FIRE_NOC_EXPIRED
            (DocumentTypeEnum.FIRE_SAFETY_NOC, "FS/LKO/2024/991", "Provisional Fire NOC", "Uttar Pradesh Fire Services", -400, -15, DocumentStatusEnum.EXPIRED, 1),
            (DocumentTypeEnum.FIRE_SAFETY_NOC, "FS/CHN/2024/442", "Building Fire Protection Certificate", "Tamil Nadu Fire & Rescue Services", -420, -35, DocumentStatusEnum.EXPIRED, 1),
            (DocumentTypeEnum.FIRE_SAFETY_NOC, "FS/KOL/2024/110", "Periodic Fire Safety NOC", "West Bengal Fire & Emergency Services", -380, -10, DocumentStatusEnum.EXPIRED, 1),
            (DocumentTypeEnum.FIRE_SAFETY_NOC, "FS/BPL/2024/552", "Statutory Fire Clearance", "Bhopal Municipal Corporation Fire Dept", -410, -25, DocumentStatusEnum.EXPIRED, 1),
            (DocumentTypeEnum.FIRE_SAFETY_NOC, "FS/MUM/2024/883", "Fire NOC - High Rise Academic Block", "Maharashtra Fire Service", -450, -45, DocumentStatusEnum.EXPIRED, 1),
        ]

        for i, (dtype, dnum, title, auth, start_offset, expiry_offset, dstatus, ver) in enumerate(doc_templates):
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
                version_number=ver,
                renewal_file_id=seeded_files["sample_fire_noc.pdf"].id if dtype == DocumentTypeEnum.FIRE_SAFETY_NOC else seeded_files["sample_land_lease_deed.pdf"].id,
                last_verified_at=now - timedelta(days=30),
            )
            db.add(doc)
        db.commit()

        # Seed 1 Multi-Version Document Renewal Chain (v1 SUPERSEDED -> v2 RENEWAL_SUBMITTED awaiting verification)
        apex_inst = db.query(Institution).filter(Institution.id == 1).first()
        apex_app = db.query(Application).filter(Application.institution_id == 1).first()
        apex_app_id = apex_app.id if apex_app else None

        v1_doc = Document(
            institution_id=1,
            application_id=apex_app_id,
            document_type=DocumentTypeEnum.FIRE_SAFETY_NOC,
            document_number="FS/KAN/2024/099",
            title="Annual Fire Safety Clearance Certificate",
            issuing_authority="Chief Fire Officer, Kanpur",
            issue_date=now.date() - timedelta(days=380),
            expiry_date=now.date() - timedelta(days=15), # Expired 15 days ago
            status=DocumentStatusEnum.SUPERSEDED,
            version_number=1,
            renewal_file_id=seeded_files["sample_fire_noc.pdf"].id,
            verification_remarks="Superseded by renewal dossier v2.",
            last_verified_at=now - timedelta(days=380),
        )
        db.add(v1_doc)
        db.flush()

        v2_doc = Document(
            institution_id=1,
            application_id=apex_app_id,
            document_type=DocumentTypeEnum.FIRE_SAFETY_NOC,
            document_number="FS/KAN/2025/100",
            title="Annual Fire Safety Clearance Certificate (v2)",
            issuing_authority="Chief Fire Officer, Kanpur",
            issue_date=now.date() - timedelta(days=2),
            expiry_date=now.date() + timedelta(days=363),
            status=DocumentStatusEnum.RENEWAL_SUBMITTED,
            version_number=2,
            previous_version_id=v1_doc.id,
            renewal_file_id=seeded_files["sample_fire_noc.pdf"].id,
            renewal_notes="Renewed fire safety audit conducted and passed by CFO Kanpur. Requesting officer verification.",
            created_at=now - timedelta(days=2),
        )
        db.add(v2_doc)
        db.commit()

        print("✓ Seeded 25 statutory documents with versioning chains and active renewal.")

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
