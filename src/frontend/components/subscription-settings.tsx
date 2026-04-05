"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
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
import { useUpdateSubscription, useDeleteSubscription, useGenerateFundDescription } from "@/lib/hooks";
import { clearSubscriptionId } from "@/lib/subscription";
import { ApiError, type Frequency, type SubscriptionResponse } from "@/lib/api";

interface SubscriptionSettingsProps {
  subscription: SubscriptionResponse;
}

export function SubscriptionSettings({
  subscription,
}: SubscriptionSettingsProps) {
  const router = useRouter();
  const updateMutation = useUpdateSubscription(subscription.id);
  const deleteMutation = useDeleteSubscription();
  const generateMutation = useGenerateFundDescription();

  const [frequency, setFrequency] = useState<Frequency>(
    subscription.frequency
  );
  const [fundDescription, setFundDescription] = useState(
    subscription.fund_description ?? ""
  );
  const [confirmDelete, setConfirmDelete] = useState(false);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    try {
      await updateMutation.mutateAsync({
        frequency,
        fund_description: fundDescription.trim() || null,
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

            <div className="space-y-2">
              <Label htmlFor="settings-frequency">Digest Frequency</Label>
              <Select
                value={frequency}
                onValueChange={(v) => v && setFrequency(v as Frequency)}
              >
                <SelectTrigger id="settings-frequency">
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
                <Label htmlFor="settings-fund-desc">Fund Description</Label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={generateMutation.isPending}
                  onClick={async () => {
                    try {
                      const result = await generateMutation.mutateAsync(subscription.email);
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
                id="settings-fund-desc"
                placeholder="Describe your fund's focus..."
                value={fundDescription}
                onChange={(e) => setFundDescription(e.target.value)}
                rows={3}
                disabled={generateMutation.isPending}
              />
            </div>

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
