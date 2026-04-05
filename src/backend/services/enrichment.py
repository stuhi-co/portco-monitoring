import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import Company, IndustryRecord
from backend.schemas import Industry
from backend.services.search import exa

logger = logging.getLogger(__name__)

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
    """Enrich a company using the Exa Research API with outputSchema."""
    instructions = (
        f"Research the company '{company.name}'. Provide a concise profile including: "
        f"what they do, their market position, main competitors, and key topics to monitor."
    )

    try:
        research = await exa.research.create(
            instructions=instructions,
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
