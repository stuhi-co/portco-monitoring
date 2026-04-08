import logging
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.api.auth import create_session_for_subscriber, get_current_subscriber
from backend.database import get_session, Company, IndustryRecord, Subscriber
from backend.schemas import (
    CompanyResponse,
    DayOfWeek,
    GenerateFundDescriptionRequest,
    GenerateFundDescriptionResponse,
    Industry,
    SubscribeRequest,
    SubscriptionResponse,
    SubscriptionUpdate,
)
from backend.config import settings
from backend.services.enrichment import enrich_fund_description, extract_domain

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["subscriptions"])

INDUSTRY_LABELS: dict[str, str] = {
    "ai_ml": "AI/ML",
    "biotech": "Biotech",
    "cleantech": "CleanTech",
    "cloud_infrastructure": "Cloud Infrastructure",
    "communications": "Communications",
    "construction_tech": "Construction Tech",
    "crypto_web3": "Crypto/Web3",
    "cybersecurity": "Cybersecurity",
    "data_analytics": "Data Analytics",
    "devops": "DevOps",
    "ecommerce": "E-Commerce",
    "edtech": "EdTech",
    "enterprise_software": "Enterprise Software",
    "fintech": "FinTech",
    "food_and_delivery": "Food & Delivery",
    "gaming": "Gaming",
    "govtech_defense": "GovTech/Defense",
    "healthtech": "HealthTech",
    "hr_tech": "HR Tech",
    "insurtech": "InsurTech",
    "legal_tech": "Legal Tech",
    "martech": "MarTech",
    "media_entertainment": "Media & Entertainment",
    "mobility_transport": "Mobility & Transport",
    "proptech": "PropTech",
    "social_and_creator": "Social & Creator",
    "supply_chain": "Supply Chain",
    "travel_hospitality": "Travel & Hospitality",
    "other": "Other",
}


async def _get_or_create_industry(session: AsyncSession, name: str) -> IndustryRecord:
    result = await session.execute(select(IndustryRecord).where(IndustryRecord.name == name))
    industry = result.scalar_one_or_none()
    if industry is None:
        industry = IndustryRecord(name=name)
        session.add(industry)
        await session.flush()
    return industry


async def _enrich_companies_background(subscriber_id: UUID) -> None:
    """Background task to enrich companies via Exa Research API."""
    from backend.database import async_session_factory
    from backend.services.enrichment import enrich_company

    async with async_session_factory() as session:
        result = await session.execute(
            select(Company)
            .where(Company.subscriber_id == subscriber_id, Company.enriched_at.is_(None))
            .options(selectinload(Company.industry))
        )
        companies = result.scalars().all()

        for company in companies:
            try:
                await enrich_company(session, company)
            except Exception:
                logger.exception("Failed to enrich company %s", company.name)

        await session.commit()


@router.post(
    "/generate-fund-description",
    response_model=GenerateFundDescriptionResponse,
)
async def generate_fund_description(body: GenerateFundDescriptionRequest):
    domain = extract_domain(body.email)
    if domain is None:
        raise HTTPException(
            status_code=422,
            detail="Please use a company email to auto-generate a fund description.",
        )
    try:
        description = await enrich_fund_description(domain)
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Failed to generate fund description. Please describe your fund manually.",
        )
    if not description:
        raise HTTPException(
            status_code=502,
            detail="Failed to generate fund description. Please describe your fund manually.",
        )
    return GenerateFundDescriptionResponse(fund_description=description)


