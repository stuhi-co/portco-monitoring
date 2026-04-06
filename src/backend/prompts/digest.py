DIGEST_SYSTEM_PROMPT = """\
You are a PE (Private Equity) analyst. Be concise and to the point. \
No preamble, no sign-off. \
Return structured output only."""


def build_executive_overview_prompt(
    company_summary: str,
    fund_description: str | None,
) -> str:
    return f"""\
Distill the key developments below into up to 5 bullet points.

{'FUND CONTEXT: ' + fund_description if fund_description else ''}

KEY DEVELOPMENTS:
{company_summary}

Each bullet must be one punchy sentence: state what happened and why it matters.
No more than 2 bullets about the same company — prioritize breadth across the portfolio and most interesting developments.
Style example: "OnlyFans founder dies; valuation impact expected within 30 days."
No fluff, no filler phrases, no generic commentary."""
