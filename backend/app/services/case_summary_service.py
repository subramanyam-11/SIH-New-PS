"""
AI Case Summary Service for SIH26262 (Phase 7 Innovation Layer).
Produces structured, explainable case summaries with:
- Case snapshot & executive overview
- Timeline highlights
- Pending items & compliance flags
- Upcoming statutory deadlines
- Current delay risk score with top factors
- Suggested next steps for authorized officers

Decision support only: Automation assists officers; statutory scrutiny,
inspections, and final decisions stay with authorized humans.
Never sends uploaded file contents or personal data to external providers.
"""
import hashlib
import json
import logging
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models import (
    Application, CaseSummary, StageHistory, Document, DocumentStatusEnum,
    Undertaking, UndertakingStatusEnum, EvcVisit, EvcStatusEnum, Alert, AlertStatusEnum
)
from app.core.config import settings
from app.services.clock import ClockService, normalize_dt
from app.services.risk_score_service import RiskScoreService

logger = logging.getLogger(__name__)


class CaseSummaryService:
    """
    Structured e-Case Summary engine with caching and optional LLM smoothing.
    Always builds deterministic baseline first.
    """

    @staticmethod
    def extract_metadata(db: Session, application: Application) -> Dict[str, Any]:
        """
        Extract sanitized metadata for summary generation.
        NO personal data, NO file contents.
        Only stages, dates, counts, deficiency tags, rule codes, and risk metrics.
        """
        now = normalize_dt(ClockService.get_now())

        # Stage history
        history_records = db.query(StageHistory).filter(
            StageHistory.application_id == application.id
        ).order_by(StageHistory.entered_at.asc()).all()

        timeline = []
        all_deficiency_tags = []
        for h in history_records:
            timeline.append({
                "stage": h.to_stage.name if h.to_stage else "Stage",
                "action": h.action_taken,
                "entered_at": h.entered_at.isoformat() if h.entered_at else None,
                "completed_at": h.completed_at.isoformat() if h.completed_at else None,
                "duration_hours": h.duration_hours,
            })
            if h.deficiency_tags:
                all_deficiency_tags.extend(h.deficiency_tags)

        # Active documents & pending renewals
        docs = db.query(Document).filter(
            Document.institution_id == application.institution_id,
            Document.status != DocumentStatusEnum.SUPERSEDED,
        ).all()
        expired_docs = [d.title for d in docs if d.expiry_date <= now.date()]
        expiring_docs = [d.title for d in docs if 0 < (d.expiry_date - now.date()).days <= 30]

        # Active undertakings
        undertakings = db.query(Undertaking).filter(
            Undertaking.institution_id == application.institution_id,
            Undertaking.status.notin_([UndertakingStatusEnum.COMPLIED, UndertakingStatusEnum.VERIFIED]),
        ).all()
        pending_undertakings = [u.condition_title for u in undertakings]

        # EVC Visit status
        evc_visits = db.query(EvcVisit).filter(
            EvcVisit.application_id == application.id
        ).all()
        evc_info = []
        for v in evc_visits:
            evc_info.append({
                "status": v.status.value,
                "scheduled_date": v.scheduled_date.isoformat() if v.scheduled_date else None,
                "has_report": bool(v.report_file_id),
            })

        # Active alerts
        alerts = db.query(Alert).filter(
            Alert.application_id == application.id,
            Alert.status.in_([AlertStatusEnum.ACTIVE, AlertStatusEnum.ESCALATED]),
        ).all()
        alert_codes = [a.rule.code for a in alerts if a.rule]

        # Risk score calculation
        risk_result = RiskScoreService.compute_score(db, application)

        return {
            "app_number": application.application_number,
            "category": application.category.title if application.category else "Technical Approval",
            "stage": application.current_stage.name if application.current_stage else "SCRUTINY",
            "stage_code": application.current_stage.code if application.current_stage else "SCRUTINY",
            "case_holder": application.case_holder,
            "revert_count": application.revert_count or 0,
            "deficiency_tags": list(set(all_deficiency_tags)),
            "timeline": timeline,
            "expired_docs": expired_docs,
            "expiring_docs": expiring_docs,
            "pending_undertakings": pending_undertakings,
            "evc_visits": evc_info,
            "active_alert_codes": alert_codes,
            "risk_score": risk_result.get("score", 0.0),
            "risk_band": risk_result.get("band", "LOW"),
            "risk_factors": risk_result.get("factors", []),
            "sla_days": application.current_stage.default_sla_days if application.current_stage else 7,
        }

    @staticmethod
    def compute_hash(metadata: Dict[str, Any]) -> str:
        """Deterministic SHA-256 hash of the input metadata."""
        canonical_json = json.dumps(metadata, sort_keys=True, default=str)
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_deterministic_summary(meta: Dict[str, Any]) -> Dict[str, Any]:
        """
        Builds the baseline structured summary completely offline.
        Uses verified facts only.
        """
        app_num = meta["app_number"]
        category = meta["category"]
        stage = meta["stage"]
        stage_code = meta["stage_code"]
        holder = meta["case_holder"]
        reverts = meta["revert_count"]
        risk_score = meta["risk_score"]
        risk_band = meta["risk_band"]
        sla_days = meta["sla_days"]

        # Executive summary text
        holder_desc = "Application is currently held by AICTE desk." if holder == "WITH_AICTE" else "Clock is paused: awaiting institution deficiency response."
        exec_summary = (
            f"Statutory dossier review for Application {app_num} ({category}). "
            f"The application currently resides in the '{stage}' stage under statutory SLA of {sla_days} working days. "
            f"{holder_desc} Administrative tracking records {reverts} deficiency revert cycle(s). "
            f"Delay risk rating is {risk_score}/100 ({risk_band})."
        )

        # Timeline highlights
        timeline_highlights = []
        for item in meta.get("timeline", []):
            action_desc = f"{item['stage']}: {item['action'].replace('_', ' ').title()}"
            if item.get("completed_at"):
                action_desc += f" (completed in {round(item['duration_hours'] or 0, 1)}h)"
            timeline_highlights.append({
                "stage": item["stage"],
                "description": action_desc,
                "timestamp": item.get("entered_at"),
            })
        if not timeline_highlights:
            timeline_highlights.append({
                "stage": stage,
                "description": f"Dossier entered {stage} stage.",
                "timestamp": None,
            })

        # Pending items
        pending_items = []
        for doc in meta.get("expired_docs", []):
            pending_items.append({"type": "EXPIRED_DOCUMENT", "description": f"Expired statutory document: {doc}"})
        for doc in meta.get("expiring_docs", []):
            pending_items.append({"type": "EXPIRING_DOCUMENT", "description": f"Document expiring within 30 days: {doc}"})
        for ut in meta.get("pending_undertakings", []):
            pending_items.append({"type": "PENDING_UNDERTAKING", "description": f"Unverified compliance undertaking: {ut}"})
        for v in meta.get("evc_visits", []):
            if v["status"] == "SCHEDULED" and not v["has_report"]:
                pending_items.append({"type": "PENDING_EVC_REPORT", "description": "Scheduled inspection report pending submission."})
        for code in meta.get("active_alert_codes", []):
            pending_items.append({"type": "ACTIVE_ALERT", "description": f"Unresolved statutory alert: {code}"})

        # Upcoming deadlines
        upcoming_deadlines = [
            {"item": f"{stage} Stage Statutory SLA", "limit": f"{sla_days} working days", "basis": "WORKING_DAYS"}
        ]
        if meta.get("expiring_docs"):
            upcoming_deadlines.append({
                "item": "Document Renewal Submission",
                "limit": "Before statutory expiry",
                "basis": "CALENDAR_DAYS"
            })

        # Top risk factors
        top_risk_factors = []
        for f in meta.get("risk_factors", []):
            if f.get("points", 0) > 0:
                top_risk_factors.append({
                    "factor": f["name"],
                    "points": f["points"],
                    "weight": f["weight"],
                    "explanation": f["explanation"],
                })

        # Suggested next steps for desk officer (advisory, decision support only)
        suggested_next_steps = []
        if meta.get("expired_docs"):
            suggested_next_steps.append("Request valid renewal deed/certificate for expired statutory documents.")
        if stage_code in ["EVC_PENDING", "EVC_SCHEDULED"]:
            suggested_next_steps.append("Confirm expert panel availability and coordinate inspection visit date.")
        elif stage_code == "SCRUTINY":
            suggested_next_steps.append("Complete checklist verification of land, building, and faculty norms.")
        elif stage_code == "SAC_SHC_REVIEW":
            suggested_next_steps.append("Review appellate committee observations before final competent authority decision.")
        else:
            suggested_next_steps.append("Review dossier timeline against stage SLA to prevent regulatory delay.")

        # Key findings
        key_findings = [
            f"Statutory dossier tracking in {stage} with {sla_days}d benchmark.",
            f"Clarification history: {reverts} clarification cycle(s) completed.",
            f"Regulatory risk index: {risk_score} points ({risk_band} band).",
        ]

        # Compliance flags
        compliance_flags = []
        if meta.get("deficiency_tags"):
            compliance_flags.extend([f"Deficiency on record: {t}" for t in meta["deficiency_tags"]])
        if meta.get("expired_docs"):
            compliance_flags.append(f"Statutory compliance lapse: {len(meta['expired_docs'])} expired document(s).")
        if not compliance_flags:
            compliance_flags.append("No active fatal statutory deficiencies identified.")

        risk_assessment = (
            f"DELAY RISK: {risk_band} ({risk_score}/100 points). "
            f"{'Elevated supervisory attention recommended.' if risk_band == 'HIGH' else 'Standard statutory tracking.'}"
        )

        return {
            "executive_summary": exec_summary,
            "key_findings": key_findings,
            "compliance_flags": compliance_flags,
            "risk_assessment": risk_assessment,
            "timeline_highlights": timeline_highlights,
            "pending_items": pending_items,
            "upcoming_deadlines": upcoming_deadlines,
            "suggested_next_steps": suggested_next_steps,
            "top_risk_factors": top_risk_factors,
            "risk_score_at_generation": risk_score,
            "source_label": "Template summary",
        }

    @staticmethod
    def polish_with_optional_llm(structured: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optional LLM smoothing: if LLM_PROVIDER is 'gemini' and API key is configured,
        call external provider to rewrite the executive summary and findings in smoother language.
        NEVER sends file contents or personal data.
        Falls back automatically on any error or timeout.
        """
        provider = getattr(settings, "LLM_PROVIDER", "none").lower()
        api_key = getattr(settings, "LLM_API_KEY", "")
        timeout = getattr(settings, "LLM_TIMEOUT_SECONDS", 10)

        if provider not in ["gemini"] or not api_key:
            return structured

        try:
            # Prepare minimal sanitized facts payload
            facts = {
                "application": meta["app_number"],
                "category": meta["category"],
                "current_stage": meta["stage"],
                "sla_days": meta["sla_days"],
                "reverts": meta["revert_count"],
                "risk_band": meta["risk_band"],
                "risk_score": meta["risk_score"],
                "pending_items_count": len(structured.get("pending_items", [])),
                "expired_docs": meta.get("expired_docs", []),
            }

            # Optional external call (or mocked client in tests)
            from app.services.llm import get_llm_client
            llm_client = get_llm_client()
            if hasattr(llm_client, "rewrite_summary"):
                rewritten = llm_client.rewrite_summary(facts, structured["executive_summary"])
                if rewritten and isinstance(rewritten, str):
                    structured["executive_summary"] = rewritten
                    structured["source_label"] = "AI-assisted summary"
                    return structured

            # Standard Gemini call when enabled with real API key
            import urllib.request
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            prompt_text = (
                f"You are a regulatory drafting assistant for the All India Council for Technical Education (AICTE). "
                f"Rewrite this executive case summary in concise, formal administrative language. "
                f"Do NOT add any facts, dates, or assumptions not present in these input facts: {json.dumps(facts)}. "
                f"Original summary: {structured['executive_summary']}"
            )
            req_body = json.dumps({"contents": [{"parts": [{"text": prompt_text}]}]}).encode("utf-8")
            req = urllib.request.Request(url, data=req_body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                resp_data = json.loads(response.read().decode("utf-8"))
                candidates = resp_data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts and "text" in parts[0]:
                        structured["executive_summary"] = parts[0]["text"].strip()
                        structured["source_label"] = "AI-assisted summary"
        except Exception as e:
            logger.warning(f"Optional LLM call skipped or failed ({e}); falling back to deterministic template.")
            structured["source_label"] = "Template summary"

        return structured

    @staticmethod
    def get_or_generate_summary(
        db: Session,
        application_id: int,
        force_regenerate: bool = False,
    ) -> CaseSummary:
        """
        Retrieve cached summary or generate a fresh one if inputs changed or regeneration requested.
        """
        app = db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise ValueError(f"Application {application_id} not found.")

        meta = CaseSummaryService.extract_metadata(db, app)
        input_hash = CaseSummaryService.compute_hash(meta)
        now = normalize_dt(ClockService.get_now())

        existing = db.query(CaseSummary).filter(
            CaseSummary.application_id == application_id
        ).first()

        # Check cache validity
        if existing and not force_regenerate and getattr(existing, "input_hash", None) == input_hash:
            return existing

        # Generate fresh deterministic summary
        structured = CaseSummaryService.generate_deterministic_summary(meta)

        # Apply optional LLM smoothing
        final_summary = CaseSummaryService.polish_with_optional_llm(structured, meta)

        if not existing:
            existing = CaseSummary(application_id=application_id)
            db.add(existing)

        existing.executive_summary = final_summary["executive_summary"]
        existing.key_findings = final_summary["key_findings"]
        existing.compliance_flags = final_summary["compliance_flags"]
        existing.risk_assessment = final_summary["risk_assessment"]
        existing.source_label = final_summary["source_label"]
        existing.input_hash = input_hash
        existing.timeline_highlights = final_summary["timeline_highlights"]
        existing.pending_items = final_summary["pending_items"]
        existing.upcoming_deadlines = final_summary["upcoming_deadlines"]
        existing.suggested_next_steps = final_summary["suggested_next_steps"]
        existing.risk_score_at_generation = final_summary["risk_score_at_generation"]
        existing.top_risk_factors = final_summary["top_risk_factors"]
        existing.generated_by = "AI_ASSISTANT" if final_summary["source_label"] == "AI-assisted summary" else "TEMPLATE_ENGINE"
        existing.last_generated_at = now

        db.commit()
        db.refresh(existing)
        return existing
