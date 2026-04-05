import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from uuid import UUID

from backend.config import settings
from backend.database import Article, Company, async_session_factory
from backend.services.analysis import synthesize_company_developments
from backend.services.digest import compile_digest
from backend.services.email import send_digest_email
from backend.services.repository import (
    create_digest,
    get_last_digest_end,
    get_subscriber_with_companies,
    load_existing_articles,
)
from backend.schemas import SourceType
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
        subscriber = await get_subscriber_with_companies(session, subscriber_id)
        if subscriber is None or not subscriber.is_active:
            logger.warning("Subscriber %s not found or inactive", subscriber_id)
            return

        # Determine time window
        period_end = datetime.now(timezone.utc)
        last_end = await get_last_digest_end(session, subscriber_id)
        period_start = last_end if last_end else period_end - timedelta(days=7)

        logger.info(
            "Running pipeline for %s (%s), period %s to %s",
            subscriber.email,
            subscriber_id,
            period_start.isoformat(),
            period_end.isoformat(),
        )

        # ── Step 1: Search ────────────────────────────────────────────────────
        raw_results, industry_articles = await _collect_news(subscriber.companies, period_start)

        if not raw_results:
            logger.info("No news found for subscriber %s", subscriber.email)
            return

        # Build URL → source_type mapping per company (before dedup loses source_type)
        _PRIORITY = {SourceType.company: 2, SourceType.competitor: 1, SourceType.industry: 0}
        source_types: dict[str, dict[str, str]] = {}
        for company_name, search_results in raw_results.items():
            mapping: dict[str, str] = {}
            for sr in search_results:
                existing = mapping.get(sr.url)
                if existing is None or _PRIORITY[sr.source_type] > _PRIORITY.get(SourceType(existing), -1):
                    mapping[sr.url] = sr.source_type.value
            source_types[company_name] = mapping

        # ── Step 2: Deduplicate ───────────────────────────────────────────────
        articles = await _dedup_and_store_articles(session, raw_results)

        if not articles:
            logger.info("All articles already seen for subscriber %s", subscriber.email)
            return

        # ── Step 3: Synthesize ────────────────────────────────────────────────
        developments_by_company = await _synthesize_all(subscriber, articles, source_types)

        # ── Step 4: Create digest record ──────────────────────────────────────
        # Count unique source URLs across all developments
        all_source_urls: set[str] = set()
        for developments in developments_by_company.values():
            for d in developments:
                all_source_urls.update(d["source_urls"])
        total_articles = len(all_source_urls)

        digest = await create_digest(session, subscriber.id, period_start, period_end)

        # ── Step 5: Compile digest HTML ───────────────────────────────────────
        companies_by_industry = _group_companies_by_industry(subscriber.companies)

        period_start_str = period_start.strftime("%b %d")
        period_end_str = period_end.strftime("%b %d, %Y")

        # Convert industry SearchResults to dicts for the digest layer
        industry_article_dicts = {
            industry: [
                {"title": sr.title or "", "summary": sr.summary or ""}
                for sr in results
            ]
            for industry, results in industry_articles.items()
        }

        subject, html = await compile_digest(
            subscriber_email=subscriber.email,
            subscriber_id=str(subscriber.id),
            fund_description=subscriber.fund_description,
            companies_by_industry=companies_by_industry,
            developments_by_company=developments_by_company,
            industry_articles=industry_article_dicts,
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


async def _collect_news(
    companies: list[Company],
    start_date: datetime,
) -> tuple[dict[str, list[SearchResult]], dict[str, list[SearchResult]]]:
    """Collect news for all companies and their industries (in parallel).

    Returns:
        (by_company, by_industry) where:
        - by_company: {company_name: [SearchResult, ...]}
        - by_industry: {industry_name: [SearchResult, ...]}
    """
    results: dict[str, list[SearchResult]] = defaultdict(list)
    industry_results_map: dict[str, list[SearchResult]] = {}

    # Fan out company + competitor searches in parallel
    async def _search_for_company(company: Company) -> tuple[str, str | None]:
        industry_name = company.industry.name if company.industry else None

        company_results = await search_company_news(company.name, industry_name, start_date)
        results[company.name].extend(company_results)

        if company.competitors:
            comp_results = await search_competitor_news(company.competitors, industry_name, start_date)
            results[company.name].extend(comp_results)

        return company.name, industry_name

    company_tasks = [_search_for_company(c) for c in companies]
    company_results = await asyncio.gather(*company_tasks)

    # Industry searches (one per unique industry, in parallel)
    seen_industries: set[str] = set()
    industry_tasks: dict[str, asyncio.Task[list[SearchResult]]] = {}
    for _, industry_name in company_results:
        if industry_name and industry_name not in seen_industries:
            seen_industries.add(industry_name)
            industry_tasks[industry_name] = search_industry_news(industry_name, start_date)

    if industry_tasks:
        industry_results_list = await asyncio.gather(*industry_tasks.values())
        for industry_name, ind_results in zip(industry_tasks.keys(), industry_results_list):
            industry_results_map[industry_name] = ind_results
            for c in companies:
                if (c.industry and c.industry.name) == industry_name:
                    results[c.name].extend(ind_results)

    return dict(results), industry_results_map


async def _dedup_and_store_articles(
    session,
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

    # Batch-load all existing articles in one query
    existing_articles = await load_existing_articles(session, list(all_results.keys()))

    # Store new articles, reuse existing
    for url, (sr, company_names) in all_results.items():
        if url in existing_articles:
            article = existing_articles[url]
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

        for cn in company_names:
            if article not in articles_by_company[cn]:
                articles_by_company[cn].append(article)

    await session.flush()
    return dict(articles_by_company)


async def _synthesize_all(
    subscriber,
    articles_by_company: dict[str, list[Article]],
    source_types: dict[str, dict[str, str]],
) -> dict[str, list[dict]]:
    """Synthesize all articles for each company into deduplicated developments (in parallel).

    Returns: {company_name: [{development data}]}
    """
    company_map = {c.name: c for c in subscriber.companies}

    async def _synthesize_one(company_name: str, articles: list[Article]) -> tuple[str, list[dict]]:
        company = company_map.get(company_name)
        if not company:
            return company_name, []

        url_source_types = source_types.get(company_name, {})

        article_dicts = [
            {
                "url": a.url,
                "title": a.title or "",
                "summary": a.summary or "",
                "highlights": a.highlights or [],
                "source_type": url_source_types.get(a.url, "company"),
            }
            for a in articles
        ]

        industry_name = company.industry.name if company.industry else None

        developments = await synthesize_company_developments(
            articles=article_dicts,
            company_name=company_name,
            company_description=company.description,
            company_industry=industry_name,
            fund_description=subscriber.fund_description,
        )

        filtered = [
            d.model_dump()
            for d in developments
            if d.relevance_score >= settings.relevance_threshold
        ]
        filtered.sort(key=lambda x: -x["relevance_score"])
        return company_name, filtered[:settings.max_developments_per_company]

    tasks = [_synthesize_one(name, arts) for name, arts in articles_by_company.items()]
    results = await asyncio.gather(*tasks)
    return {name: devs for name, devs in results if devs}


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
