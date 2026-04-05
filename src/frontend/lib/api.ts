// ── Types mirroring backend schemas.py ──────────────────────────────────────

export type Industry =
  | "ai_ml"
  | "biotech"
  | "cleantech"
  | "cloud_infrastructure"
  | "communications"
  | "construction_tech"
  | "crypto_web3"
  | "cybersecurity"
  | "data_analytics"
  | "devops"
  | "ecommerce"
  | "edtech"
  | "enterprise_software"
  | "fintech"
  | "food_and_delivery"
  | "gaming"
  | "govtech_defense"
  | "healthtech"
  | "hr_tech"
  | "insurtech"
  | "legal_tech"
  | "martech"
  | "media_entertainment"
  | "mobility_transport"
  | "proptech"
  | "social_and_creator"
  | "supply_chain"
  | "travel_hospitality"
  | "other";

export type Frequency = "daily" | "weekly";

export interface CompanyInput {
  name: string;
  industry?: Industry | null;
}

export interface SubscribeRequest {
  email: string;
  companies: CompanyInput[];
  frequency?: Frequency;
  fund_description?: string | null;
}

export interface SubscriptionUpdate {
  frequency?: Frequency | null;
  fund_description?: string | null;
  add_companies?: CompanyInput[] | null;
  remove_company_ids?: string[] | null;
}

export interface CompanyResponse {
  id: string;
  name: string;
  industry: Industry | null;
  description: string | null;
  competitors: string[] | null;
  key_topics: string[] | null;
  enriched_at: string | null;
}

export interface SubscriptionResponse {
  id: string;
  email: string;
  frequency: Frequency;
  fund_description: string | null;
  is_active: boolean;
  companies: CompanyResponse[];
  created_at: string;
}

export interface DigestSummary {
  id: string;
  subject: string | null;
  article_count: number | null;
  period_start: string | null;
  period_end: string | null;
  sent_at: string | null;
  created_at: string;
}

export interface IndustryOption {
  value: string;
  label: string;
}

// ── API Error ───────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

// ── Fetch helper ────────────────────────────────────────────────────────────

async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }
  return res.json();
}

// ── API functions ───────────────────────────────────────────────────────────

export function subscribe(body: SubscribeRequest) {
  return fetchJSON<SubscriptionResponse>("/api/subscribe", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getSubscription(id: string) {
  return fetchJSON<SubscriptionResponse>(`/api/subscriptions/${id}`);
}

export function lookupByEmail(email: string) {
  return fetchJSON<SubscriptionResponse>(
    `/api/subscriptions/lookup?email=${encodeURIComponent(email)}`
  );
}

export function updateSubscription(id: string, body: SubscriptionUpdate) {
  return fetchJSON<SubscriptionResponse>(`/api/subscriptions/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function deleteSubscription(id: string) {
  const res = await fetch(`/api/subscriptions/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }
}

export function getDigests(subscriptionId: string) {
  return fetchJSON<DigestSummary[]>(
    `/api/subscriptions/${subscriptionId}/digests`
  );
}

export async function getDigestHtml(digestId: string): Promise<string> {
  const res = await fetch(`/api/digests/${digestId}`);
  if (!res.ok) {
    throw new ApiError(res.status, "Failed to load digest");
  }
  return res.text();
}

export function triggerDigest(subscriptionId: string) {
  return fetchJSON<{ message: string; subscriber_id: string }>(
    `/api/subscriptions/${subscriptionId}/trigger`,
    { method: "POST" }
  );
}

export function getIndustries() {
  return fetchJSON<IndustryOption[]>("/api/industries");
}
