"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getSubscriptionId } from "@/lib/subscription";
import { AppHeader } from "@/components/app-header";
import { SubscribeForm } from "@/components/subscribe-form";

export default function HomePage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const id = getSubscriptionId();
    if (id) {
      router.replace("/dashboard");
    } else {
      setReady(true);
    }
  }, [router]);

  if (!ready) return null;

  return (
    <>
      <AppHeader />
      <main className="mx-auto w-full max-w-xl flex-1 px-4 py-10">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold tracking-tight">
            Portfolio Intelligence
          </h1>
          <p className="mt-2 text-muted-foreground">
            AI-powered news monitoring for your portfolio companies.
            Get actionable insights delivered to your inbox.
          </p>
        </div>
        <SubscribeForm />
      </main>
    </>
  );
}
