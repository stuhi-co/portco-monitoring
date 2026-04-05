import json
import logging

import anthropic

from backend.config import settings

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

ANALYSIS_SYSTEM_PROMPT = """\
You are a PE (Private Equity) analyst specializing in portfolio company intelligence.
You analyze news articles and provide structured assessments focused on what matters
to PE investors: valuation signals, competitive dynamics, growth indicators, risk factors,
and strategic opportunities.

Always be concise and direct. Your "So What" PE insight should be one actionable sentence
that a PE partner would find valuable."""


def _build_article_analysis_prompt(
    article_title: str,
    article_summary: str,
    article_highlights: list[str],
    company_name: str,
    company_description: str | None,
    company_industry: str | None,
    fund_description: str | None,
) -> str:
    highlights_text = "\n".join(f"- {h}" for h in article_highlights) if article_highlights else "N/A"
    return f"""\
Analyze this article for PE relevance to the portfolio company.

COMPANY: {company_name}
COMPANY DESCRIPTION: {company_description or 'N/A'}
INDUSTRY: {company_industry or 'N/A'}
FUND CONTEXT: {fund_description or 'N/A'}

ARTICLE TITLE: {article_title}
ARTICLE SUMMARY: {article_summary or 'N/A'}
KEY EXCERPTS:
{highlights_text}

Return a JSON object with exactly these fields:
{{
  "relevance_score": <float 0-10, where 10 = directly impacts company valuation/strategy>,
  "category": <one of: "m_and_a", "funding", "leadership", "product", "regulatory", "competitor", "new_entrant", "industry">,
  "pe_insight": <one sentence "So What" for a PE investor — what action or implication does this have?>,
  "is_competitor_alert": <boolean — true if this is about a competitor or new market entrant>
}}

Return ONLY valid JSON, no markdown fences or extra text."""


async def analyze_articles(
    articles: list[dict],
    company_name: str,
    company_description: str | None,
    company_industry: str | None,
    fund_description: str | None,
) -> list[dict]:
    """Analyze a batch of articles for PE relevance using Claude.

    Each article dict should have: title, summary, highlights, url.
    Returns list of analysis dicts with: relevance_score, category, pe_insight, is_competitor_alert.
    """
    results = []

    for i in range(0, len(articles), settings.analysis_batch_size):
        batch = articles[i : i + settings.analysis_batch_size]
        # Process batch articles concurrently-ish by batching in a single prompt
        for article in batch:
            prompt = _build_article_analysis_prompt(
                article_title=article.get("title", ""),
                article_summary=article.get("summary", ""),
                article_highlights=article.get("highlights", []),
                company_name=company_name,
                company_description=company_description,
                company_industry=company_industry,
                fund_description=fund_description,
            )

            try:
                response = client.messages.create(
                    model=settings.claude_model,
                    max_tokens=300,
                    system=ANALYSIS_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                )

                text = response.content[0].text.strip()
                # Handle potential markdown fences
                if text.startswith("```"):
                    text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

                analysis = json.loads(text)

                # Validate and normalize
                analysis["relevance_score"] = float(analysis.get("relevance_score", 0))
                analysis["category"] = str(analysis.get("category", "industry"))
                analysis["pe_insight"] = str(analysis.get("pe_insight", ""))
                analysis["is_competitor_alert"] = bool(analysis.get("is_competitor_alert", False))
                analysis["url"] = article["url"]

                results.append(analysis)

            except (json.JSONDecodeError, KeyError, IndexError):
                logger.exception("Failed to parse Claude analysis for %s", article.get("url"))
                results.append({
                    "url": article["url"],
                    "relevance_score": 0.0,
                    "category": "industry",
                    "pe_insight": "Analysis unavailable.",
                    "is_competitor_alert": False,
                })

    return results


async def generate_executive_overview(
    analyses_by_company: dict[str, list[dict]],
    fund_description: str | None,
) -> str:
    """Generate the executive overview for the top of the digest."""
    # Build a summary of all high-scoring articles
    summary_parts = []
    for company_name, analyses in analyses_by_company.items():
        relevant = [a for a in analyses if a.get("relevance_score", 0) >= settings.relevance_threshold]
        if relevant:
            insights = "; ".join(a["pe_insight"] for a in relevant[:3])
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
        system=ANALYSIS_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


async def generate_industry_pulse(
    industry_name: str,
    company_names: list[str],
    analyses: list[dict],
) -> str:
    """Generate a brief industry pulse for a sector cluster."""
    insights = "\n".join(
        f"- [{a.get('category', 'industry')}] {a.get('pe_insight', '')}"
        for a in analyses[:10]
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
        system=ANALYSIS_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()
