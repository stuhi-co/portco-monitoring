import logging

import anthropic

from backend.config import settings
from backend.schemas import Development

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

SYNTHESIS_SYSTEM_PROMPT = """\
You are a PE (Private Equity) analyst specializing in portfolio company intelligence.
You synthesize multiple news articles into distinct developments and provide structured
assessments focused on what matters to PE investors: valuation signals, competitive dynamics,
growth indicators, risk factors, and strategic opportunities.

Be concise but do not omit material information. Every development must capture the full picture.
Only report facts explicitly stated in the articles. Do not speculate or add information not present in the sources.
Only reference URLs from the provided article list. Do not fabricate or infer URLs.
If multiple articles cover the same event, merge them into a single development and list all source URLs.
Each pe_insight must be one actionable sentence grounded in the article content."""


class SynthesisResponse(anthropic.BaseModel):
    developments: list[Development]


def _build_synthesis_prompt(
    articles: list[dict],
    company_name: str,
    company_description: str | None,
    company_industry: str | None,
    fund_description: str | None,
) -> str:
    # Cap highlights per article if there are many articles
    max_highlights = 3 if len(articles) > 15 else 5

    article_blocks = []
    for i, a in enumerate(articles, 1):
        highlights = a.get("highlights", [])[:max_highlights]
        highlights_text = "\n".join(f"  - {h}" for h in highlights) if highlights else "  N/A"
        article_blocks.append(
            f"[{i}] URL: {a['url']}\n"
            f"    Title: {a.get('title', 'N/A')}\n"
            f"    Summary: {a.get('summary', 'N/A')}\n"
            f"    Highlights:\n{highlights_text}"
        )

    articles_text = "\n\n".join(article_blocks)

    return f"""\
Analyze these articles for PE relevance to the portfolio company and synthesize them into
distinct developments. Deduplicate overlapping coverage — if multiple articles cover the same
event or topic, merge them into a single development citing all relevant source URLs.

COMPANY: {company_name}
COMPANY DESCRIPTION: {company_description or 'N/A'}
INDUSTRY: {company_industry or 'N/A'}
FUND CONTEXT: {fund_description or 'N/A'}

ARTICLES:
{articles_text}

Return deduplicated developments. Only use URLs from the list above."""


async def synthesize_company_developments(
    articles: list[dict],
    company_name: str,
    company_description: str | None,
    company_industry: str | None,
    fund_description: str | None,
) -> list[Development]:
    """Synthesize all articles for a company into deduplicated developments.

    Each article dict should have: url, title, summary, highlights.
    Returns list of validated Development objects.
    """
    if not articles:
        return []

    valid_urls = {a["url"] for a in articles}

    prompt = _build_synthesis_prompt(
        articles=articles,
        company_name=company_name,
        company_description=company_description,
        company_industry=company_industry,
        fund_description=fund_description,
    )

    try:
        response = client.messages.parse(
            model=settings.claude_model,
            max_tokens=2000,
            system=SYNTHESIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            output_format=SynthesisResponse,
        )

        parsed = response.parsed_output
        if not parsed:
            logger.error("No parsed output in synthesis response for %s", company_name)
            return []

        developments = []
        for dev in parsed.developments:
            # Filter hallucinated URLs
            dev.source_urls = [u for u in dev.source_urls if u in valid_urls]
            if not dev.source_urls:
                logger.warning("Dropping development with no valid source URLs: %s", dev.headline)
                continue
            developments.append(dev)

        return developments

    except Exception:
        logger.exception("Failed to synthesize developments for %s", company_name)
        return []


OVERVIEW_SYSTEM_PROMPT = """\
You are a PE (Private Equity) analyst specializing in portfolio company intelligence.
Always be concise and direct."""


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

    company_summary = "\n".join(summary_parts)

    prompt = f"""\
You are writing the executive overview for a PE fund's weekly portfolio intelligence digest.

FUND CONTEXT: {fund_description or 'Growth equity fund'}

KEY DEVELOPMENTS THIS WEEK:
{company_summary}

Write 3-4 sentences highlighting the most important themes across the portfolio.
Focus on: cross-portfolio patterns, competitive dynamics, sector-level shifts, and
actionable signals for the investment team.

Be direct and specific — no preamble or sign-off."""

    response = client.messages.create(
        model=settings.claude_model,
        max_tokens=400,
        system=OVERVIEW_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


async def generate_industry_pulse(
    industry_name: str,
    company_names: list[str],
    developments: list[dict],
) -> str:
    """Generate a brief industry pulse for a sector cluster."""
    insights = "\n".join(
        f"- [{d.get('category', 'industry')}] {d.get('pe_insight', '')}"
        for d in developments[:10]
    )

    if not insights:
        return f"No significant developments in {industry_name.replace('_', ' ')} this period."

    prompt = f"""\
Write a 2-sentence industry pulse for the "{industry_name.replace('_', ' ')}" sector.

Portfolio companies in this sector: {', '.join(company_names)}

Key developments:
{insights}

Be specific about market dynamics. No preamble."""

    response = client.messages.create(
        model=settings.claude_model,
        max_tokens=200,
        system=OVERVIEW_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()
