// ── Industry labels ─────────────────────────────────────────────────────────

const INDUSTRY_LABELS: Record<string, string> = {
  ai_ml: "AI/ML",
  biotech: "Biotech",
  cleantech: "CleanTech",
  cloud_infrastructure: "Cloud Infrastructure",
  communications: "Communications",
  construction_tech: "Construction Tech",
  crypto_web3: "Crypto/Web3",
  cybersecurity: "Cybersecurity",
  data_analytics: "Data Analytics",
  devops: "DevOps",
  ecommerce: "E-Commerce",
  edtech: "EdTech",
  enterprise_software: "Enterprise Software",
  fintech: "FinTech",
  food_and_delivery: "Food & Delivery",
  gaming: "Gaming",
  govtech_defense: "GovTech/Defense",
  healthtech: "HealthTech",
  hr_tech: "HR Tech",
  insurtech: "InsurTech",
  legal_tech: "Legal Tech",
  martech: "MarTech",
  media_entertainment: "Media & Entertainment",
  mobility_transport: "Mobility & Transport",
  proptech: "PropTech",
  social_and_creator: "Social & Creator",
  supply_chain: "Supply Chain",
  travel_hospitality: "Travel & Hospitality",
  other: "Other",
};

export function getIndustryLabel(value: string): string {
  return INDUSTRY_LABELS[value] ?? value.replace(/_/g, " ");
}

// ── Limits ──────────────────────────────────────────────────────────────────

export const MAX_COMPANIES = 10;

export const DIGEST_COOLDOWN_HOURS = 24;
