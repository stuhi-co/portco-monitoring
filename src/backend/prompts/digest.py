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
Summarize the key developments below in a brief executive overview.

{'FUND CONTEXT: ' + fund_description if fund_description else ''}

KEY DEVELOPMENTS:
{company_summary}

Be straight to the point — just state what happened and why it matters. \
No fluff, no filler phrases, no generic commentary. \
Keep it short but cover every important development. \
Do NOT use markdown formatting. Output plain text only."""
