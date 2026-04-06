"use client";

import { Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useGenerateFundDescription } from "@/lib/hooks";
import { ApiError } from "@/lib/api";

interface FundDescriptionFieldProps {
  email: string;
  value: string;
  onChange: (v: string) => void;
  label?: string;
  requireEmailValidation?: boolean;
}

export function FundDescriptionField({
  email,
  value,
  onChange,
  label = "Fund Description",
  requireEmailValidation = false,
}: FundDescriptionFieldProps) {
  const generateMutation = useGenerateFundDescription();

  const emailInvalid = requireEmailValidation && (!email.trim() || !email.includes("@"));

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label>{label}</Label>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={emailInvalid || generateMutation.isPending}
          onClick={async () => {
            try {
              const result = await generateMutation.mutateAsync(email.trim());
              onChange(result.fund_description);
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
        placeholder="Describe your fund's focus..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={3}
        disabled={generateMutation.isPending}
      />
    </div>
  );
}
