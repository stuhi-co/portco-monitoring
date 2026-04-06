from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ── StrEnums ──────────────────────────────────────────────────────────────────


class SourceType(StrEnum):
    company = "company"
    competitor = "competitor"
    industry = "industry"


class Industry(StrEnum):
    ai_ml = "ai_ml"
    biotech = "biotech"
    cleantech = "cleantech"
    cloud_infrastructure = "cloud_infrastructure"
    communications = "communications"
    construction_tech = "construction_tech"
    crypto_web3 = "crypto_web3"
    cybersecurity = "cybersecurity"
    data_analytics = "data_analytics"
    devops = "devops"
    ecommerce = "ecommerce"
    edtech = "edtech"
    enterprise_software = "enterprise_software"
    fintech = "fintech"
    food_and_delivery = "food_and_delivery"
    gaming = "gaming"
    govtech_defense = "govtech_defense"
    healthtech = "healthtech"
    hr_tech = "hr_tech"
    insurtech = "insurtech"
    legal_tech = "legal_tech"
    martech = "martech"
    media_entertainment = "media_entertainment"
    mobility_transport = "mobility_transport"
    proptech = "proptech"
    social_and_creator = "social_and_creator"
    supply_chain = "supply_chain"
    travel_hospitality = "travel_hospitality"
    other = "other"


class ArticleCategory(StrEnum):
    m_and_a = "m_and_a"
    funding = "funding"
    leadership = "leadership"
    product = "product"
    regulatory = "regulatory"
    competitor = "competitor"
    new_entrant = "new_entrant"
    industry = "industry"


class Frequency(StrEnum):
    daily = "daily"
    weekly = "weekly"


# ── Request schemas ───────────────────────────────────────────────────────────


class CompanyInput(BaseModel):
    name: str
    industry: Industry | None = None


class GenerateFundDescriptionRequest(BaseModel):
    email: EmailStr


class SubscribeRequest(BaseModel):
    email: EmailStr
    companies: list[CompanyInput] = Field(min_length=1, max_length=10)
    frequency: Frequency = Frequency.weekly
    fund_description: str | None = None


class SubscriptionUpdate(BaseModel):
    frequency: Frequency | None = None
    fund_description: str | None = None
    add_companies: list[CompanyInput] | None = None
    remove_company_ids: list[UUID] | None = None


# ── Response schemas ──────────────────────────────────────────────────────────


class CompanyResponse(BaseModel):
    id: UUID
    name: str
    industry: Industry | None
    description: str | None
    competitors: list[str] | None
    key_topics: list[str] | None
    enriched_at: datetime | None

    model_config = {"from_attributes": True}


class SubscriptionResponse(BaseModel):
    id: UUID
    email: str
    frequency: Frequency
    fund_description: str | None
    is_active: bool
    companies: list[CompanyResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


class DigestSummary(BaseModel):
    id: UUID
    subject: str | None
    article_count: int | None
    period_start: datetime | None
    period_end: datetime | None
    sent_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class GenerateFundDescriptionResponse(BaseModel):
    fund_description: str


class Development(BaseModel):
    headline: str
    summary: str
    category: ArticleCategory
    relevance_score: float = Field(ge=0, le=10)
    pe_insight: str
    source_urls: list[str] = Field(min_length=1)
