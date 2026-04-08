import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from apscheduler import AsyncScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import delete

from backend.api.auth import router as auth_router
from backend.api.digests import router as digests_router
from backend.api.subscriptions import router as subscriptions_router
from backend.config import settings
from backend.database import LoginToken, Session, async_session_factory
from backend.scheduler import get_digest_trigger, run_scheduled_digests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


async def cleanup_expired_auth() -> None:
    """Delete expired login tokens and sessions."""
    async with async_session_factory() as session:
        now = datetime.now(timezone.utc)
        await session.execute(delete(LoginToken).where(LoginToken.expires_at < now))
        await session.execute(delete(Session).where(Session.expires_at < now))
        await session.commit()
        logger.info("Cleaned up expired auth tokens and sessions")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncScheduler() as scheduler:
        await scheduler.add_schedule(
            run_scheduled_digests,
            get_digest_trigger(),
            id="hourly_digest_check",
        )
        await scheduler.add_schedule(
            cleanup_expired_auth,
            IntervalTrigger(hours=6),
            id="auth_cleanup",
        )
        await scheduler.start_in_background()
        logger.info("Scheduler started")
        yield
    logger.info("Scheduler stopped")


app = FastAPI(
    title="Stuhi Portfolio Intelligence",
    description="PE portfolio company news intelligence — automated digests with PE-focused insights",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(subscriptions_router)
app.include_router(digests_router)
