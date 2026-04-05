"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "./api";

// ── Queries ─────────────────────────────────────────────────────────────────

export function useSubscription(id: string | null) {
  return useQuery({
    queryKey: ["subscription", id],
    queryFn: () => api.getSubscription(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return false;
      const enriching = data.companies.some((c) => c.enriched_at === null);
      return enriching ? 10_000 : false;
    },
  });
}

export function useDigests(subscriptionId: string | null) {
  return useQuery({
    queryKey: ["digests", subscriptionId],
    queryFn: () => api.getDigests(subscriptionId!),
    enabled: !!subscriptionId,
  });
}

export function useDigestHtml(digestId: string) {
  return useQuery({
    queryKey: ["digestHtml", digestId],
    queryFn: () => api.getDigestHtml(digestId),
  });
}

export function useIndustries() {
  return useQuery({
    queryKey: ["industries"],
    queryFn: api.getIndustries,
    staleTime: Infinity,
  });
}

// ── Mutations ───────────────────────────────────────────────────────────────

export function useSubscribeMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.subscribe,
    onSuccess: (data) => {
      qc.setQueryData(["subscription", data.id], data);
    },
  });
}

export function useUpdateSubscription(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: api.SubscriptionUpdate) =>
      api.updateSubscription(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["subscription", id] });
    },
  });
}

export function useTriggerDigest(subscriptionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.triggerDigest(subscriptionId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["digests", subscriptionId] });
    },
  });
}

export function useDeleteSubscription() {
  return useMutation({
    mutationFn: api.deleteSubscription,
  });
}

export function useLookupByEmail() {
  return useMutation({
    mutationFn: api.lookupByEmail,
  });
}
