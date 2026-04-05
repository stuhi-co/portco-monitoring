"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Plus, Trash2, Loader2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useIndustries, useSubscribeMutation, useLookupByEmail, useGenerateFundDescription } from "@/lib/hooks";
import { setSubscriptionId } from "@/lib/subscription";
import { ApiError, type Frequency, type Industry } from "@/lib/api";

interface CompanyRow {
  name: string;
  industry: string;
}

export function SubscribeForm() {
  const router = useRouter();
  const { data: industries } = useIndustries();
  const subscribeMutation = useSubscribeMutation();
  const lookupMutation = useLookupByEmail();
  const generateMutation = useGenerateFundDescription();

  const [email, setEmail] = useState("");
  const [companies, setCompanies] = useState<CompanyRow[]>([
    { name: "", industry: "" },
  ]);
  const [frequency, setFrequency] = useState<Frequency>("weekly");
  const [fundDescription, setFundDescription] = useState("");
  const [lookupEmail, setLookupEmail] = useState("");

  function addCompanyRow() {
    setCompanies((prev) => [...prev, { name: "", industry: "" }]);
  }

  function removeCompanyRow(index: number) {
    setCompanies((prev) => prev.filter((_, i) => i !== index));
  }

  function updateCompany(index: number, field: keyof CompanyRow, value: string) {
    setCompanies((prev) =>
      prev.map((c, i) => (i === index ? { ...c, [field]: value } : c))
    );
  }

  async function handleSubscribe(e: React.FormEvent) {
    e.preventDefault();
    const validCompanies = companies.filter((c) => c.name.trim());
    if (!email.trim() || validCompanies.length === 0) {
      toast.error("Please enter your email and at least one company.");
      return;
    }

    try {
      const result = await subscribeMutation.mutateAsync({
        email: email.trim(),
        companies: validCompanies.map((c) => ({
          name: c.name.trim(),
          industry: (c.industry as Industry) || undefined,
        })),
        frequency,
        fund_description: fundDescription.trim() || undefined,
      });
      setSubscriptionId(result.id);
      toast.success("Subscribed successfully!");
      router.push("/dashboard");
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        // Email already exists — auto-lookup
        try {
          const existing = await lookupMutation.mutateAsync(email.trim());
          setSubscriptionId(existing.id);
          toast.info("Welcome back! Found your existing subscription.");
          router.push("/dashboard");
        } catch {
          toast.error("Email already subscribed but lookup failed. Try recovering below.");
        }
      } else {
        toast.error(err instanceof Error ? err.message : "Subscription failed");
      }
    }
  }

  async function handleLookup(e: React.FormEvent) {
    e.preventDefault();
    if (!lookupEmail.trim()) return;
    try {
      const result = await lookupMutation.mutateAsync(lookupEmail.trim());
      setSubscriptionId(result.id);
      toast.success("Welcome back!");
      router.push("/dashboard");
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        toast.error("No subscription found for this email.");
      } else {
        toast.error("Lookup failed. Please try again.");
      }
    }
  }

  const isLoading = subscribeMutation.isPending || lookupMutation.isPending;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Start Monitoring</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubscribe} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@fund.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="space-y-3">
              <Label>Portfolio Companies</Label>
              {companies.map((company, i) => (
                <div key={i} className="flex items-center gap-2">
                  <Input
                    placeholder="Company name"
                    value={company.name}
                    onChange={(e) => updateCompany(i, "name", e.target.value)}
                    className="flex-1"
                  />
                  <Select
                    value={company.industry}
                    onValueChange={(v) => updateCompany(i, "industry", v ?? "")}
                  >
                    <SelectTrigger className="w-[180px]">
                      <SelectValue placeholder="Industry" />
                    </SelectTrigger>
                    <SelectContent>
                      {industries?.map((ind) => (
                        <SelectItem key={ind.value} value={ind.value}>
                          {ind.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {companies.length > 1 && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => removeCompanyRow(i)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              ))}
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addCompanyRow}
              >
                <Plus className="mr-1 h-4 w-4" />
                Add Company
              </Button>
            </div>

            <div className="space-y-2">
              <Label htmlFor="frequency">Digest Frequency</Label>
              <Select
                value={frequency}
                onValueChange={(v) => v && setFrequency(v as Frequency)}
              >
                <SelectTrigger id="frequency">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="daily">Daily</SelectItem>
                  <SelectItem value="weekly">Weekly</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="fund-desc">Fund Description (optional)</Label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={!email.trim() || !email.includes("@") || generateMutation.isPending}
                  onClick={async () => {
                    try {
                      const result = await generateMutation.mutateAsync(email.trim());
                      setFundDescription(result.fund_description);
                      toast.success("Fund description generated");
                    } catch (err) {
                      if (err instanceof ApiError && err.status === 422) {
                        toast.error("Please use a company email to auto-generate");
                      } else {
                        toast.error("Generation failed, please describe your fund manually");
                      }
                    }
                  }}
                >
                  {generateMutation.isPending ? (
                    <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                  ) : (
                    <Sparkles className="mr-1 h-4 w-4" />
                  )}
                  Generate
                </Button>
              </div>
              <Textarea
                id="fund-desc"
                placeholder="Describe your fund's focus to get more relevant insights..."
                value={fundDescription}
                onChange={(e) => setFundDescription(e.target.value)}
                rows={3}
                disabled={generateMutation.isPending}
              />
            </div>

            <Button type="submit" className="w-full" disabled={isLoading}>
              {subscribeMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Subscribe
            </Button>
          </form>
        </CardContent>
      </Card>

      <Separator />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Already subscribed?</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleLookup} className="flex gap-2">
            <Input
              type="email"
              placeholder="your@email.com"
              value={lookupEmail}
              onChange={(e) => setLookupEmail(e.target.value)}
              className="flex-1"
            />
            <Button type="submit" variant="secondary" disabled={isLoading}>
              {lookupMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Recover
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
