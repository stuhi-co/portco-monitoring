"use client";

import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { DayOfWeek, Frequency } from "@/lib/api";
import { DAY_OPTIONS, HOUR_OPTIONS } from "@/lib/config";

interface DigestSchedulePickerProps {
  frequency: Frequency;
  onFrequencyChange: (v: Frequency) => void;
  preferredDay: DayOfWeek;
  onPreferredDayChange: (v: DayOfWeek) => void;
  preferredHour: number;
  onPreferredHourChange: (v: number) => void;
}

export function DigestSchedulePicker({
  frequency,
  onFrequencyChange,
  preferredDay,
  onPreferredDayChange,
  preferredHour,
  onPreferredHourChange,
}: DigestSchedulePickerProps) {
  return (
    <div className="space-y-2">
      <Label>Digest Schedule</Label>
      <div className="space-y-1">
        <Label className="text-xs text-muted-foreground font-normal">Frequency</Label>
        <Select
          value={frequency}
          onValueChange={(v) => {
            if (v) onFrequencyChange(v as Frequency);
          }}
        >
          <SelectTrigger>
            <SelectValue placeholder="Frequency" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="daily" label="Daily">Daily</SelectItem>
            <SelectItem value="weekly" label="Weekly">Weekly</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className={frequency === "weekly" ? "grid grid-cols-2 gap-4" : ""}>
        {frequency === "weekly" && (
          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground font-normal">Day</Label>
            <Select
              value={preferredDay}
              onValueChange={(v) => {
                if (v) onPreferredDayChange(v as DayOfWeek);
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="Day of week" />
              </SelectTrigger>
              <SelectContent>
                {DAY_OPTIONS.map((day) => (
                  <SelectItem key={day.value} value={day.value} label={day.label}>
                    {day.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
        <div className="space-y-1">
          <Label className="text-xs text-muted-foreground font-normal">Time</Label>
          <Select
            value={String(preferredHour)}
            onValueChange={(v) => {
              if (v) onPreferredHourChange(Number(v));
            }}
          >
            <SelectTrigger>
              <SelectValue placeholder="Time" />
            </SelectTrigger>
            <SelectContent>
              {HOUR_OPTIONS.map((hour) => (
                <SelectItem key={hour.value} value={hour.value} label={hour.label}>
                  {hour.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      <p className="text-xs text-muted-foreground">
        Times are in your local timezone ({Intl.DateTimeFormat().resolvedOptions().timeZone})
      </p>
    </div>
  );
}
