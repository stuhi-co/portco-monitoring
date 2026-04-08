import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_subscriber
from backend.config import settings
from backend.database import get_session, Digest, Subscriber
from backend.schemas import DigestSummary

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["digests"])


@router.get("/subscriptions/{subscriber_id}/digests", response_model=list[DigestSummary])
async def list_digests(
    subscriber_id: UUID,
    current_subscriber: Subscriber = Depends(get_current_subscriber),
    session: AsyncSession = Depends(get_session),
):
    if current_subscriber.id != subscriber_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    result = await session.execute(
        select(Digest)
        .where(Digest.subscriber_id == subscriber_id)
        .order_by(Digest.created_at.desc())
    )
    return result.scalars().all()


@router.get("/digests/{digest_id}", response_class=HTMLResponse)
async def view_digest(
    digest_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Digest).where(Digest.id == digest_id))
    digest = result.scalar_one_or_none()
    if digest is None:
        raise HTTPException(status_code=404, detail="Digest not found")
    return HTMLResponse(content=digest.html_content or "<p>No content</p>")


@router.post("/subscriptions/{subscriber_id}/trigger", status_code=202)
async def trigger_digest(
    subscriber_id: UUID,
    background_tasks: BackgroundTasks,
    current_subscriber: Subscriber = Depends(get_current_subscriber),
    session: AsyncSession = Depends(get_session),
):
    if current_subscriber.id != subscriber_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    subscriber = current_subscriber
    if not subscriber.is_active:
        raise HTTPException(status_code=400, detail="Subscription is inactive")

    # Cooldown check
    latest_result = await session.execute(
        select(Digest)
        .where(Digest.subscriber_id == subscriber_id)
        .order_by(Digest.created_at.desc())
        .limit(1)
    )
    latest_digest = latest_result.scalar_one_or_none()
    if latest_digest is not None:
        cooldown = timedelta(hours=settings.digest_cooldown_hours)
        created = latest_digest.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        elapsed = datetime.now(timezone.utc) - created
        if elapsed < cooldown:
            remaining = cooldown - elapsed
            hours, remainder = divmod(int(remaining.total_seconds()), 3600)
            minutes = remainder // 60
            raise HTTPException(
                status_code=429,
                detail=f"Please wait {hours}h {minutes}m before generating another digest",
            )

    background_tasks.add_task(_run_pipeline, subscriber_id)
    return {"message": "Digest generation started", "subscriber_id": str(subscriber_id)}


async def _run_pipeline(subscriber_id: UUID) -> None:
    from backend.pipeline import run_digest_pipeline

    try:
        await run_digest_pipeline(subscriber_id)
    except Exception:
        logger.exception("Pipeline failed for subscriber %s", subscriber_id)
