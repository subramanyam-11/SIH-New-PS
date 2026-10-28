import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.config import settings
from app.models import EmailOutbox, CommunicationTemplate
from app.services.clock import ClockService, normalize_dt


class EmailService:
    @staticmethod
    def queue_email(
        db: Session,
        recipient_email: str,
        subject: str,
        body: str,
        recipient_user_id: Optional[int] = None,
        template_code: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
    ) -> EmailOutbox:
        """
        Creates a queued email outbox entry.
        Delivery is decoupled and governed by EMAIL_SEND_ENABLED.
        """
        now = ClockService.get_now()
        outbox_entry = EmailOutbox(
            recipient_email=recipient_email,
            recipient_user_id=recipient_user_id,
            subject=subject,
            body=body,
            status="QUEUED",
            template_code=template_code,
            entity_type=entity_type,
            entity_id=entity_id,
            attempts=0,
            created_at=now,
            updated_at=now,
        )
        db.add(outbox_entry)
        db.flush()

        # If sending is off, immediately mark as SUPPRESSED to keep outbox pristine
        if not settings.EMAIL_SEND_ENABLED:
            outbox_entry.status = "SUPPRESSED"
            outbox_entry.error_message = "Delivery suppressed: EMAIL_SEND_ENABLED is false (demo/local mode)"
            outbox_entry.sent_at = now
            db.flush()

        return outbox_entry

    @staticmethod
    def queue_from_template(
        db: Session,
        template_code: str,
        recipient_email: str,
        context: Dict[str, Any],
        recipient_user_id: Optional[int] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        default_subject: Optional[str] = None,
        default_body: Optional[str] = None,
    ) -> EmailOutbox:
        """
        Renders an email from database communication_templates if present,
        or falls back to default values.
        """
        tpl = db.query(CommunicationTemplate).filter(CommunicationTemplate.code == template_code).first()
        if tpl:
            subject = tpl.subject
            body = tpl.body_template
            for k, v in context.items():
                placeholder = f"{{{k}}}"
                subject = subject.replace(placeholder, str(v))
                body = body.replace(placeholder, str(v))
        else:
            subject = default_subject or f"[AICTE Alert] Notification regarding {entity_type or 'Record'}"
            body = default_body or "An official AICTE compliance notification has been issued."

        return EmailService.queue_email(
            db=db,
            recipient_email=recipient_email,
            subject=subject,
            body=body,
            recipient_user_id=recipient_user_id,
            template_code=template_code,
            entity_type=entity_type,
            entity_id=entity_id,
        )

    @staticmethod
    def process_outbox(db: Session, limit: int = 50) -> Dict[str, int]:
        """
        Processes pending QUEUED entries in the email outbox.
        """
        now = ClockService.get_now()
        queued = db.query(EmailOutbox).filter(EmailOutbox.status == "QUEUED").limit(limit).all()

        counts = {"sent": 0, "suppressed": 0, "failed": 0}
        if not queued:
            return counts

        if not settings.EMAIL_SEND_ENABLED:
            for item in queued:
                item.status = "SUPPRESSED"
                item.error_message = "Delivery suppressed: EMAIL_SEND_ENABLED is false"
                item.sent_at = now
                counts["suppressed"] += 1
            db.commit()
            return counts

        # SMTP Sending when enabled
        try:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
            if settings.SMTP_TLS:
                server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

            for item in queued:
                item.attempts += 1
                try:
                    msg = MIMEMultipart()
                    msg["From"] = settings.SMTP_FROM_EMAIL
                    msg["To"] = item.recipient_email
                    msg["Subject"] = item.subject
                    msg.attach(MIMEText(item.body, "plain"))

                    server.send_message(msg)
                    item.status = "SENT"
                    item.sent_at = now
                    item.error_message = None
                    counts["sent"] += 1
                except Exception as ex:
                    item.status = "FAILED"
                    item.error_message = str(ex)
                    counts["failed"] += 1

            server.quit()
        except Exception as ex:
            for item in queued:
                item.attempts += 1
                item.status = "FAILED"
                item.error_message = f"SMTP Server connection error: {str(ex)}"
                counts["failed"] += 1

        db.commit()
        return counts
