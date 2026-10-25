"use client";

import React from "react";
import type { FindingSchema } from "@/lib/schemas";
import { SeverityIndicator, type SeverityType } from "@/components/verdict/SeverityIndicator";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { Gauge, AlertCircle, Info } from "lucide-react";

export interface FindingCardProps {
  finding: FindingSchema;
  className?: string;
  onSelect?: (finding: FindingSchema) => void;
  isSelected?: boolean;
}

export function FindingCard({
  finding,
  className,
  onSelect,
  isSelected = false,
}: FindingCardProps) {
  const severityKey = (finding.severity?.toLowerCase() || "ok") as SeverityType;

  return (
    <Card
      data-testid={`finding-card-${finding.check_id}`}
      onClick={() => onSelect?.(finding)}
      className={cn(
        "p-3.5 border transition-colors rounded-md bg-card space-y-2.5",
        isSelected ? "border-steel ring-1 ring-steel" : "border-border hover:border-steel/60",
        onSelect && "cursor-pointer",
        className
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 truncate">
          <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-secondary text-secondary-foreground border border-border">
            {finding.module}
          </span>
          <span className="font-mono text-xs text-muted-foreground truncate">
            {finding.check_id}
          </span>
        </div>
        <SeverityIndicator severity={severityKey} size="sm" />
      </div>

      <div className="text-sm font-medium text-foreground leading-snug">
        {finding.message}
      </div>

      {finding.metrics && finding.metrics.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 pt-1">
          {finding.metrics.map((metric, idx) => (
            <div
              key={`${metric.name}-${idx}`}
              className="flex items-center justify-between text-xs p-1.5 rounded bg-muted/40 border border-border font-mono"
            >
              <span className="text-muted-foreground truncate mr-2">{metric.name}</span>
              <div className="flex items-center gap-1 shrink-0 font-medium num">
                <span>
                  {typeof metric.value === "number" ? metric.value.toFixed(1) : metric.value}
                </span>
                {metric.unit && <span className="text-muted-foreground">{metric.unit}</span>}
                {metric.error_margin !== undefined && metric.error_margin !== null && (
                  <span className="text-muted-foreground text-[10px]">
                    (±{metric.error_margin} {metric.unit})
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {finding.near_threshold_note && (
        <div className="flex items-center gap-1.5 p-2 text-xs rounded border border-hold/30 bg-hold/10 text-hold font-mono">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
          <span>{finding.near_threshold_note}</span>
        </div>
      )}

      {finding.degraded && (
        <div className="flex items-center gap-1.5 p-2 text-xs rounded border border-border bg-secondary text-muted-foreground font-mono">
          <Info className="w-3.5 h-3.5 shrink-0 text-steel" />
          <span>Degraded execution: fail-safe fallback applied</span>
        </div>
      )}

      <div className="flex items-center justify-between pt-1 text-[11px] font-mono text-muted-foreground border-t border-border/60">
        <div className="flex items-center gap-1.5">
          <Gauge className="w-3 h-3 text-steel" />
          <span>Confidence:</span>
          <span className="text-foreground font-medium num">
            {(finding.confidence * 100).toFixed(0)}%
          </span>
        </div>

        {finding.step_position !== undefined && (
          <span>Step {finding.step_position}</span>
        )}
      </div>
    </Card>
  );
}
