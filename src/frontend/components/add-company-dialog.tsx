"use client";

import { useState } from "react";
import { Plus, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useIndustries, useUpdateSubscription } from "@/lib/hooks";
import type { Industry } from "@/lib/api";

interface AddCompanyDialogProps {
  subscriptionId: string;
}

export function AddCompanyDialog({ subscriptionId }: AddCompanyDialogProps) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");
  const { data: industries } = useIndustries();
  const updateMutation = useUpdateSubscription(subscriptionId);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;

    try {
      await updateMutation.mutateAsync({
        add_companies: [
          { name: name.trim(), industry: (industry as Industry) || undefined },
        ],
      });
      toast.success(`Added ${name.trim()}`);
      setName("");
      setIndustry("");
      setOpen(false);
    } catch {
      toast.error("Failed to add company");
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button variant="outline" size="sm" />}>
        <Plus className="mr-1 h-4 w-4" />
        Add Company
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add Company</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleAdd} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="company-name">Company Name</Label>
            <Input
              id="company-name"
              placeholder="e.g. Stripe"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="company-industry">Industry (optional)</Label>
            <Select value={industry} onValueChange={(v) => setIndustry(v ?? "")}>
              <SelectTrigger id="company-industry">
                <SelectValue placeholder="Select industry" />
              </SelectTrigger>
              <SelectContent>
                {industries?.map((ind) => (
                  <SelectItem key={ind.value} value={ind.value}>
                    {ind.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button
            type="submit"
            className="w-full"
            disabled={updateMutation.isPending}
          >
            {updateMutation.isPending && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            Add
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