@router.post("/subscribe", response_model=SubscriptionResponse, status_code=201)
async def subscribe(
    body: SubscribeRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    # Check for existing subscriber
    result = await session.execute(select(Subscriber).where(Subscriber.email == body.email))
    existing = result.scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email already subscribed")

    timezone = "America/New_York"
    if body.timezone:
        try:
            ZoneInfo(body.timezone)
            timezone = body.timezone
        except (KeyError, ValueError):
            raise HTTPException(status_code=422, detail=f"Invalid timezone: {body.timezone}")

    subscriber = Subscriber(
        email=body.email,
        frequency=body.frequency.value,
        preferred_day=body.preferred_day.value,
        preferred_hour=body.preferred_hour,
        fund_description=body.fund_description,
        timezone=timezone,
    )
    session.add(subscriber)
    await session.flush()

    for comp in body.companies:
        industry_rec = None
        if comp.industry:
            industry_rec = await _get_or_create_industry(session, comp.industry.value)

        company = Company(
            subscriber_id=subscriber.id,
            name=comp.name,
            industry_id=industry_rec.id if industry_rec else None,
        )
        session.add(company)

    # Auto-login: create session and set cookie
    await create_session_for_subscriber(subscriber, session, response)
    await session.commit()

    # Reload with relationships
    result = await session.execute(
        select(Subscriber)
        .where(Subscriber.id == subscriber.id)
        .options(selectinload(Subscriber.companies).selectinload(Company.industry))
    )
    subscriber = result.scalar_one()

    # Enrich companies in background
    background_tasks.add_task(_enrich_companies_background, subscriber.id)

    return _subscriber_to_response(subscriber)


@router.get("/subscriptions/{subscriber_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscriber_id: UUID,
    current_subscriber: Subscriber = Depends(get_current_subscriber),
):
    if current_subscriber.id != subscriber_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return _subscriber_to_response(current_subscriber)


@router.patch("/subscriptions/{subscriber_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscriber_id: UUID,
    body: SubscriptionUpdate,
    background_tasks: BackgroundTasks,
    current_subscriber: Subscriber = Depends(get_current_subscriber),
    session: AsyncSession = Depends(get_session),
):
    if current_subscriber.id != subscriber_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    subscriber = await _load_subscriber(session, subscriber_id)

    if body.frequency is not None:
        subscriber.frequency = body.frequency.value
    if body.fund_description is not None:
        subscriber.fund_description = body.fund_description
    if body.preferred_day is not None:
        subscriber.preferred_day = body.preferred_day.value
    if body.preferred_hour is not None:
        subscriber.preferred_hour = body.preferred_hour
    if body.timezone is not None:
        try:
            ZoneInfo(body.timezone)
        except (KeyError, ValueError):
            raise HTTPException(status_code=422, detail=f"Invalid timezone: {body.timezone}")
        subscriber.timezone = body.timezone

    if body.remove_company_ids:
        for cid in body.remove_company_ids:
            result = await session.execute(
                select(Company).where(Company.id == cid, Company.subscriber_id == subscriber.id)
            )
            company = result.scalar_one_or_none()
            if company:
                await session.delete(company)

    new_companies_added = False
    if body.add_companies:
        current_count = len(subscriber.companies)
        if current_count + len(body.add_companies) > settings.max_companies_per_subscription:
            raise HTTPException(
                status_code=422,
                detail=f"Cannot exceed {settings.max_companies_per_subscription} companies per subscription",
            )
        for comp in body.add_companies:
            industry_rec = None
            if comp.industry:
                industry_rec = await _get_or_create_industry(session, comp.industry.value)
            company = Company(
                subscriber_id=subscriber.id,
                name=comp.name,
                industry_id=industry_rec.id if industry_rec else None,
            )
            session.add(company)
            new_companies_added = True

    await session.commit()

    # Reload
    subscriber = await _load_subscriber(session, subscriber_id)

    if new_companies_added:
        background_tasks.add_task(_enrich_companies_background, subscriber.id)

    return _subscriber_to_response(subscriber)


@router.delete("/subscriptions/{subscriber_id}", status_code=204)
async def delete_subscription(
    subscriber_id: UUID,
    current_subscriber: Subscriber = Depends(get_current_subscriber),
    session: AsyncSession = Depends(get_session),
):
    if current_subscriber.id != subscriber_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    subscriber = await _load_subscriber(session, subscriber_id)
    await session.delete(subscriber)
    await session.commit()


@router.get("/unsubscribe/{subscriber_id}")
async def unsubscribe(
    subscriber_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Subscriber).where(Subscriber.id == subscriber_id))
    subscriber = result.scalar_one_or_none()
    if subscriber is None:
        raise HTTPException(status_code=404, detail="Subscription not found")

    subscriber.is_active = False
    await session.commit()
    return {"message": "Successfully unsubscribed", "email": subscriber.email}


@router.get("/industries")
async def list_industries():
    return [{"value": i.value, "label": INDUSTRY_LABELS.get(i.value, i.value.replace("_", " ").title())} for i in Industry]


@router.get("/health")
async def health():
    return {"status": "ok"}


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _load_subscriber(session: AsyncSession, subscriber_id: UUID) -> Subscriber:
    result = await session.execute(
        select(Subscriber)
        .where(Subscriber.id == subscriber_id)
        .options(selectinload(Subscriber.companies).selectinload(Company.industry))
    )
    subscriber = result.scalar_one_or_none()
    if subscriber is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return subscriber


def _subscriber_to_response(subscriber: Subscriber) -> SubscriptionResponse:
    return SubscriptionResponse(
        id=subscriber.id,
        email=subscriber.email,
        frequency=subscriber.frequency,
        fund_description=subscriber.fund_description,
        preferred_day=subscriber.preferred_day,
        preferred_hour=subscriber.preferred_hour,
        timezone=subscriber.timezone,
        is_active=subscriber.is_active,
        created_at=subscriber.created_at,
        companies=[
            CompanyResponse(
                id=c.id,
                name=c.name,
                industry=c.industry.name if c.industry else None,
                description=c.description,
                competitors=c.competitors,
                key_topics=c.key_topics,
                enriched_at=c.enriched_at,
            )
            for c in subscriber.companies
        ],
    )
