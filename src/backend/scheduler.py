import logging
from datetime import datetime, timezone

from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from zoneinfo import ZoneInfo

from backend.database import async_session_factory, Subscriber
from backend.pipeline import run_digest_pipeline

logger = logging.getLogger(__name__)

DAY_NAMES = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


async def run_scheduled_digests() -> None:
    """Hourly check: run digest for subscribers whose preferred day/hour matches now."""
    utc_now = datetime.now(timezone.utc)
    logger.info("Hourly digest check at %s UTC", utc_now.strftime("%Y-%m-%d %H:%M"))

    async with async_session_factory() as session:
        result = await session.execute(
            select(Subscriber).where(Subscriber.is_active.is_(True))
        )
        subscribers = result.scalars().all()

    for sub in subscribers:
        try:
            tz = ZoneInfo(sub.timezone)
        except (KeyError, ValueError):
            logger.warning("Invalid timezone %r for %s, falling back to UTC", sub.timezone, sub.email)
            tz = timezone.utc

        local_now = utc_now.astimezone(tz)
        local_day = DAY_NAMES[local_now.weekday()]
        local_hour = local_now.hour

        should_run = local_hour == sub.preferred_hour
        if sub.frequency == "weekly":
            should_run = should_run and local_day == sub.preferred_day

        if should_run:
            try:
                logger.info("Running scheduled digest for %s (tz=%s, %s %02d:00)", sub.email, sub.timezone, local_day, local_hour)
                await run_digest_pipeline(sub.id)
            except Exception:
                logger.exception("Digest pipeline failed for %s", sub.email)


def get_digest_trigger() -> CronTrigger:
    return CronTrigger(minute=0)
