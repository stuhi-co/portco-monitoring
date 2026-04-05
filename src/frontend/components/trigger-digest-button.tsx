"use client";

import { Loader2, Zap } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { useTriggerDigest } from "@/lib/hooks";

interface TriggerDigestButtonProps {
  subscriptionId: string;
}

export function TriggerDigestButton({
  subscriptionId,
}: TriggerDigestButtonProps) {
  const mutation = useTriggerDigest(subscriptionId);

  async function handleTrigger() {
    try {
      await mutation.mutateAsync();
      toast.success(
        "Digest generation started! It will appear here once ready."
      );
    } catch {
      toast.error("Failed to trigger digest generation");
    }
  }

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={handleTrigger}
      disabled={mutation.isPending}
    >
      {mutation.isPending ? (
        <Loader2 className="mr-1 h-4 w-4 animate-spin" />
      ) : (
        <Zap className="mr-1 h-4 w-4" />
      )}
      Generate Digest
    </Button>
  );
}
