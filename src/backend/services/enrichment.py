import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import Company, IndustryRecord
from backend.schemas import Industry
from backend.services.search import exa

logger = logging.getLogger(__name__)

GENERIC_EMAIL_DOMAINS: frozenset[str] = frozenset({
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com",
    "yahoo.com", "yahoo.fr", "yahoo.co.uk", "protonmail.com", "proton.me",
    "icloud.com", "me.com", "mac.com", "aol.com", "zoho.com", "yandex.com",
    "mail.com", "gmx.com", "gmx.net", "fastmail.com", "tutanota.com",
    "msn.com", "hey.com",
})

def extract_domain(email: str) -> str | None:
    """Extract domain from email. Returns None for generic email providers."""
    domain = email.rsplit("@", 1)[-1].lower()
    if domain in GENERIC_EMAIL_DOMAINS:
        return None
    return domain


async def enrich_fund_description(domain: str) -> str | None:
    """Search the web for info about the org and return a generated description."""
    query = (
        f"What does the organization at {domain} do? "
        f"Investment focus, business model, target sectors, and stage preference."
    )

    try:
        result = await exa.search(
            query=query,
            type="auto",
            num_results=3,
            category="company",
            output_schema={
                "type": "object",
                "properties": {
                    "fund_description": {
                        "type": "string",
                        "description": (
                            "A 2-4 sentence description of the organization: what they do, "
                            "their investment focus or business model, target sectors, "
                            "and stage preference. Third-person perspective."
                        ),
                    },
                },
                "required": ["fund_description"],
            },
        )
    except Exception:
        logger.exception("Exa search failed for domain %s", domain)
        raise

    if not result.output or not result.output.content:
        logger.warning("No output returned for %s", domain)
        return None

    content = result.output.content
    if isinstance(content, dict):
        return content.get("fund_description")
    return content


ENRICHMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "description": {
            "type": "string",
            "description": "A 2-3 sentence description of what the company does, its market position, and business model.",
        },
        "industry": {
            "type": "string",
            "description": f"The primary industry category. Must be one of: {', '.join(i.value for i in Industry)}",
        },
        "competitors": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Top 3-5 direct competitors by name.",
        },
        "key_topics": {
            "type": "array",
            "items": {"type": "string"},
            "description": "5-8 key topics, technologies, or themes relevant to monitoring this company.",
        },
    },
    "required": ["description", "industry", "competitors", "key_topics"],
}


async def enrich_company(session: AsyncSession, company: Company) -> None:
    """Enrich a company using the Exa Research API with structured output."""
    instructions = (
        f"Research the company '{company.name}'. Provide a concise profile including: "
        f"what they do, their market position, main competitors, and key topics to monitor."
    )

    try:
        research = await exa.research.create(
            instructions=instructions,
            model="exa-research-fast",
            output_schema=ENRICHMENT_SCHEMA,
        )
        result = await exa.research.poll_until_finished(
            research.research_id,
            timeout_ms=120_000,
        )
    except Exception:
        logger.exception("Exa Research API failed for %s", company.name)
        raise

    # Extract structured output
    data = result.output.parsed if result.output and result.output.parsed else None
    if not data:
        logger.warning("No enrichment data returned for %s", company.name)
        return

    company.description = data.get("description")
    company.competitors = data.get("competitors", [])
    company.key_topics = data.get("key_topics", [])
    company.enriched_at = datetime.now(timezone.utc)

    # Set industry if not already set
    industry_name = data.get("industry", "other")
    try:
        Industry(industry_name)
    except ValueError:
        industry_name = "other"

    if company.industry_id is None:
        result_q = await session.execute(
            select(IndustryRecord).where(IndustryRecord.name == industry_name)
        )
        industry_rec = result_q.scalar_one_or_none()
        if industry_rec is None:
            industry_rec = IndustryRecord(name=industry_name)
            session.add(industry_rec)
            await session.flush()
        company.industry_id = industry_rec.id

    logger.info(
        "Enriched %s: industry=%s, competitors=%s, topics=%d",
        company.name,
        industry_name,
        company.competitors,
        len(company.key_topics or []),
    )
