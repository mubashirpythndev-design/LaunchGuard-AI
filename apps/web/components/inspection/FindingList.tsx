"use client";

import React, { useState, useMemo } from "react";
import type { FindingSchema } from "@/lib/schemas";
import { FindingCard } from "@/components/inspection/FindingCard";
import { cn } from "@/lib/utils";
import { ListFilter, ShieldAlert, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface FindingListProps {
  findings: FindingSchema[];
  onSelectFinding?: (finding: FindingSchema) => void;
  selectedCheckId?: string | null;
  className?: string;
}

export function FindingList({
  findings,
  onSelectFinding,
  selectedCheckId,
  className,
}: FindingListProps) {
  const [severityFilter, setSeverityFilter] = useState<string>("all");

  const counts = useMemo(() => {
    let critical = 0;
    let warning = 0;
    let ok = 0;
    for (const f of findings) {
      const sev = f.severity?.toLowerCase();
      if (sev === "critical") critical++;
      else if (sev === "warning") warning++;
      else if (sev === "ok") ok++;
    }
    return { total: findings.length, critical, warning, ok };
  }, [findings]);

  const filteredFindings = useMemo(() => {
    let list = findings;
    if (severityFilter !== "all") {
      list = list.filter((f) => f.severity?.toLowerCase() === severityFilter);
    }
    // Sort critical first, then warning, then ok
    const rank: Record<string, number> = { critical: 1, warning: 2, ok: 3 };
    return [...list].sort((a, b) => {
      const rankA = rank[a.severity?.toLowerCase()] ?? 4;
      const rankB = rank[b.severity?.toLowerCase()] ?? 4;
      if (rankA !== rankB) return rankA - rankB;
      return (a.step_position ?? 0) - (b.step_position ?? 0);
    });
  }, [findings, severityFilter]);

  return (
    <div className={cn("flex flex-col space-y-3", className)}>
      {/* Header and filter bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 p-2.5 border rounded-md border-border bg-card">
        <div className="flex items-center gap-2">
          <ListFilter className="w-4 h-4 text-steel shrink-0" />
          <span className="text-xs font-semibold text-foreground">
            Findings ({counts.total})
          </span>
          <div className="flex items-center gap-1.5 text-[11px] font-mono">
            {counts.critical > 0 && (
              <span className="px-1.5 py-0.5 rounded border border-nogo/30 bg-nogo/10 text-nogo num">
                {counts.critical} critical
              </span>
            )}
            {counts.warning > 0 && (
              <span className="px-1.5 py-0.5 rounded border border-hold/30 bg-hold/10 text-hold num">
                {counts.warning} warning
              </span>
            )}
            {counts.ok > 0 && (
              <span className="px-1.5 py-0.5 rounded border border-go/30 bg-go/10 text-go num">
                {counts.ok} ok
              </span>
            )}
          </div>
        </div>

        {/* Severity filter buttons */}
        <div className="flex items-center gap-1">
          {(["all", "critical", "warning", "ok"] as const).map((filterKey) => (
            <Button
              key={filterKey}
              type="button"
              variant={severityFilter === filterKey ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setSeverityFilter(filterKey)}
              className={cn(
                "h-6 px-2 text-[11px] font-mono capitalize",
                severityFilter === filterKey
                  ? "border border-border text-foreground"
                  : "text-muted-foreground"
              )}
            >
              {filterKey}
            </Button>
          ))}
        </div>
      </div>

      {/* Findings stack */}
      {filteredFindings.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-8 border rounded-md border-border bg-card text-center space-y-2">
          {findings.length === 0 ? (
            <>
              <CheckCircle2 className="w-8 h-8 text-steel" />
              <p className="text-sm font-medium text-foreground">No inspection findings</p>
              <p className="text-xs text-muted-foreground">
                Upload a launch vehicle image to run automated body and fin inspections.
              </p>
            </>
          ) : (
            <>
              <ShieldAlert className="w-8 h-8 text-muted-foreground" />
              <p className="text-sm font-medium text-foreground">
                No {severityFilter} findings
              </p>
              <p className="text-xs text-muted-foreground">
                Adjust filter to view all {counts.total} findings.
              </p>
            </>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          {filteredFindings.map((finding, index) => (
            <FindingCard
              key={`${finding.quadrant ?? "single"}-${finding.module}-${finding.check_id}-${index}`}
              finding={finding}
              isSelected={selectedCheckId === finding.check_id}
              onSelect={onSelectFinding}
            />
          ))}
        </div>
      )}
    </div>
  );
}
