import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.config import settings
from backend.database import async_session_factory, Article, Company, Digest, Subscriber
from backend.services.analysis import synthesize_company_developments
from backend.services.digest import compile_digest
from backend.services.email import send_digest_email
from backend.services.search import (
    SearchResult,
    search_company_news,
    search_competitor_news,
    search_industry_news,
)

logger = logging.getLogger(__name__)


async def run_digest_pipeline(subscriber_id: UUID) -> None:
    """Full pipeline: search → dedup → synthesize → compile → send."""
    async with async_session_factory() as session:
        # Load subscriber with companies and industries
        result = await session.execute(
            select(Subscriber)
            .where(Subscriber.id == subscriber_id)
            .options(selectinload(Subscriber.companies).selectinload(Company.industry))
        )
        subscriber = result.scalar_one_or_none()
        if subscriber is None or not subscriber.is_active:
            logger.warning("Subscriber %s not found or inactive", subscriber_id)
            return

        # Determine time window
        period_end = datetime.now(timezone.utc)
        period_start = await _get_period_start(session, subscriber_id, period_end)

        logger.info(
            "Running pipeline for %s (%s), period %s to %s",
            subscriber.email,
            subscriber_id,
            period_start.isoformat(),
            period_end.isoformat(),
        )

        # ── Step 1: Search ────────────────────────────────────────────────────
        raw_results = await _collect_news(subscriber.companies, period_start)

        if not raw_results:
            logger.info("No news found for subscriber %s", subscriber.email)
            return

        # ── Step 2: Deduplicate ───────────────────────────────────────────────
        articles = await _dedup_and_store_articles(session, raw_results)

        if not articles:
            logger.info("All articles already seen for subscriber %s", subscriber.email)
            return

        # ── Step 3: Synthesize ────────────────────────────────────────────────
        developments_by_company = await _synthesize_all(subscriber, articles)

        # ── Step 4: Create digest record ──────────────────────────────────────
        # Count unique source URLs across all developments
        all_source_urls: set[str] = set()
        for developments in developments_by_company.values():
            for d in developments:
                all_source_urls.update(d["source_urls"])
        total_articles = len(all_source_urls)

        digest = Digest(
            subscriber_id=subscriber.id,
            period_start=period_start,
            period_end=period_end,
        )
        session.add(digest)
        await session.flush()

        # ── Step 5: Compile digest HTML ───────────────────────────────────────
        companies_by_industry = _group_companies_by_industry(subscriber.companies)

        period_start_str = period_start.strftime("%b %d")
        period_end_str = period_end.strftime("%b %d, %Y")

        subject, html = await compile_digest(
            subscriber_email=subscriber.email,
            subscriber_id=str(subscriber.id),
            fund_description=subscriber.fund_description,
            companies_by_industry=companies_by_industry,
            developments_by_company=developments_by_company,
            period_start=period_start_str,
            period_end=period_end_str,
        )

        digest.subject = subject
        digest.html_content = html
        digest.article_count = total_articles

        # ── Step 6: Send email ────────────────────────────────────────────────
        email_id = await send_digest_email(subscriber.email, subject, html)
        if email_id:
            digest.sent_at = datetime.now(timezone.utc)

        await session.commit()
        logger.info(
            "Pipeline complete for %s: %d articles analyzed, digest_id=%s",
            subscriber.email,
            total_articles,
            digest.id,
        )


async def _get_period_start(
    session: AsyncSession, subscriber_id: UUID, period_end: datetime
) -> datetime:
    """Get the start of the period — end of last digest, or 7 days ago."""
    result = await session.execute(
        select(Digest.period_end)
        .where(Digest.subscriber_id == subscriber_id, Digest.sent_at.is_not(None))
        .order_by(Digest.created_at.desc())
        .limit(1)
    )
    last_end = result.scalar_one_or_none()
    if last_end:
        return last_end
    return period_end - timedelta(days=7)


