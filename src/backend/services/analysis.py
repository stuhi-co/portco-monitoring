import logging

import anthropic
from pydantic import BaseModel, Field
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from backend.config import settings
from backend.prompts import (
    DIGEST_SYSTEM_PROMPT,
    SYNTHESIS_SYSTEM_PROMPT,
    build_executive_overview_prompt,
    build_industry_pulse_prompt,
    build_synthesis_prompt,
)
from backend.schemas import ArticleCategory, Development

logger = logging.getLogger(__name__)

client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

_retry_anthropic = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(
        (anthropic.APITimeoutError, anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.InternalServerError)
    ),
    reraise=True,
)


# ── LLM output models (index-based, never exposed outside this module) ───────


class _LLMDevelopment(BaseModel):
    headline: str
    summary: str
    category: ArticleCategory
    relevance_score: float = Field(ge=0, le=10)
    pe_insight: str
    source_indices: list[int] = Field(
        min_length=1,
        description="1-based indices of the articles that support this development.",
    )


class _SynthesisResponse(BaseModel):
    developments: list[_LLMDevelopment]


# ── Synthesis ────────────────────────────────────────────────────────────────


@_retry_anthropic
async def synthesize_company_developments(
    articles: list[dict],
    company_name: str,
    company_description: str | None,
    company_industry: str | None,
    fund_description: str | None,
) -> list[Development]:
    """Synthesize all articles for a company into deduplicated developments.

    Each article dict should have: url, title, summary, highlights.
    Returns list of validated Development objects with resolved URLs.
    """
    if not articles:
        return []

    # Build index → URL mapping (1-based)
    index_to_url = {i: a["url"] for i, a in enumerate(articles, 1)}

    prompt = build_synthesis_prompt(
        articles=articles,
        company_name=company_name,
        company_description=company_description,
        company_industry=company_industry,
        fund_description=fund_description,
    )

    try:
        response = await client.messages.parse(
            model=settings.claude_model,
            max_tokens=2000,
            system=SYNTHESIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            output_format=_SynthesisResponse,
        )

        parsed = response.parsed_output
        if not parsed:
            logger.error("No parsed output in synthesis response for %s", company_name)
            return []

        developments = []
        for raw in parsed.developments:
            # Resolve valid indices to URLs, skip out-of-range indices
            source_urls = [
                index_to_url[i]
                for i in raw.source_indices
                if i in index_to_url
            ]
            if not source_urls:
                logger.warning("Dropping development with no valid source indices: %s", raw.headline)
                continue

            developments.append(
                Development(
                    headline=raw.headline,
                    summary=raw.summary,
                    category=raw.category,
                    relevance_score=raw.relevance_score,
                    pe_insight=raw.pe_insight,
                    source_urls=source_urls,
                )
            )

        return developments

    except (anthropic.APITimeoutError, anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.InternalServerError):
        raise  # Let tenacity handle retries
    except Exception:
        logger.exception("Failed to synthesize developments for %s", company_name)
        return []


# ── Digest text generation ───────────────────────────────────────────────────


@_retry_anthropic
async def generate_executive_overview(
    developments_by_company: dict[str, list[dict]],
    fund_description: str | None,
) -> str:
    """Generate the executive overview for the top of the digest."""
    summary_parts = []
    for company_name, developments in developments_by_company.items():
        relevant = [d for d in developments if d.get("relevance_score", 0) >= settings.relevance_threshold]
        if relevant:
            insights = "; ".join(d["pe_insight"] for d in relevant[:3])
            summary_parts.append(f"- {company_name}: {insights}")

    if not summary_parts:
        return "No significant portfolio developments this period."

    prompt = build_executive_overview_prompt(
        company_summary="\n".join(summary_parts),
        fund_description=fund_description,
    )

    response = await client.messages.create(
        model=settings.claude_model,
        max_tokens=300,
        system=DIGEST_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


@_retry_anthropic
async def generate_industry_pulse(
    industry_name: str,
    articles: list[dict],
) -> str:
    """Generate a broad industry pulse from raw Exa industry articles.

    Each article dict should have: title, summary.
    """
    if not articles:
        return f"No significant developments in {industry_name.replace('_', ' ')} this period."

    prompt = build_industry_pulse_prompt(
        industry_name=industry_name,
        articles=articles,
    )

    response = await client.messages.create(
        model=settings.claude_model,
        max_tokens=150,
        system=DIGEST_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()
