import asyncio
import logging

import resend

from backend.config import settings

logger = logging.getLogger(__name__)

resend.api_key = settings.resend_api_key


async def send_magic_link_email(to_email: str, token: str) -> str | None:
    """Send a magic link sign-in email via Resend. Returns the email ID or None on failure."""
    link = f"{settings.frontend_base_url}/auth/verify?token={token}"
    html = f"""\
<div style="font-family: sans-serif; max-width: 480px; margin: 0 auto; padding: 32px 0;">
  <h2 style="margin-bottom: 16px;">Sign in to Stuhi</h2>
  <p style="margin-bottom: 24px; color: #555;">Click the button below to sign in to your Stuhi Portfolio Intelligence account. This link expires in {settings.magic_link_ttl_minutes} minutes.</p>
  <a href="{link}" style="display: inline-block; padding: 12px 24px; background-color: #0f172a; color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: 600;">Sign In</a>
  <p style="margin-top: 24px; font-size: 13px; color: #888;">If you didn't request this link, you can safely ignore this email.</p>
</div>"""
    try:
        result = await asyncio.to_thread(
            resend.Emails.send,
            {
                "from": settings.email_from,
                "to": [to_email],
                "subject": "Sign in to Stuhi",
                "html": html,
            },
        )
        email_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        logger.info("Sent magic link to %s, email_id=%s", to_email, email_id)
        return email_id
    except Exception:
        logger.exception("Failed to send magic link email to %s", to_email)
        return None


async def send_digest_email(
    to_email: str,
    subject: str,
    html_content: str,
) -> str | None:
    """Send a digest email via Resend. Returns the email ID or None on failure."""
    try:
        result = await asyncio.to_thread(
            resend.Emails.send,
            {
                "from": settings.email_from,
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            },
        )
        email_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        logger.info("Sent digest to %s, email_id=%s", to_email, email_id)
        return email_id
    except Exception:
        logger.exception("Failed to send email to %s", to_email)
        return None