async def _collect_news(
    companies: list[Company],
    start_date: datetime,
) -> dict[str, list[SearchResult]]:
    """Collect news for all companies and their industries.

    Returns: {company_name: [SearchResult, ...]}
    """
    results: dict[str, list[SearchResult]] = defaultdict(list)
    seen_industries: set[str] = set()

    for company in companies:
        industry_name = company.industry.name if company.industry else None

        # Company news
        company_results = await search_company_news(
            company.name, industry_name, start_date
        )
        results[company.name].extend(company_results)

        # Competitor news
        if company.competitors:
            comp_results = await search_competitor_news(
                company.competitors, industry_name, start_date
            )
            results[company.name].extend(comp_results)

        # Industry news (once per industry)
        if industry_name and industry_name not in seen_industries:
            seen_industries.add(industry_name)
            industry_results = await search_industry_news(industry_name, start_date)
            # Add industry results to all companies in this industry
            for c in companies:
                c_industry = c.industry.name if c.industry else None
                if c_industry == industry_name:
                    results[c.name].extend(industry_results)

    return dict(results)


async def _dedup_and_store_articles(
    session: AsyncSession,
    raw_results: dict[str, list[SearchResult]],
) -> dict[str, list[Article]]:
    """Deduplicate articles by URL and store new ones.

    Returns: {company_name: [Article, ...]}
    """
    articles_by_company: dict[str, list[Article]] = defaultdict(list)

    # Collect all unique URLs across all companies
    all_results: dict[str, tuple[SearchResult, list[str]]] = {}
    for company_name, search_results in raw_results.items():
        for sr in search_results:
            if sr.url not in all_results:
                all_results[sr.url] = (sr, [])
            all_results[sr.url][1].append(company_name)

    # Check which URLs already exist
    existing_urls = set()
    if all_results:
        url_list = list(all_results.keys())
        result = await session.execute(
            select(Article.url).where(Article.url.in_(url_list))
        )
        existing_urls = {row[0] for row in result.all()}

    # Store new articles
    url_to_article: dict[str, Article] = {}
    for url, (sr, company_names) in all_results.items():
        if url in existing_urls:
            # Load existing article
            result = await session.execute(select(Article).where(Article.url == url))
            article = result.scalar_one()
        else:
            article = Article(
                url=sr.url,
                title=sr.title,
                summary=sr.summary,
                highlights=sr.highlights,
                author=sr.author,
                published_at=sr.published_at,
            )
            session.add(article)

        url_to_article[url] = article

        for cn in company_names:
            if article not in articles_by_company[cn]:
                articles_by_company[cn].append(article)

    await session.flush()
    return dict(articles_by_company)


async def _synthesize_all(
    subscriber: Subscriber,
    articles_by_company: dict[str, list[Article]],
) -> dict[str, list[dict]]:
    """Synthesize all articles for each company into deduplicated developments.

    Returns: {company_name: [{development data}]}
    """
    developments_by_company: dict[str, list[dict]] = {}

    company_map = {c.name: c for c in subscriber.companies}

    for company_name, articles in articles_by_company.items():
        company = company_map.get(company_name)
        if not company:
            continue

        # Prepare articles for synthesis
        article_dicts = [
            {
                "url": a.url,
                "title": a.title or "",
                "summary": a.summary or "",
                "highlights": a.highlights or [],
            }
            for a in articles
        ]

        industry_name = company.industry.name if company.industry else None

        # Run Claude synthesis
        developments = await synthesize_company_developments(
            articles=article_dicts,
            company_name=company_name,
            company_description=company.description,
            company_industry=industry_name,
            fund_description=subscriber.fund_description,
        )

        # Filter by relevance threshold, sort, and limit
        filtered = [
            d.model_dump()
            for d in developments
            if d.relevance_score >= settings.relevance_threshold
        ]
        filtered.sort(key=lambda x: -x["relevance_score"])
        developments_by_company[company_name] = filtered[:settings.max_developments_per_company]

    return developments_by_company


def _group_companies_by_industry(companies: list[Company]) -> dict[str, list[dict]]:
    """Group companies by industry for digest rendering."""
    by_industry: dict[str, list[dict]] = defaultdict(list)
    for c in companies:
        industry_name = c.industry.name if c.industry else "other"
        by_industry[industry_name].append({
            "name": c.name,
            "id": str(c.id),
        })
    return dict(by_industry)
