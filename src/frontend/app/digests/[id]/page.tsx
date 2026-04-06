"use client";

import { use } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AppHeader } from "@/components/app-header";
import { useDigestHtml } from "@/lib/hooks";

export default function DigestViewerPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: html, isLoading, error } = useDigestHtml(id);

  return (
    <>
      <AppHeader />
      <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-6">
        <div className="mb-4">
          <Link href="/dashboard">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-1 h-4 w-4" />
              Back to Dashboard
            </Button>
          </Link>
        </div>

        {isLoading && (
          <p className="text-muted-foreground">Loading digest...</p>
        )}

        {error && (
          <p className="text-destructive">Failed to load digest.</p>
        )}

        {html && (
          <iframe
            srcDoc={html.replace(
              "<head>",
              '<head><base target="_blank">'
            )}
            sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"
            className="w-full rounded-lg border border-border bg-white"
            style={{ minHeight: "80vh" }}
            title="Digest content"
          />
        )}
      </main>
    </>
  );
}
