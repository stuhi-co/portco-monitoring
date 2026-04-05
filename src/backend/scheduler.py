import logging

from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from backend.config import settings
from backend.database import async_session_factory, Subscriber
from backend.pipeline import run_digest_pipeline

logger = logging.getLogger(__name__)


async def run_all_digests() -> None:
    """Run digest pipeline for all active subscribers."""
    logger.info("Scheduled digest run starting")

    async with async_session_factory() as session:
        result = await session.execute(
            select(Subscriber).where(Subscriber.is_active.is_(True))
        )
        subscribers = result.scalars().all()

    for sub in subscribers:
        try:
            logger.info("Running digest for %s", sub.email)
            await run_digest_pipeline(sub.id)
        except Exception:
            logger.exception("Digest pipeline failed for %s", sub.email)


def get_digest_trigger() -> CronTrigger:
    return CronTrigger(
        day_of_week=settings.digest_cron_day_of_week,
        hour=settings.digest_cron_hour,
        minute=0,
    )
