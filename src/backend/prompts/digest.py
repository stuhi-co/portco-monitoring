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
    company_names: list[str],
    insights: str,
) -> str:
    return f"""\
Write a 1-2 sentence industry pulse for the "{industry_name.replace('_', ' ')}" sector.

Portfolio companies: {', '.join(company_names)}

Key developments:
{insights}

Be specific about market dynamics."""
