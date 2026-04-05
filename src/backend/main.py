import logging
from contextlib import asynccontextmanager

from apscheduler import AsyncScheduler
from fastapi import FastAPI

from backend.api.digests import router as digests_router
from backend.api.subscriptions import router as subscriptions_router
from backend.scheduler import get_digest_trigger, run_all_digests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncScheduler() as scheduler:
        await scheduler.add_schedule(
            run_all_digests,
            get_digest_trigger(),
            id="weekly_digest",
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

app.include_router(subscriptions_router)
app.include_router(digests_router)
