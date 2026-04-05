import logging

import resend

from backend.config import settings

logger = logging.getLogger(__name__)

resend.api_key = settings.resend_api_key


async def send_digest_email(
    to_email: str,
    subject: str,
    html_content: str,
) -> str | None:
    """Send a digest email via Resend. Returns the email ID or None on failure."""
    try:
        result = resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        })
        email_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        logger.info("Sent digest to %s, email_id=%s", to_email, email_id)
        return email_id
    except Exception:
        logger.exception("Failed to send email to %s", to_email)
        return None
