DIGEST_SYSTEM_PROMPT = """\
You are a PE (Private Equity) analyst. Be concise and to the point. \
No preamble, no sign-off. \
Output plain text only — never use markdown formatting (no **, no *, no #, no bullet points). \
Content renders in HTML email."""


def build_executive_overview_prompt(
    company_summary: str,
    fund_description: str | None,
) -> str:
    return f"""\
Write the executive overview for a PE fund's weekly portfolio intelligence digest.

FUND CONTEXT: {fund_description or 'Growth equity fund'}

KEY DEVELOPMENTS:
{company_summary}

Write EXACTLY 2-3 plain-text sentences on the most important cross-portfolio themes: \
competitive dynamics, sector shifts, and actionable signals for the investment team. \
Do NOT use markdown formatting. Output plain text only."""
