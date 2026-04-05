DIGEST_SYSTEM_PROMPT = """\
You are a PE (Private Equity) analyst. Be concise and to the point. \
No preamble, no sign-off."""


def build_executive_overview_prompt(
    company_summary: str,
    fund_description: str | None,
) -> str:
    return f"""\
Write the executive overview for a PE fund's weekly portfolio intelligence digest.

FUND CONTEXT: {fund_description or 'Growth equity fund'}

KEY DEVELOPMENTS:
{company_summary}

Write 2-3 concise sentences on the most important cross-portfolio themes: \
competitive dynamics, sector shifts, and actionable signals for the investment team."""


def build_industry_pulse_prompt(
    industry_name: str,
    articles: list[dict],
) -> str:
    article_lines = "\n".join(
        f"- {a.get('title', 'N/A')}: {a.get('summary', 'N/A')}"
        for a in articles[:10]
    )

    return f"""\
Write a 1-2 sentence industry pulse for the "{industry_name.replace('_', ' ')}" sector.

Focus on broad market dynamics, regulatory shifts, and macro trends — \
NOT on individual company news.

Recent industry coverage:
{article_lines}"""
