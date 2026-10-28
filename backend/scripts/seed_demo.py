import os
import sys
from datetime import datetime, timedelta

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models import (
    Application, Institution, ApplicationCategory, StagePath, Stage,
    User, UserRoleEnum, ApplicationStatusEnum, StageStatusEnum, StageHistory
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
        print("=== DEMO DATA SEED COMPLETED SUCCESSFULLY ===")

    except Exception as e:
        db.rollback()
        print(f"Error seeding demo applications: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_applications()
