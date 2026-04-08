"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Plus, Trash2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DigestSchedulePicker } from "@/components/digest-schedule-picker";
import { FundDescriptionField } from "@/components/fund-description-field";
import { useIndustries, useSubscribeMutation, useRequestMagicLink } from "@/lib/hooks";
import { setSubscriptionId } from "@/lib/subscription";
import { ApiError, type DayOfWeek, type Frequency, type Industry } from "@/lib/api";
import { MAX_COMPANIES } from "@/lib/config";

interface CompanyRow {
  name: string;
  industry: string;
}

export function SubscribeForm() {
  const router = useRouter();
  const { data: industries } = useIndustries();
  const subscribeMutation = useSubscribeMutation();
  const magicLinkMutation = useRequestMagicLink();
  const [magicLinkSent, setMagicLinkSent] = useState(false);

  const [email, setEmail] = useState("");
  const [companies, setCompanies] = useState<CompanyRow[]>([
    { name: "", industry: "" },
  ]);
  const [frequency, setFrequency] = useState<Frequency>("weekly");
  const [preferredDay, setPreferredDay] = useState<DayOfWeek>("monday");
  const [preferredHour, setPreferredHour] = useState(9);
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
        preferred_day: preferredDay,
        preferred_hour: preferredHour,
        fund_description: fundDescription.trim() || undefined,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      });
      setSubscriptionId(result.id);
      toast.success("Subscribed successfully!");
      router.push("/dashboard");
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        toast.error("Email already subscribed. Please sign in instead.");
      } else {
        toast.error(err instanceof Error ? err.message : "Subscription failed");
      }
    }
  }

  async function handleMagicLink(e: React.FormEvent) {
    e.preventDefault();
    if (!lookupEmail.trim()) return;
    try {
      await magicLinkMutation.mutateAsync(lookupEmail.trim());
      setMagicLinkSent(true);
    } catch {
      toast.error("Failed to send login link. Please try again.");
    }
  }

  const isLoading = subscribeMutation.isPending || magicLinkMutation.isPending;

  return (
    <Tabs defaultValue="signin">
      <TabsList className="mb-4 w-full">
        <TabsTrigger value="signin" className="flex-1">Sign In</TabsTrigger>
        <TabsTrigger value="signup" className="flex-1">Get Started</TabsTrigger>
      </TabsList>

      <TabsContent value="signin">
        <Card>
          <CardHeader>
            <CardTitle>Welcome Back</CardTitle>
          </CardHeader>
          <CardContent>
            {magicLinkSent ? (
              <div className="space-y-4 text-center">
                <p className="text-sm text-muted-foreground">
                  Check your email for a sign-in link. It may take a moment to arrive<br />Also check your spam folder.
                </p>
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => setMagicLinkSent(false)}
                >
                  Use a different email
                </Button>
              </div>
            ) : (
              <form onSubmit={handleMagicLink} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="lookup-email">Email</Label>
                  <Input
                    id="lookup-email"
                    type="email"
                    placeholder="you@fund.com"
                    value={lookupEmail}
                    onChange={(e) => setLookupEmail(e.target.value)}
                    required
                  />
                </div>
                <Button type="submit" className="w-full" disabled={isLoading}>
                  {magicLinkMutation.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  Send Sign-In Link
                </Button>
              </form>
            )}
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="signup">
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
                        <SelectValue placeholder="Industry (optional)" />
                      </SelectTrigger>
                      <SelectContent>
                        {industries?.map((ind) => (
                          <SelectItem key={ind.value} value={ind.value} label={ind.label}>
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
                {companies.length >= MAX_COMPANIES ? (
                  <p className="text-sm text-muted-foreground">
                    Maximum of {MAX_COMPANIES} companies reached.
                  </p>
                ) : (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={addCompanyRow}
                  >
                    <Plus className="mr-1 h-4 w-4" />
                    Add Company
                  </Button>
                )}
              </div>

              <FundDescriptionField
                email={email}
                value={fundDescription}
                onChange={setFundDescription}
                label="Fund Description (optional)"
                requireEmailValidation
              />

              <DigestSchedulePicker
                frequency={frequency}
                onFrequencyChange={setFrequency}
                preferredDay={preferredDay}
                onPreferredDayChange={setPreferredDay}
                preferredHour={preferredHour}
                onPreferredHourChange={setPreferredHour}
              />

              <Button type="submit" className="w-full" disabled={isLoading}>
                {subscribeMutation.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Subscribe
              </Button>
            </form>
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  );
}
