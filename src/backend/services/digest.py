import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from backend.config import settings
from backend.services.analysis import generate_executive_overview, generate_industry_pulse

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "templates"
_jinja_env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)), autoescape=True)


async def compile_digest(
    subscriber_email: str,
    subscriber_id: str,
    fund_description: str | None,
    companies_by_industry: dict[str, list[dict]],
    developments_by_company: dict[str, list[dict]],
    industry_articles: dict[str, list[dict]],
    period_start: str,
    period_end: str,
) -> tuple[str, str]:
    """Compile the full digest HTML.

    Args:
        companies_by_industry: {industry_name: [{name, id, ...}]}
        developments_by_company: {company_name: [{development data}]}
        industry_articles: {industry_name: [{title, summary}]}
        period_start/end: formatted date strings

    Returns:
        (subject, html_content)
    """
    # Generate executive overview
    executive_overview = await generate_executive_overview(developments_by_company, fund_description)

    # Generate industry pulses and organize data for template
    industry_sections = []
    total_articles = 0

    for industry_name, companies in companies_by_industry.items():
        company_sections = []

        for company in companies:
            company_name = company["name"]
            company_developments = developments_by_company.get(company_name, [])

            if company_developments:
                # Count unique source URLs for this company
                company_source_urls: set[str] = set()
                for d in company_developments:
                    company_source_urls.update(d["source_urls"])
                total_articles += len(company_source_urls)

                company_sections.append({
                    "name": company_name,
                    "developments": company_developments,
                })

        # Generate industry pulse from broad industry articles (not company developments)
        industry_pulse = await generate_industry_pulse(
            industry_name, industry_articles.get(industry_name, [])
        )

        if company_sections:
            industry_sections.append({
                "name": industry_name.replace("_", " ").title(),
                "pulse": industry_pulse,
                "companies": company_sections,
            })

    subject = f"Portfolio Intelligence — Week of {period_end}"

    unsubscribe_url = f"{settings.app_base_url}/api/unsubscribe/{subscriber_id}"

    template = _jinja_env.get_template("digest.html")
    html = template.render(
        executive_overview=executive_overview,
        industry_sections=industry_sections,
        total_articles=total_articles,
        period_start=period_start,
        period_end=period_end,
        unsubscribe_url=unsubscribe_url,
    )

    return subject, html
