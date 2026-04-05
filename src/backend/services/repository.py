import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database import Article, Company, Digest, Subscriber

logger = logging.getLogger(__name__)


async def get_subscriber_with_companies(
    session: AsyncSession, subscriber_id: UUID
) -> Subscriber | None:
    """Load subscriber with eager-loaded companies and industries."""
    result = await session.execute(
        select(Subscriber)
        .where(Subscriber.id == subscriber_id)
        .options(selectinload(Subscriber.companies).selectinload(Company.industry))
    )
    return result.scalar_one_or_none()


async def get_last_digest_end(
    session: AsyncSession, subscriber_id: UUID
) -> datetime | None:
    """Get the period_end of the most recent sent digest."""
    result = await session.execute(
        select(Digest.period_end)
        .where(Digest.subscriber_id == subscriber_id, Digest.sent_at.is_not(None))
        .order_by(Digest.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def load_existing_articles(
    session: AsyncSession, urls: list[str]
) -> dict[str, Article]:
    """Batch-load existing articles by URL. Returns {url: Article}."""
    if not urls:
        return {}
    result = await session.execute(
        select(Article).where(Article.url.in_(urls))
    )
    return {a.url: a for a in result.scalars().all()}


async def create_digest(
    session: AsyncSession,
    subscriber_id: UUID,
    period_start: datetime,
    period_end: datetime,
) -> Digest:
    """Create and flush a new digest record."""
    digest = Digest(
        subscriber_id=subscriber_id,
        period_start=period_start,
        period_end=period_end,
    )
    session.add(digest)
    await session.flush()
    return digest
