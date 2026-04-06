"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { FileText, Loader2 } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useDigests } from "@/lib/hooks";
import { TriggerDigestButton } from "./trigger-digest-button";

interface DigestListProps {
  subscriptionId: string;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function DigestList({ subscriptionId }: DigestListProps) {
  const [isGenerating, setIsGenerating] = useState(false);
  const digestCountAtTrigger = useRef<number | null>(null);
  const { data: digests, isLoading } = useDigests(subscriptionId, {
    refetchInterval: isGenerating ? 5_000 : false,
  });

  useEffect(() => {
    if (
      isGenerating &&
      digests &&
      digestCountAtTrigger.current !== null &&
      digests.length > digestCountAtTrigger.current
    ) {
      setIsGenerating(false);
      digestCountAtTrigger.current = null;
    }
  }, [digests, isGenerating]);

  function handleTriggerSuccess() {
    digestCountAtTrigger.current = digests?.length ?? 0;
    setIsGenerating(true);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Past Digests</h2>
        <TriggerDigestButton
          subscriptionId={subscriptionId}
          digests={digests}
          onTriggerSuccess={handleTriggerSuccess}
        />
      </div>

      {isLoading && (
        <p className="text-sm text-muted-foreground">Loading digests...</p>
      )}

      {digests && digests.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            <FileText className="mx-auto mb-2 h-8 w-8" />
            <p>No digests yet. Generate your first one!</p>
          </CardContent>
        </Card>
      )}

      {isGenerating && (
        <Card className="border-dashed">
          <CardContent className="flex items-center gap-3 py-4">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Generating your digest... This may take a minute.
            </p>
          </CardContent>
        </Card>
      )}

      {digests?.map((digest) => (
        <Link key={digest.id} href={`/digests/${digest.id}`}>
          <Card className="transition-colors hover:border-primary/40">
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between">
                <CardTitle className="text-base">
                  {digest.subject || "Untitled Digest"}
                </CardTitle>
                {digest.article_count != null && (
                  <Badge variant="secondary" className="text-xs">
                    {digest.article_count} articles
                  </Badge>
                )}
              </div>
              <CardDescription>
                {digest.period_start && digest.period_end
                  ? `${formatDate(digest.period_start)} - ${formatDate(digest.period_end)}`
                  : formatDate(digest.created_at)}
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
      ))}
    </div>
  );
}
