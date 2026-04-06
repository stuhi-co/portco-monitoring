"use client";

import { useState, useEffect } from "react";
import { Loader2, Zap } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { useTriggerDigest } from "@/lib/hooks";
import { ApiError, type DigestSummary } from "@/lib/api";
import { DIGEST_COOLDOWN_HOURS } from "@/lib/config";

interface TriggerDigestButtonProps {
  subscriptionId: string;
  digests?: DigestSummary[];
}

function getCooldownRemaining(digests?: DigestSummary[]): number {
  if (!digests || digests.length === 0) return 0;
  const latest = digests[0]; // sorted desc by created_at
  const createdAt = new Date(latest.created_at).getTime();
  const cooldownMs = DIGEST_COOLDOWN_HOURS * 60 * 60 * 1000;
  const remaining = createdAt + cooldownMs - Date.now();
  return remaining > 0 ? remaining : 0;
}

function formatRemaining(ms: number): string {
  const totalMinutes = Math.ceil(ms / 60_000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

export function TriggerDigestButton({
  subscriptionId,
  digests,
}: TriggerDigestButtonProps) {
  const mutation = useTriggerDigest(subscriptionId);
  const [cooldownMs, setCooldownMs] = useState(() =>
    getCooldownRemaining(digests)
  );

  useEffect(() => {
    setCooldownMs(getCooldownRemaining(digests));
  }, [digests]);

  useEffect(() => {
    if (cooldownMs <= 0) return;
    const timer = setInterval(() => {
      setCooldownMs((prev) => {
        const next = prev - 60_000;
        return next > 0 ? next : 0;
      });
    }, 60_000);
    return () => clearInterval(timer);
  }, [cooldownMs > 0]);

  const onCooldown = cooldownMs > 0;

  async function handleTrigger() {
    try {
      await mutation.mutateAsync();
      toast.success(
        "Digest generation started! It will appear here once ready."
      );
      // Start local cooldown immediately
      setCooldownMs(DIGEST_COOLDOWN_HOURS * 60 * 60 * 1000);
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        toast.error(err.detail);
      } else {
        toast.error("Failed to trigger digest generation");
      }
    }
  }

  return (
    <div className="flex items-center gap-2">
      <Button
        variant="outline"
        size="sm"
        onClick={handleTrigger}
        disabled={mutation.isPending || onCooldown}
      >
        {mutation.isPending ? (
          <Loader2 className="mr-1 h-4 w-4 animate-spin" />
        ) : (
          <Zap className="mr-1 h-4 w-4" />
        )}
        Generate Digest
      </Button>
      {onCooldown && (
        <span className="text-xs text-muted-foreground">
          Available in {formatRemaining(cooldownMs)}
        </span>
      )}
    </div>
  );
}
