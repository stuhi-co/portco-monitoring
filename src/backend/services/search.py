import logging
from dataclasses import dataclass, field
from datetime import datetime

from exa_py import AsyncExa
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from backend.config import settings

logger = logging.getLogger(__name__)

exa = AsyncExa(api_key=settings.exa_api_key)

_retry_exa = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(ValueError),
    reraise=True,
)


@dataclass
class SearchResult:
    url: str
    title: str | None = None
    summary: str | None = None
    highlights: list[str] = field(default_factory=list)
    author: str | None = None
    published_at: datetime | None = None


def _parse_results(exa_results) -> list[SearchResult]:
    """Convert Exa search results to our internal dataclass."""
    parsed: list[SearchResult] = []
    for r in exa_results.results:
        published = None
        if r.published_date:
            try:
                published = datetime.fromisoformat(r.published_date)
            except (ValueError, TypeError):
                pass

        parsed.append(
            SearchResult(
                url=r.url,
                title=r.title,
                summary=r.summary,
                highlights=r.highlights or [],
                author=r.author,
                published_at=published,
            )
        )
    return parsed


@_retry_exa
async def search_company_news(
    company_name: str,
    industry: str | None,
    start_date: datetime | None,
) -> list[SearchResult]:
    """Search for recent news about a specific company."""
    industry_ctx = f" in {industry.replace('_', ' ')}" if industry else ""
    query = (
        f"Recent news about {company_name}: business developments, product launches, "
        f"funding rounds, leadership changes, and strategic moves{industry_ctx}"
    )

    kwargs: dict = {
        "query": query,
        "type": "auto",
        "category": "news",
        "num_results": settings.exa_results_per_query,
        "contents": {
            "highlights": {"num_sentences": 5},
            "summary": True,
        },
        "system_prompt": "Prefer primary sources. Avoid duplicate results.",
    }

    if start_date:
        kwargs["start_published_date"] = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")

    logger.info("Searching news for %s", company_name)
    result = await exa.search(**kwargs)
    return _parse_results(result)


@_retry_exa
async def search_competitor_news(
    competitors: list[str],
    industry: str | None,
    start_date: datetime | None,
) -> list[SearchResult]:
    """Search for news about a company's competitors."""
    if not competitors:
        return []

    comp_names = ", ".join(competitors[:5])
    industry_ctx = f" in {industry.replace('_', ' ')}" if industry else ""
    query = (
        f"News about {comp_names}: funding, acquisitions, product launches, "
        f"and competitive moves{industry_ctx}"
    )

    kwargs: dict = {
        "query": query,
        "type": "auto",
        "category": "news",
        "num_results": settings.exa_results_per_query,
        "contents": {
            "highlights": {"num_sentences": 5},
            "summary": True,
        },
        "system_prompt": "Prefer primary sources. Avoid duplicate results.",
    }

    if start_date:
        kwargs["start_published_date"] = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")

    logger.info("Searching competitor news for %s", comp_names)
    result = await exa.search(**kwargs)
    return _parse_results(result)


@_retry_exa
async def search_industry_news(
    industry: str,
    start_date: datetime | None,
) -> list[SearchResult]:
    """Search for broad industry trends and developments."""
    industry_label = industry.replace("_", " ")
    query = (
        f"Latest trends and developments in {industry_label}: market shifts, "
        f"regulatory changes, M&A activity, emerging competitors, and investment themes"
    )

    kwargs: dict = {
        "query": query,
        "type": "auto",
        "category": "news",
        "num_results": settings.exa_results_per_query,
        "contents": {
            "highlights": {"num_sentences": 5},
            "summary": True,
        },
        "system_prompt": "Prefer primary sources. Avoid duplicate results.",
    }

    if start_date:
        kwargs["start_published_date"] = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")

    logger.info("Searching industry news for %s", industry_label)
    result = await exa.search(**kwargs)
    return _parse_results(result)
