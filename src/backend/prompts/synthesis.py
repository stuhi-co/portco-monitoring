SYNTHESIS_SYSTEM_PROMPT = """\
You are a PE (Private Equity) analyst. You synthesize news articles into deduplicated \
developments for PE investors. Be concise and to the point.

CATEGORY DEFINITIONS:
- m_and_a: Mergers, acquisitions, divestitures involving the portfolio company or a named competitor.
- funding: Fundraising rounds, IPO filings, debt issuance, or credit facilities.
- leadership: C-suite hires, departures, board changes.
- product: New product launches, major feature releases, partnerships, platform expansions \
by the portfolio company.
- regulatory: Government actions, compliance changes, legal rulings affecting the company or sector.
- competitor: Any development primarily about a named competitor (funding, product, M&A, leadership). \
If the article is from a competitor search, default to this category unless it directly involves \
the portfolio company.
- new_entrant: A previously unknown player entering the market.
- industry: Broad market statistics, macro trends, or sector-wide reports not tied to a specific company.

DEDUP RULES:
- If multiple articles describe the SAME event, strategic move, or announcement, merge them into \
ONE development and list all source indices.
- An acquisition, its regulatory approval, and its strategic implications are ONE development.
- A product launch and its market reception are ONE development.

RELEVANCE SCORING GUIDE:
- 9-10: Direct news about the portfolio company (earnings, product launch, M&A, leadership change).
- 7-8: Named competitor making a significant move (funding, acquisition, product launch).
- 5-6: Tangential or loosely related news; industry report that mentions the company or sector.
- ≤4: Generic industry statistics, unrelated companies, or noise.
- RULE: Generic industry statistics or macro reports with no mention of specific companies \
must NEVER score above 5.

RULES:
- Only report facts explicitly stated in the articles. Do not speculate.
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

    # Group articles by source_type
    groups: dict[str, list[tuple[int, dict]]] = {"company": [], "competitor": [], "industry": []}
    for i, a in enumerate(articles, 1):
        st = a.get("source_type", "company")
        groups.setdefault(st, []).append((i, a))

    def _format_article(idx: int, article: dict) -> str:
        highlights = article.get("highlights", [])[:max_highlights]
        highlights_text = "\n".join(f"  - {h}" for h in highlights) if highlights else "  N/A"
        st = article.get("source_type", "company")
        return (
            f"[{idx}] ({st}) Title: {article.get('title', 'N/A')}\n"
            f"    Summary: {article.get('summary', 'N/A')}\n"
            f"    Highlights:\n{highlights_text}"
        )

    sections = []

    if groups["company"]:
        lines = "\n\n".join(_format_article(i, a) for i, a in groups["company"])
        sections.append(f"ARTICLES ABOUT {company_name.upper()} (portfolio company):\n{lines}")

    if groups["competitor"]:
        lines = "\n\n".join(_format_article(i, a) for i, a in groups["competitor"])
        sections.append(f"ARTICLES ABOUT COMPETITORS:\n{lines}")

    if groups["industry"]:
        lines = "\n\n".join(_format_article(i, a) for i, a in groups["industry"])
        sections.append(f"BROAD INDUSTRY ARTICLES:\n{lines}")

    articles_text = "\n\n---\n\n".join(sections)

    return f"""\
Synthesize these articles into deduplicated developments for the portfolio company.

COMPANY: {company_name}
DESCRIPTION: {company_description or 'N/A'}
INDUSTRY: {company_industry or 'N/A'}
FUND CONTEXT: {fund_description or 'N/A'}

{articles_text}

Merge overlapping articles about the same event/theme into a SINGLE development.
Use article [N] indices for source_indices."""
