"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AppHeader } from "@/components/app-header";
import { CompanyCard } from "@/components/company-card";
import { AddCompanyDialog } from "@/components/add-company-dialog";
import { DigestList } from "@/components/digest-list";
import { SubscriptionSettings } from "@/components/subscription-settings";
import { useSubscription, useUpdateSubscription } from "@/lib/hooks";
import {
  getSubscriptionId,
  clearSubscriptionId,
} from "@/lib/subscription";
import { ApiError } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [subId, setSubId] = useState<string | null>(null);

  useEffect(() => {
    const id = getSubscriptionId();
    if (!id) {
      router.replace("/");
    } else {
      setSubId(id);
    }
  }, [router]);

  const { data: subscription, error, isLoading } = useSubscription(subId);
  const updateMutation = useUpdateSubscription(subId ?? "");

  useEffect(() => {
    if (error instanceof ApiError && error.status === 404) {
      clearSubscriptionId();
      router.replace("/");
    }
  }, [error, router]);

  async function handleRemoveCompany(companyId: string) {
    try {
      await updateMutation.mutateAsync({ remove_company_ids: [companyId] });
      toast.success("Company removed");
    } catch {
      toast.error("Failed to remove company");
    }
  }

  if (!subId || isLoading) {
    return (
      <>
        <AppHeader />
        <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-10">
          <p className="text-muted-foreground">Loading...</p>
        </main>
      </>
    );
  }

  if (!subscription) return null;

  return (
    <>
      <AppHeader />
      <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-6">
        <Tabs defaultValue="portfolio">
          <TabsList className="mb-6">
            <TabsTrigger value="portfolio">Portfolio</TabsTrigger>
            <TabsTrigger value="digests">Digests</TabsTrigger>
            <TabsTrigger value="settings">Settings</TabsTrigger>
          </TabsList>

          <TabsContent value="portfolio">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">
                  Your Companies ({subscription.companies.length})
                </h2>
                <AddCompanyDialog subscriptionId={subscription.id} companyCount={subscription.companies.length} />
              </div>
              {subscription.companies.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No companies yet. Add your first portfolio company above.
                </p>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2">
                  {subscription.companies.map((company) => (
                    <CompanyCard
                      key={company.id}
                      company={company}
                      onRemove={handleRemoveCompany}
                      removing={updateMutation.isPending}
                    />
                  ))}
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="digests">
            <DigestList subscriptionId={subscription.id} />
          </TabsContent>

          <TabsContent value="settings">
            <SubscriptionSettings subscription={subscription} />
          </TabsContent>
        </Tabs>
      </main>
    </>
  );
}
