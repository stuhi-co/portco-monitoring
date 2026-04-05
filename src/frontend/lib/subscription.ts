const STORAGE_KEY = "stuhi_subscription_id";

export function getSubscriptionId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(STORAGE_KEY);
}

export function setSubscriptionId(id: string): void {
  localStorage.setItem(STORAGE_KEY, id);
}

export function clearSubscriptionId(): void {
  localStorage.removeItem(STORAGE_KEY);
}
