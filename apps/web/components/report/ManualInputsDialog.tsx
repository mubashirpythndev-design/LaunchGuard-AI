"use client";

import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { AlertCircle, ArrowRight, Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import type { AwaitingInputPayload } from "@/lib/sse";

export const manualInputsSchema = z.object({
  wind_speed_ms: z
    .number({
      required_error: "Wind speed is required",
      invalid_type_error: "Wind speed must be a number",
    })
    .min(0, "Wind speed cannot be negative")
    .max(60, "Wind speed cannot exceed 60 m/s"),
  visibility: z.enum(["good", "moderate", "poor"], {
    required_error: "Visibility assessment is required",
  }),
  precipitation: z.enum(["none", "light", "heavy"], {
    required_error: "Precipitation condition is required",
  }),
  area_cleared: z.boolean({
    required_error: "Area clearance confirmation is required",
  }),
  notes: z.string().max(500, "Notes cannot exceed 500 characters").optional(),
});

export type ManualInputsFormData = z.infer<typeof manualInputsSchema>;

interface ManualInputsDialogProps {
  open: boolean;
  onOpenChange?: (open: boolean) => void;
  runId: string;
  awaitingInput?: AwaitingInputPayload | null;
  onSubmit: (data: ManualInputsFormData) => Promise<void> | void;
}

export function ManualInputsDialog({
  open,
  onOpenChange,
  onSubmit,
}: ManualInputsDialogProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<ManualInputsFormData>({
    resolver: zodResolver(manualInputsSchema),
    defaultValues: {
      wind_speed_ms: undefined,
      visibility: "good",
      precipitation: "none",
      area_cleared: false,
      notes: "",
    },
  });

  const areaClearedValue = watch("area_cleared");

  const onFormSubmit = async (data: ManualInputsFormData) => {
    setIsSubmitting(true);
    setServerError(null);
    try {
      await onSubmit(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setServerError(err.message);
      } else {
        setServerError("Failed to submit manual inputs.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md border-zinc-800 bg-zinc-950 font-sans text-zinc-100 sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2 text-base font-semibold">
            <AlertCircle className="h-5 w-5 text-amber-500" />
            <span>Range Safety: Manual Verification Required</span>
          </DialogTitle>
          <DialogDescription className="text-xs text-zinc-400">
            Step 4 paused. Confirm range environmental conditions and pad
            clearance to resume automated inspection.
          </DialogDescription>
        </DialogHeader>

        {serverError && (
          <div
            className="flex items-center space-x-2 rounded-md border border-red-800/80 bg-red-950/40 p-3 text-xs text-red-300"
            role="alert"
          >
            <AlertCircle className="h-4 w-4 shrink-0 text-red-400" />
            <span>{serverError}</span>
          </div>
        )}

        <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-4 py-2">
          {/* Wind Speed */}
          <div className="space-y-1.5">
            <label
              htmlFor="wind_speed_ms"
              className="text-xs font-mono font-medium text-zinc-300"
            >
              Surface Wind Speed (m/s) *
            </label>
            <input
              id="wind_speed_ms"
              type="number"
              step="0.1"
              {...register("wind_speed_ms", { valueAsNumber: true })}
              className="w-full rounded-md border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:border-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500"
              placeholder="e.g. 5.5"
            />
            {errors.wind_speed_ms && (
              <p
                className="text-xs text-red-400"
                role="alert"
                data-testid="error-wind-speed"
              >
                {errors.wind_speed_ms.message}
              </p>
            )}
          </div>

          {/* Visibility */}
          <div className="space-y-1.5">
            <label
              htmlFor="visibility"
              className="text-xs font-mono font-medium text-zinc-300"
            >
              Atmospheric Visibility *
            </label>
            <select
              id="visibility"
              {...register("visibility")}
              className="w-full rounded-md border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 focus:border-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500"
            >
              <option value="good">Good (10+ km, clear horizon)</option>
              <option value="moderate">Moderate (4 - 10 km, haze/fog)</option>
              <option value="poor">Poor (&lt; 4 km, dense cloud/fog)</option>
            </select>
            {errors.visibility && (
              <p className="text-xs text-red-400" role="alert">
                {errors.visibility.message}
              </p>
            )}
          </div>

          {/* Precipitation */}
          <div className="space-y-1.5">
            <label
              htmlFor="precipitation"
              className="text-xs font-mono font-medium text-zinc-300"
            >
              Precipitation *
            </label>
            <select
              id="precipitation"
              {...register("precipitation")}
              className="w-full rounded-md border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 focus:border-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500"
            >
              <option value="none">None</option>
              <option value="light">Light rain / mist</option>
              <option value="heavy">Heavy precipitation / storm</option>
            </select>
            {errors.precipitation && (
              <p className="text-xs text-red-400" role="alert">
                {errors.precipitation.message}
              </p>
            )}
          </div>

          {/* Area Cleared Checkbox */}
          <div className="flex items-center space-x-2 pt-1">
            <input
              id="area_cleared"
              type="checkbox"
              checked={areaClearedValue}
              onChange={(e) => setValue("area_cleared", e.target.checked)}
              className="h-4 w-4 rounded border-zinc-700 bg-zinc-900 text-blue-600 focus:ring-zinc-500"
            />
            <label
              htmlFor="area_cleared"
              className="text-xs font-mono text-zinc-300 select-none cursor-pointer"
            >
              Pad exclusion zone cleared of personnel and equipment *
            </label>
          </div>
          {errors.area_cleared && (
            <p className="text-xs text-red-400" role="alert">
              {errors.area_cleared.message}
            </p>
          )}

          {/* Optional Notes */}
          <div className="space-y-1.5">
            <label
              htmlFor="notes"
              className="text-xs font-mono font-medium text-zinc-400"
            >
              Range Officer Notes (Optional)
            </label>
            <textarea
              id="notes"
              rows={2}
              {...register("notes")}
              className="w-full rounded-md border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:border-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500"
              placeholder="e.g. Cleared by Range Safety Officer."
            />
          </div>

          <DialogFooter className="pt-2">
            <Button
              type="submit"
              disabled={isSubmitting}
              className="w-full sm:w-auto font-mono text-xs uppercase"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                  <span>Resuming...</span>
                </>
              ) : (
                <>
                  <span>Resume Inspection</span>
                  <ArrowRight className="ml-2 h-3.5 w-3.5" />
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
