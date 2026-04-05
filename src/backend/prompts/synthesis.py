SYNTHESIS_SYSTEM_PROMPT = """\
You are a PE (Private Equity) analyst. You synthesize news articles into deduplicated \
developments for PE investors. Be concise and to the point.

Rules:
- Only report facts explicitly stated in the articles. Do not speculate.
- If multiple articles cover the same event, merge into one development and list all source indices.
- Reference articles by their [N] index only.
- Each pe_insight must be one actionable sentence.
- Each summary must be 1-2 sentences max."""


def build_synthesis_prompt(
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
            f"[{i}] Title: {a.get('title', 'N/A')}\n"
            f"    Summary: {a.get('summary', 'N/A')}\n"
            f"    Highlights:\n{highlights_text}"
        )

    articles_text = "\n\n".join(article_blocks)

    return f"""\
Synthesize these articles into deduplicated developments for the portfolio company.

COMPANY: {company_name}
DESCRIPTION: {company_description or 'N/A'}
INDUSTRY: {company_industry or 'N/A'}
FUND CONTEXT: {fund_description or 'N/A'}

ARTICLES:
{articles_text}

Return deduplicated developments. Use article [N] indices for source_indices."""
