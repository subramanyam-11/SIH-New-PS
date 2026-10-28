import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.core.security import get_password_hash
from app.models import (
    Region, Role, User, UserRoleEnum, Institution,
    ApplicationCategory, StagePath, Stage,
    AlertRule, EscalationRule, AlertTypeEnum, AlertSeverityEnum,
    SystemConfig, CommunicationTemplate
)


def seed_foundation():
    db: Session = SessionLocal()
    try:
        print("--- SEEDING FOUNDATION DATA ---")

        # 1. ROLES (6 standard AICTE roles)
        roles_data = [
            (UserRoleEnum.ADMIN, "System Administrator", "Full system configuration and audit access"),
            (UserRoleEnum.SCRUTINY_OFFICER, "Scrutiny Officer", "Reviews application dossiers, checks compliance and marks deficiencies"),
            (UserRoleEnum.EVC_COORDINATOR, "EVC Coordinator", "Schedules inspection panels and tracks report submissions"),
            (UserRoleEnum.REGIONAL_HEAD, "Regional Head / Director", "Oversees regional pendency, endorses transitions, handles escalations"),
            (UserRoleEnum.COMPETENT_AUTHORITY, "Competent Authority / Council", "Senior council management, SAC/SHC appeals, and final approvals"),
            (UserRoleEnum.INSTITUTION_USER, "Institution User", "Institution Principal / Registrar submitting compliance evidence")
        ]

        roles_map = {}
        for code, title, desc in roles_data:
            role = db.query(Role).filter(Role.code == code).first()
            if not role:
                role = Role(code=code, title=title, description=desc)
                db.add(role)
                db.flush()
            roles_map[code] = role
        print(f"✓ Seeded {len(roles_map)} roles.")

        # 2. REGIONS (5 Regions)
        regions_data = [
            ("RO_NORTH", "Northern Regional Office (Kanpur)", "Kanpur", ["Uttar Pradesh", "Uttarakhand"]),
            ("RO_WEST", "Western Regional Office (Mumbai)", "Mumbai", ["Maharashtra", "Goa"]),
            ("RO_SOUTH", "Southern Regional Office (Chennai)", "Chennai", ["Tamil Nadu", "Puducherry"]),
            ("RO_EAST", "Eastern Regional Office (Kolkata)", "Kolkata", ["West Bengal", "Odisha", "Bihar", "Jharkhand"]),
            ("RO_CENTRAL", "Central Regional Office (Bhopal)", "Bhopal", ["Madhya Pradesh", "Chhattisgarh", "Gujarat"])
        ]

        regions_map = {}
        for code, name, hq, states in regions_data:
            reg = db.query(Region).filter(Region.code == code).first()
            if not reg:
                reg = Region(code=code, name=name, headquarters=hq, states_covered=states)
                db.add(reg)
                db.flush()
            regions_map[code] = reg
        print(f"✓ Seeded {len(regions_map)} regions.")

        # 3. INSTITUTIONS (15 Representative Institutions)
        institutions_data = [
            ("1-102938471", "Apex Institute of Technology, Kanpur", "Engineering & Technology", "Self-Financing", regions_map["RO_NORTH"].id, "NH-2, Kalyanpur", "Kanpur", "Uttar Pradesh", "208017", "principal@apexkanpur.edu", "+91-512-258901"),
            ("1-102938472", "Doon Valley College of Engineering, Dehradun", "Engineering & Technology", "Self-Financing", regions_map["RO_NORTH"].id, "Rajpur Road", "Dehradun", "Uttarakhand", "248001", "info@doonvalley.edu", "+91-135-274902"),
            ("1-102938473", "Kashi Institute of Management, Varanasi", "Management", "Self-Financing", regions_map["RO_NORTH"].id, "Mirzapur Road", "Varanasi", "Uttar Pradesh", "221005", "admin@kashimgmt.edu", "+91-542-269103"),
            ("1-204958381", "Sahyadri College of Engineering & Tech, Pune", "Engineering & Technology", "Govt-Aided", regions_map["RO_WEST"].id, "Karve Road", "Pune", "Maharashtra", "411038", "director@sahyadri.edu", "+91-20-254390"),
            ("1-204958382", "Maratha Mandal Polytechnic, Kolhapur", "Polytechnic", "Self-Financing", regions_map["RO_WEST"].id, "Station Road", "Kolhapur", "Maharashtra", "416001", "principal@mmpoly.edu", "+91-231-265104"),
            ("1-204958383", "Vidarbha Business School, Nagpur", "Management", "Self-Financing", regions_map["RO_WEST"].id, "Wardha Road", "Nagpur", "Maharashtra", "440015", "dean@vidarbhabs.edu", "+91-712-284905"),
            ("1-305849201", "Kaveri Institute of Technology, Coimbatore", "Engineering & Technology", "Self-Financing", regions_map["RO_SOUTH"].id, "Avinashi Road", "Coimbatore", "Tamil Nadu", "641014", "principal@kaveri.edu", "+91-422-290106"),
            ("1-305849202", "Thanjavur Polytechnic College, Thanjavur", "Polytechnic", "Govt", regions_map["RO_SOUTH"].id, "Trichy Road", "Thanjavur", "Tamil Nadu", "613007", "principal@thanjavurpoly.gov.in", "+91-436-248907"),
            ("1-305849203", "Madras Academy of Computer Applications, Chennai", "MCA", "Self-Financing", regions_map["RO_SOUTH"].id, "OMR Expressway", "Chennai", "Tamil Nadu", "600096", "info@maca.edu", "+91-44-245010"),
            ("1-409582711", "Kalinga Institute of Engineering, Bhubaneswar", "Engineering & Technology", "Self-Financing", regions_map["RO_EAST"].id, "Patia", "Bhubaneswar", "Odisha", "751024", "info@kalingaeng.edu", "+91-674-272511"),
            ("1-409582712", "Hooghly Institute of Technology, Kolkata", "Polytechnic", "Govt-Aided", regions_map["RO_EAST"].id, "Grand Trunk Road", "Kolkata", "West Bengal", "712103", "principal@hooghlytech.edu", "+91-33-268012"),
            ("1-409582713", "Patna School of Pharmacy, Patna", "Pharmacy", "Self-Financing", regions_map["RO_EAST"].id, "Bailey Road", "Patna", "Bihar", "800001", "director@patnapharmacy.edu", "+91-612-223413"),
            ("1-508392101", "Malwa Institute of Technology, Indore", "Engineering & Technology", "Self-Financing", regions_map["RO_CENTRAL"].id, "Bypass Road", "Indore", "Madhya Pradesh", "452016", "admin@malwatech.edu", "+91-731-280514"),
            ("1-508392102", "Chhattisgarh College of Applied Sciences, Raipur", "Applied Arts", "Self-Financing", regions_map["RO_CENTRAL"].id, "VIP Road", "Raipur", "Chhattisgarh", "492006", "principal@ccasraipur.edu", "+91-771-297115"),
            ("1-508392103", "Narmada Polytechnic Institute, Jabalpur", "Polytechnic", "Govt", regions_map["RO_CENTRAL"].id, "Civil Lines", "Jabalpur", "Madhya Pradesh", "482001", "principal@narmadapoly.gov.in", "+91-761-262116")
        ]

        institutions_map = {}
        for aicte_id, name, itype, cat, reg_id, addr, city, state, pin, email, phone in institutions_data:
            inst = db.query(Institution).filter(Institution.aicte_id == aicte_id).first()
            if not inst:
                inst = Institution(
                    aicte_id=aicte_id, name=name, institution_type=itype,
                    category=cat, region_id=reg_id, address=addr,
                    city=city, state=state, pincode=pin,
                    primary_email=email, primary_phone=phone
                )
                db.add(inst)
                db.flush()
            institutions_map[aicte_id] = inst
        print(f"✓ Seeded {len(institutions_map)} institutions.")

        # 4. USERS (Demo Personas)
        default_pwd_hash = get_password_hash("Password@123")
        users_data = [
            ("admin@aicte.gov.in", "admin@aicte.gov.in", "Dr. Rajesh Verma (System Admin)", UserRoleEnum.ADMIN, None, None),
            ("ro.north@aicte.gov.in", "ro.north@aicte.gov.in", "Er. Sunil Trivedi (Regional Head North)", UserRoleEnum.REGIONAL_HEAD, regions_map["RO_NORTH"].id, None),
            ("ro.west@aicte.gov.in", "ro.west@aicte.gov.in", "Dr. Priya Kulkarni (Regional Head West)", UserRoleEnum.REGIONAL_HEAD, regions_map["RO_WEST"].id, None),
            ("ro.south@aicte.gov.in", "ro.south@aicte.gov.in", "Dr. K. Swaminathan (Regional Head South)", UserRoleEnum.REGIONAL_HEAD, regions_map["RO_SOUTH"].id, None),
            ("ro.east@aicte.gov.in", "ro.east@aicte.gov.in", "Prof. Anirban Mukherjee (Regional Head East)", UserRoleEnum.REGIONAL_HEAD, regions_map["RO_EAST"].id, None),
            ("ro.central@aicte.gov.in", "ro.central@aicte.gov.in", "Dr. Archana Verma (Regional Head Central)", UserRoleEnum.REGIONAL_HEAD, regions_map["RO_CENTRAL"].id, None),
            ("scrutiny1@aicte.gov.in", "scrutiny1@aicte.gov.in", "Amit Sharma (Scrutiny Desk North)", UserRoleEnum.SCRUTINY_OFFICER, regions_map["RO_NORTH"].id, None),
            ("scrutiny2@aicte.gov.in", "scrutiny2@aicte.gov.in", "Neha Joshi (Scrutiny Desk West)", UserRoleEnum.SCRUTINY_OFFICER, regions_map["RO_WEST"].id, None),
            ("scrutiny3@aicte.gov.in", "scrutiny3@aicte.gov.in", "R. Venkatesh (Scrutiny Desk South)", UserRoleEnum.SCRUTINY_OFFICER, regions_map["RO_SOUTH"].id, None),
            ("scrutiny4@aicte.gov.in", "scrutiny4@aicte.gov.in", "Subhashish Das (Scrutiny Desk East)", UserRoleEnum.SCRUTINY_OFFICER, regions_map["RO_EAST"].id, None),
            ("scrutiny5@aicte.gov.in", "scrutiny5@aicte.gov.in", "Manish Tiwari (Scrutiny Desk Central)", UserRoleEnum.SCRUTINY_OFFICER, regions_map["RO_CENTRAL"].id, None),
            ("evc.coord@aicte.gov.in", "evc.coord@aicte.gov.in", "Prof. K. Ramanathan (National EVC Coordinator)", UserRoleEnum.EVC_COORDINATOR, None, None),
            ("chairman@aicte.gov.in", "chairman@aicte.gov.in", "Prof. T. G. Sitharam (Competent Authority)", UserRoleEnum.COMPETENT_AUTHORITY, None, None),
            ("principal@apexkanpur.edu", "principal@apexkanpur.edu", "Dr. V. K. Saxena (Principal, Apex Kanpur)", UserRoleEnum.INSTITUTION_USER, regions_map["RO_NORTH"].id, institutions_map["1-102938471"].id),
            ("director@sahyadri.edu", "director@sahyadri.edu", "Dr. S. R. Patil (Director, Sahyadri Pune)", UserRoleEnum.INSTITUTION_USER, regions_map["RO_WEST"].id, institutions_map["1-204958381"].id),
            ("principal@kaveri.edu", "principal@kaveri.edu", "Dr. S. Ramachandran (Principal, Kaveri Coimbatore)", UserRoleEnum.INSTITUTION_USER, regions_map["RO_SOUTH"].id, institutions_map["1-305849201"].id),
            ("director@kalinga.edu", "director@kalinga.edu", "Dr. B. K. Mohanty (Director, Kalinga Bhubaneswar)", UserRoleEnum.INSTITUTION_USER, regions_map["RO_EAST"].id, institutions_map["1-409582711"].id),
            ("principal@malwa.edu", "principal@malwa.edu", "Dr. N. K. Chouhan (Principal, Malwa Indore)", UserRoleEnum.INSTITUTION_USER, regions_map["RO_CENTRAL"].id, institutions_map["1-508392101"].id)
        ]

        users_count = 0
        for uname, email, fname, role_code, reg_id, inst_id in users_data:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    username=uname, email=email, password_hash=default_pwd_hash,
                    full_name=fname, role_id=roles_map[role_code].id,
                    region_id=reg_id, institution_id=inst_id, is_active=True
                )
                db.add(user)
                users_count += 1
            else:
                user.region_id = reg_id
                user.role_id = roles_map[role_code].id
                user.institution_id = inst_id
        db.flush()
        print(f"✓ Seeded/Updated demo users (total {len(users_data)} personas across all 5 regions).")

        # 5. APPLICATION CATEGORIES
        app_cats_data = [
            ("NEW_INSTITUTE", "Setting up New Technical Institution", True, False, "Comprehensive initial scrutiny, land inspection and EVC"),
            ("EOA", "Extension of Approval (EoA) - Routine", False, False, "Standard annual continuation of approval"),
            ("INCREASE_INTAKE", "Increase in Intake / Additional Course", True, False, "Requires verification of physical infrastructure capacity"),
            ("CHANGE_OF_SITE", "Change of Site / Location", True, True, "Requires thorough scrutiny of new land title deed and physical EVC"),
            ("CLOSURE", "Closure of Institution / Course", False, True, "Requires SAC/SHC review regarding student transfer and staff arrangements")
        ]

        for code, title, req_evc, req_sac, desc in app_cats_data:
            if not db.query(ApplicationCategory).filter(ApplicationCategory.code == code).first():
                db.add(ApplicationCategory(code=code, title=title, requires_evc=req_evc, requires_sac_shc=req_sac, description=desc))
        db.flush()
        print("✓ Seeded application categories.")

        # 6. STAGES (Configurable Default SLAs)
        stages_data = [
            ("SUBMITTED", "Submitted & Docketed", 2, UserRoleEnum.SCRUTINY_OFFICER, "Application received online from institution"),
            ("SCRUTINY", "Scrutiny & Document Verification", 7, UserRoleEnum.SCRUTINY_OFFICER, "Desk scrutiny of uploaded statutory documents"),
            ("RE_SCRUTINY", "Re-Scrutiny (Deficiency Clarification)", 7, UserRoleEnum.INSTITUTION_USER, "Clock paused for officer; institution responds to deficiencies"),
            ("EVC_PENDING", "EVC Pending Scheduling", 5, UserRoleEnum.EVC_COORDINATOR, "Awaiting committee panel and inspection date assignment"),
            ("EVC_SCHEDULED", "EVC Inspection Scheduled", 10, UserRoleEnum.EVC_COORDINATOR, "Panel assigned; awaiting site inspection and report submission"),
            ("EVC_COMPLETED", "EVC Inspection Completed", 3, UserRoleEnum.REGIONAL_HEAD, "Report uploaded; awaiting regional head review"),
            ("SAC_SHC_REVIEW", "SAC / SHC Appellate Hearing", 14, UserRoleEnum.COMPETENT_AUTHORITY, "Standing Hearing or Appellate Committee review"),
            ("APPROVAL_GRANTED", "Approval Granted (Order Issued)", 5, UserRoleEnum.COMPETENT_AUTHORITY, "Formal EoA / Letter of Approval issued"),
            ("APPROVAL_REJECTED", "Application Rejected", 0, UserRoleEnum.COMPETENT_AUTHORITY, "Statutory rejection letter with specific APH grounds")
        ]

        for code, name, sla, role, desc in stages_data:
            if not db.query(Stage).filter(Stage.code == code).first():
                db.add(Stage(code=code, name=name, default_sla_days=sla, responsible_role=role, description=desc))
        db.flush()
        print("✓ Seeded workflow stages.")

        # 7. STAGE PATHS (5 APH Paths)
        stage_paths_data = [
            ("PATH_1_SCRUTINY_ONLY", "Path 1: Scrutiny Only (Routine EoA)", "Direct path for standard renewals without intake alterations",
             ["SUBMITTED", "SCRUTINY", "APPROVAL_GRANTED"]),
            ("PATH_2_SCRUTINY_EVC", "Path 2: Scrutiny + EVC (New Inst / Expansion)", "Standard pathway requiring physical infrastructure inspection",
             ["SUBMITTED", "SCRUTINY", "EVC_PENDING", "EVC_SCHEDULED", "EVC_COMPLETED", "APPROVAL_GRANTED"]),
            ("PATH_3_EVC_SAC_SHC", "Path 3: Hearing Appeal + Re-EVC", "Appellate cycle following hearing committee orders",
             ["SUBMITTED", "SAC_SHC_REVIEW", "EVC_PENDING", "EVC_SCHEDULED", "EVC_COMPLETED", "APPROVAL_GRANTED"]),
            ("PATH_4_EVC_ONLY", "Path 4: Surprise / Physical Inspection Only", "Physical infrastructure audit or verification",
             ["SUBMITTED", "EVC_PENDING", "EVC_SCHEDULED", "EVC_COMPLETED", "APPROVAL_GRANTED"]),
            ("PATH_5_FULL_CYCLE", "Path 5: Full Cycle (Comprehensive Review)", "High-scrutiny pathway with scrutiny, EVC, and SAC/SHC hearing",
             ["SUBMITTED", "SCRUTINY", "RE_SCRUTINY", "EVC_PENDING", "EVC_SCHEDULED", "EVC_COMPLETED", "SAC_SHC_REVIEW", "APPROVAL_GRANTED"])
        ]

        for code, name, desc, seq in stage_paths_data:
            if not db.query(StagePath).filter(StagePath.code == code).first():
                db.add(StagePath(code=code, name=name, description=desc, stage_sequence=seq, is_active=True))
        db.flush()
        print("✓ Seeded stage paths.")

        # 8. ALERT RULES (Explainable Rules from docs/05)
        alert_rules_data = [
            ("RULE_SCRUTINY_NEAR_BREACH", "Scrutiny Near-Breach Alert", AlertTypeEnum.NEAR_BREACH, "APPLICATION",
             {"field": "days_remaining", "operator": "<=", "value": 2}, AlertSeverityEnum.MEDIUM,
             "APH 2026 Chapter II Clause 2.3", "Application {app_num} is within 48h of Scrutiny SLA breach."),
            ("RULE_SCRUTINY_OVERDUE", "Scrutiny SLA Overdue Alert", AlertTypeEnum.OVERDUE, "APPLICATION",
             {"field": "days_overdue", "operator": ">=", "value": 0}, AlertSeverityEnum.HIGH,
             "APH 2026 Chapter II Clause 2.3", "Application {app_num} has exceeded Scrutiny SLA deadline."),
            ("RULE_EVC_UNSCHEDULED", "EVC Unscheduled Warning", AlertTypeEnum.EVC_UNSCHEDULED, "APPLICATION",
             {"field": "days_in_stage", "operator": ">=", "value": 3}, AlertSeverityEnum.HIGH,
             "APH 2026 Chapter II Clause 2.6", "Application {app_num} pending in EVC queue for >3 days without schedule."),
            ("RULE_LEASE_90D", "Land Lease 90-Day Expiry Warning", AlertTypeEnum.DOCUMENT_EXPIRING, "DOCUMENT",
             {"field": "days_until_expiry", "operator": "<=", "value": 90}, AlertSeverityEnum.MEDIUM,
             "APH 2026 Chapter I Clause 1.4(e)", "Land lease for {institution} expires in <= 90 days."),
            ("RULE_LEASE_30D", "Land Lease 30-Day Critical Warning", AlertTypeEnum.DOCUMENT_EXPIRING, "DOCUMENT",
             {"field": "days_until_expiry", "operator": "<=", "value": 30}, AlertSeverityEnum.HIGH,
             "APH 2026 Chapter I Clause 1.4(e)", "Land lease for {institution} expires in <= 30 days. Action required."),
            ("RULE_FIRE_NOC_EXPIRED", "Fire NOC Expired Statutory Violation", AlertTypeEnum.DOCUMENT_EXPIRED, "DOCUMENT",
             {"field": "is_expired", "operator": "==", "value": True}, AlertSeverityEnum.CRITICAL,
             "APH 2026 Chapter I Clause 1.4(g)", "Fire Safety NOC has expired for {institution}. Approval must be held."),
            ("RULE_UNDERTAKING_DUE_15D", "Undertaking Due in 15 Days", AlertTypeEnum.UNDERTAKING_DUE, "UNDERTAKING",
             {"field": "days_until_due", "operator": "<=", "value": 15}, AlertSeverityEnum.MEDIUM,
             "APH 2026 Chapter III Clause 3.2", "Conditional undertaking condition due in 15 days for {institution}."),
            ("RULE_MULTIPLE_REVERTS", "Repeated Reverts Escalation", AlertTypeEnum.MULTIPLE_REVERTS, "APPLICATION",
             {"field": "revert_count", "operator": ">=", "value": 2}, AlertSeverityEnum.HIGH,
             "APH 2026 Chapter II Clause 2.5", "Application {app_num} has been reverted 2 or more times. Requires supervision.")
        ]

        for code, name, atype, etype, cond, sev, aph, tmpl in alert_rules_data:
            rule = db.query(AlertRule).filter(AlertRule.code == code).first()
            if not rule:
                rule = AlertRule(
                    code=code, name=name, alert_type=atype, entity_type=etype,
                    condition_logic=cond, severity=sev, aph_reference_clause=aph,
                    template_message=tmpl, is_active=True
                )
                db.add(rule)
                db.flush()

                # Add escalation rules for overdue rules
                if code == "RULE_SCRUTINY_OVERDUE":
                    db.add(EscalationRule(alert_rule_id=rule.id, tier_level=1, target_role=UserRoleEnum.SCRUTINY_OFFICER, trigger_delay_days=0, action_required="Desk notice"))
                    db.add(EscalationRule(alert_rule_id=rule.id, tier_level=2, target_role=UserRoleEnum.REGIONAL_HEAD, trigger_delay_days=2, action_required="Regional intervention"))
                    db.add(EscalationRule(alert_rule_id=rule.id, tier_level=3, target_role=UserRoleEnum.COMPETENT_AUTHORITY, trigger_delay_days=5, action_required="Council docket"))
        db.flush()
        print("✓ Seeded alert rules and 3-tier escalation hierarchies.")

        # 9. SYSTEM CONFIG (APH Rules JSON)
        configs = [
            ("aph_version", {"academic_year": "2026-2027", "handbook_code": "APH_2026_V1"}, "Active APH version"),
            ("sla_rules", {
                "SCRUTINY": 7,
                "RE_SCRUTINY_INSTITUTION_LIMIT": 7,
                "EVC_PENDING_TO_SCHEDULE": 5,
                "EVC_SCHEDULED_TO_VISIT": 10,
                "EVC_VISIT_TO_REPORT": 3,
                "SAC_SHC_REVIEW": 14,
                "FINAL_APPROVAL_DECISION": 5
            }, "Standard stage SLA limits in calendar days"),
            ("alert_thresholds", {
                "near_breach_percent": 80,
                "near_breach_min_days": 2,
                "evc_unscheduled_days": 3,
                "undertaking_warning_days": [60, 30, 15, 7],
                "document_expiry_warning_days": [90, 60, 30, 15, 7]
            }, "Watchdog thresholds for triggering automated alerts"),
            ("escalation_ladder", {
                "tier_1_officer": 0,
                "tier_2_regional_head_days": 2,
                "tier_3_competent_authority_days": 5
            }, "Days past due date for escalating alerts"),
            ("max_revert_cycles", {
                "limit": 2,
                "action_on_exceeded": "ESCALATION_REQUIRED",
                "description": "Max allowable clarification cycles before mandatory escalation to Regional Head"
            }, "Revert cap rule configuration"),
            ("deficiency_tags", [
                {"code": "DEF_LAND_TITLE", "label": "Land Title / Ownership Defect", "description": "Clear and undisputed land title deed or registry proof not produced."},
                {"code": "DEF_FIRE_NOC", "label": "Fire Safety NOC Missing or Expired", "description": "Valid Fire and Rescue Services NOC from competent state authority missing."},
                {"code": "DEF_FACULTY_CADRE", "label": "Faculty Cadre Ratio Deficiency", "description": "Mandatory Professor : Associate Professor : Assistant Professor ratio not met."},
                {"code": "DEF_FDR_VALIDITY", "label": "AICTE Joint FDR / Security Deposit Deficit", "description": "Statutory security deposit joint FDR not renewed or insufficient quantum."},
                {"code": "DEF_INFRASTRUCTURE", "label": "Instructional / Built-up Area Deficit", "description": "Built-up area falls below prescribed square meters per approved student intake."},
                {"code": "DEF_AFFIDAVIT", "label": "Statutory Affidavit Defect", "description": "Duly notarized affidavit on non-judicial stamp paper in prescribed format missing."},
                {"code": "DEF_ACCREDITATION", "label": "NBA / NAAC Accreditation Proof Deficient", "description": "Valid NBA/NAAC tier certificate required for intake expansion not submitted."},
                {"code": "DEF_LEASE_VALIDITY", "label": "Land Lease Duration Insufficient", "description": "Lease period is less than the mandatory minimum 30 years from date of application."},
                {"code": "DEF_OTHER", "label": "Other Regulatory Deficiency (Remark Required)", "description": "Specific regulatory deficiency described in written remarks.", "requires_remark": True}
            ], "Configured taxonomy of statutory deficiency tags")
        ]

        for k, v, d in configs:
            cfg = db.query(SystemConfig).filter(SystemConfig.config_key == k).first()
            if not cfg:
                db.add(SystemConfig(config_key=k, config_value=v, description=d))
            else:
                cfg.config_value = v
                cfg.description = d
        db.flush()
        print("✓ Seeded system configuration tables (including deficiency tags & revert cap).")

        # 10. COMMUNICATION TEMPLATES
        comm_templates_data = [
            ("APP_SUBMITTED",
             "[AICTE] Application {application_number} Received & Docketed",
             "Dear Head of Institution,\n\nYour application {application_number} for {academic_year} has been received and docketed under pathway '{path_name}'.\n\nCurrent Stage: {current_stage}\nTarget SLA: {sla_days} calendar days.\n\nYou may track procedural milestones in real-time on the AICTE Portal.\n\nAll India Council for Technical Education",
             ["application_number", "academic_year", "path_name", "current_stage", "sla_days"]),
            ("DEFICIENCY_NOTICE",
             "[AICTE URGENT] Deficiency Notice: Application {application_number}",
             "Dear Head of Institution,\n\nUpon statutory scrutiny of application {application_number}, the following deficiencies have been recorded under APH 2026 guidelines:\n\nDeficiency Tags:\n{deficiency_tags}\n\nOfficer Remarks:\n{remarks}\n\nYou are requested to submit point-by-point clarifications and documentary evidence on the portal within {clarification_limit_days} days. The scrutiny SLA clock has been paused pending your submission.\n\nRegional Directorate, AICTE",
             ["application_number", "deficiency_tags", "remarks", "clarification_limit_days"]),
            ("STAGE_ADVANCED",
             "[AICTE] Application {application_number} Procedural Update: {to_stage}",
             "Dear Applicant,\n\nApplication {application_number} has successfully concluded {from_stage} and has transitioned to '{to_stage}'.\n\nNext Step SLA: {sla_days} days.\nAction by: {responsible_role}\n\nAll India Council for Technical Education",
             ["application_number", "from_stage", "to_stage", "sla_days", "responsible_role"]),
            ("EVC_INTIMATION",
             "[AICTE NOTICE] Expert Visit Committee (EVC) Inspection Required: {application_number}",
             "Dear Head of Institution,\n\nApplication {application_number} has been recommended for physical infrastructure verification by an Expert Visit Committee (EVC).\n\nThe inspection panel will be scheduled shortly by the Regional EVC Coordinator. Kindly ensure all physical facilities, laboratory setups, and original land documents are ready for committee inspection.\n\nRegional Office, AICTE",
             ["application_number", "institution_name"]),
            ("APPROVAL_ORDER",
             "[AICTE ORDER] Statutory Decision Issued: Application {application_number}",
             "Dear Head of Institution,\n\nThe Competent Authority has rendered a statutory decision regarding application {application_number} ({category}):\n\nDecision: {decision_status}\nOrder Reference: {approval_letter_ref}\nIssuance Date: {issued_at}\n\nA formal Letter of Approval / Extension of Approval has been generated and is accessible on the portal.\n\nCouncil Secretariat,\nAll India Council for Technical Education",
             ["application_number", "category", "decision_status", "approval_letter_ref", "issued_at"])
        ]

        for code, subj, body, vars_list in comm_templates_data:
            tmpl = db.query(CommunicationTemplate).filter(CommunicationTemplate.code == code).first()
            if not tmpl:
                db.add(CommunicationTemplate(code=code, subject=subj, body_template=body, variables=vars_list))
            else:
                tmpl.subject = subj
                tmpl.body_template = body
                tmpl.variables = vars_list
        db.flush()
        print("✓ Seeded communication templates.")

        db.commit()
        print("=== FOUNDATION SEED COMPLETED SUCCESSFULLY ===")

    except Exception as e:
        db.rollback()
        print(f"Error seeding foundation data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_foundation()
