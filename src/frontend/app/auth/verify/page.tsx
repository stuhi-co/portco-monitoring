"use client";

import { Suspense, useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { AppHeader } from "@/components/app-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useVerifyMagicLink } from "@/lib/hooks";
import { setSubscriptionId } from "@/lib/subscription";
import Link from "next/link";

function VerifyContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const verifyMutation = useVerifyMagicLink();
  const attempted = useRef(false);

  useEffect(() => {
    if (!token || attempted.current) return;
    attempted.current = true;

    verifyMutation.mutateAsync(token).then((result) => {
      setSubscriptionId(result.subscriber_id);
      toast.success("Signed in successfully!");
      router.replace("/dashboard");
    }).catch(() => {
      // error state handled by mutation
    });
  }, [token]); // eslint-disable-line react-hooks/exhaustive-deps

  if (verifyMutation.isPending) {
    return (
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-muted-foreground">Verifying your login link...</p>
      </div>
    );
  }

  if (verifyMutation.isError) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Link expired or invalid</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            This login link is no longer valid. It may have expired or already been used.
          </p>
          <Button render={<Link href="/" />} className="w-full">
            Request a new link
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!token) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Missing token</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            No login token found. Please use the link from your email.
          </p>
          <Button render={<Link href="/" />} className="w-full">
            Go to sign in
          </Button>
        </CardContent>
      </Card>
    );
  }

  return null;
}

export default function VerifyPage() {
  return (
    <>
      <AppHeader />
      <main className="mx-auto w-full max-w-md flex-1 px-4 py-20">
        <Suspense
          fallback={
            <div className="flex flex-col items-center gap-4">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="text-muted-foreground">Loading...</p>
            </div>
          }
        >
          <VerifyContent />
        </Suspense>
      </main>
    </>
  );
}
