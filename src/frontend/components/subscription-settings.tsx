"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { DigestSchedulePicker } from "@/components/digest-schedule-picker";
import { FundDescriptionField } from "@/components/fund-description-field";
import { useUpdateSubscription, useDeleteSubscription } from "@/lib/hooks";
import { clearSubscriptionId } from "@/lib/subscription";
import type { DayOfWeek, Frequency, SubscriptionResponse } from "@/lib/api";

interface SubscriptionSettingsProps {
  subscription: SubscriptionResponse;
}

export function SubscriptionSettings({
  subscription,
}: SubscriptionSettingsProps) {
  const router = useRouter();
  const updateMutation = useUpdateSubscription(subscription.id);
  const deleteMutation = useDeleteSubscription();

  const [fundDescription, setFundDescription] = useState(
    subscription.fund_description ?? ""
  );
  const [frequency, setFrequency] = useState<Frequency>(
    subscription.frequency
  );
  const [preferredDay, setPreferredDay] = useState<DayOfWeek>(
    subscription.preferred_day
  );
  const [preferredHour, setPreferredHour] = useState(
    subscription.preferred_hour
  );
  const [confirmDelete, setConfirmDelete] = useState(false);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    try {
      await updateMutation.mutateAsync({
        fund_description: fundDescription.trim() || null,
        frequency,
        preferred_day: preferredDay,
        preferred_hour: preferredHour,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      });
      toast.success("Settings updated");
    } catch {
      toast.error("Failed to update settings");
    }
  }

  async function handleDelete() {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    try {
      await deleteMutation.mutateAsync(subscription.id);
      clearSubscriptionId();
      toast.success("Subscription deleted");
      router.replace("/");
    } catch {
      toast.error("Failed to delete subscription");
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Preferences</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSave} className="space-y-4">
            <div className="space-y-2">
              <Label>Email</Label>
              <p className="text-sm text-muted-foreground">
                {subscription.email}
              </p>
            </div>

            <FundDescriptionField
              email={subscription.email}
              value={fundDescription}
              onChange={setFundDescription}
            />

            <DigestSchedulePicker
              frequency={frequency}
              onFrequencyChange={setFrequency}
              preferredDay={preferredDay}
              onPreferredDayChange={setPreferredDay}
              preferredHour={preferredHour}
              onPreferredHourChange={setPreferredHour}
            />

            <Button type="submit" disabled={updateMutation.isPending}>
              {updateMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Save Changes
            </Button>
          </form>
        </CardContent>
      </Card>

      <Separator />

      <Card className="border-destructive/30">
        <CardHeader>
          <CardTitle className="text-base text-destructive">
            Danger Zone
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-4 text-sm text-muted-foreground">
            Permanently delete your subscription and all associated data. This
            cannot be undone.
          </p>
          <Button
            variant="destructive"
            onClick={handleDelete}
            disabled={deleteMutation.isPending}
          >
            {deleteMutation.isPending && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            {confirmDelete ? "Confirm Delete" : "Delete Subscription"}
          </Button>
          {confirmDelete && (
            <Button
              variant="ghost"
              className="ml-2"
              onClick={() => setConfirmDelete(false)}
            >
              Cancel
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
