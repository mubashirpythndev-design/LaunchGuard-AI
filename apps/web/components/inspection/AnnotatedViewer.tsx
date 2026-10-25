"use client";

import React, { useState, useMemo } from "react";
import type { FindingSchema } from "@/lib/schemas";
import { cn } from "@/lib/utils";
import { Layers, Eye, EyeOff } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface AnnotatedViewerProps {
  imageUrl: string;
  findings: FindingSchema[];
  showControls?: boolean;
  className?: string;
}

export function AnnotatedViewer({
  imageUrl,
  findings,
  showControls = true,
  className,
}: AnnotatedViewerProps) {
  // Extract all distinct modules present in the findings
  const allModules = useMemo(() => {
    const set = new Set<string>();
    for (const f of findings) {
      if (f.module) set.add(f.module);
    }
    return Array.from(set);
  }, [findings]);

  // Keep track of enabled module overlays (default all enabled)
  const [enabledModules, setEnabledModules] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    for (const m of allModules) {
      initial[m] = true;
    }
    return initial;
  });

  const toggleModule = (moduleKey: string) => {
    setEnabledModules((prev) => ({
      ...prev,
      [moduleKey]: prev[moduleKey] === false ? true : false,
    }));
  };

  const getModuleLabel = (moduleKey: string) => {
    return moduleKey.replace(/^cv\./, "").replace(/_/g, " ");
  };

  const getSeverityStroke = (severity: string) => {
    switch (severity.toLowerCase()) {
      case "critical":
        return "stroke-[var(--nogo)] fill-[var(--nogo)]/10";
      case "warning":
        return "stroke-[var(--hold)] fill-[var(--hold)]/10";
      case "ok":
      default:
        return "stroke-[var(--go)] fill-[var(--go)]/10";
    }
  };

  const getSeverityTextClass = (severity: string) => {
    switch (severity.toLowerCase()) {
      case "critical":
        return "fill-[var(--nogo)]";
      case "warning":
        return "fill-[var(--hold)]";
      case "ok":
      default:
        return "fill-[var(--go)]";
    }
  };

  const visibleFindings = useMemo(() => {
    return findings.filter((f) => {
      if (!f.overlay) return false;
      return enabledModules[f.module] !== false;
    });
  }, [findings, enabledModules]);

  return (
    <div className={cn("flex flex-col space-y-3", className)}>
      {showControls && allModules.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 p-2 border rounded-md border-border bg-card">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground mr-1">
            <Layers className="w-3.5 h-3.5 text-steel" />
            <span className="font-medium">Overlays:</span>
          </div>

          {allModules.map((moduleKey) => {
            const isEnabled = enabledModules[moduleKey] !== false;
            const label = getModuleLabel(moduleKey);
            const count = findings.filter((f) => f.module === moduleKey && f.overlay).length;

            return (
              <Button
                key={moduleKey}
                type="button"
                variant={isEnabled ? "secondary" : "ghost"}
                size="sm"
                aria-label={`Toggle ${label} overlays`}
                onClick={() => toggleModule(moduleKey)}
                className={cn(
                  "h-7 px-2.5 text-xs font-mono transition-colors",
                  isEnabled
                    ? "border border-border text-foreground"
                    : "text-muted-foreground line-through opacity-70",
                )}
              >
                {isEnabled ? (
                  <Eye className="w-3 h-3 mr-1.5 text-steel" />
                ) : (
                  <EyeOff className="w-3 h-3 mr-1.5 opacity-50" />
                )}
                <span>{label}</span>
                <span className="ml-1.5 text-[10px] opacity-70 num">({count})</span>
              </Button>
            );
          })}
        </div>
      )}

      <div className="relative overflow-hidden rounded-md border border-border bg-black/5 dark:bg-black/30 flex items-center justify-center">
        {/* Base Image */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={imageUrl}
          alt={
            findings.some((finding) => finding.check_id.endsWith("subject_unverified"))
              ? "Uploaded image; rocket geometry unverified"
              : "Annotated rocket view"
          }
          className="w-full h-auto max-h-[600px] object-contain block select-none"
        />

        {/* Normalized SVG Overlay Layer */}
        <svg
          data-testid="overlay-svg"
          viewBox="0 0 1000 1000"
          preserveAspectRatio="none"
          className="absolute inset-0 w-full h-full pointer-events-none"
        >
          {visibleFindings.map((finding) => {
            const overlay = finding.overlay;
            if (!overlay) return null;

            const strokeClass = getSeverityStroke(finding.severity);
            const textClass = getSeverityTextClass(finding.severity);
            const checkId = finding.check_id;

            if (overlay.kind === "bbox") {
              const pts = overlay.points;
              if (!pts || pts.length < 2) return null;
              const [p1, p2] = pts;
              const x1 = p1[0] * 1000;
              const y1 = p1[1] * 1000;
              const x2 = p2[0] * 1000;
              const y2 = p2[1] * 1000;

              const x = Math.min(x1, x2);
              const y = Math.min(y1, y2);
              const width = Math.abs(x2 - x1);
              const height = Math.abs(y2 - y1);

              return (
                <g key={checkId} data-testid={`overlay-bbox-${checkId}`}>
                  <rect
                    x={x}
                    y={y}
                    width={width}
                    height={height}
                    strokeWidth="3"
                    strokeDasharray={finding.severity === "warning" ? "8 4" : undefined}
                    className={strokeClass}
                  />
                  {overlay.label && (
                    <g>
                      <rect
                        x={x}
                        y={Math.max(0, y - 24)}
                        width={Math.min(300, overlay.label.length * 9 + 12)}
                        height="22"
                        className="fill-background/90 stroke-border"
                        strokeWidth="1"
                      />
                      <text
                        x={x + 6}
                        y={Math.max(16, y - 8)}
                        className={cn("text-[13px] font-mono font-medium select-none", textClass)}
                      >
                        {overlay.label}
                      </text>
                    </g>
                  )}
                </g>
              );
            }

            if (overlay.kind === "arc") {
              const pts = overlay.points;
              if (!pts || pts.length === 0) return null;
              const center = pts[0];
              const cx = center[0] * 1000;
              const cy = center[1] * 1000;
              const radius = (overlay.radius ?? 0.08) * 1000;
              const startDeg = overlay.start_deg ?? 0;
              const endDeg = overlay.end_deg ?? 0;

              const startRad = ((startDeg - 90) * Math.PI) / 180;
              const endRad = ((endDeg - 90) * Math.PI) / 180;

              const x1 = cx + radius * Math.cos(startRad);
              const y1 = cy + radius * Math.sin(startRad);
              const x2 = cx + radius * Math.cos(endRad);
              const y2 = cy + radius * Math.sin(endRad);

              const deltaDeg = Math.abs(endDeg - startDeg);
              const largeArcFlag = deltaDeg > 180 ? 1 : 0;
              const sweepFlag = endDeg >= startDeg ? 1 : 0;

              const pathData = `M ${cx} ${cy} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArcFlag} ${sweepFlag} ${x2} ${y2} Z`;

              return (
                <g key={checkId} data-testid={`overlay-arc-${checkId}`}>
                  <path
                    d={pathData}
                    strokeWidth="3"
                    strokeDasharray={finding.severity === "warning" ? "8 4" : undefined}
                    className={strokeClass}
                  />
                  {overlay.label && (
                    <g>
                      <rect
                        x={cx}
                        y={Math.max(0, cy - 24)}
                        width={Math.min(300, overlay.label.length * 9 + 12)}
                        height="22"
                        className="fill-background/90 stroke-border"
                        strokeWidth="1"
                      />
                      <text
                        x={cx + 6}
                        y={Math.max(16, cy - 8)}
                        className={cn("text-[13px] font-mono font-medium select-none", textClass)}
                      >
                        {overlay.label}
                      </text>
                    </g>
                  )}
                </g>
              );
            }

            if (overlay.kind === "polygon") {
              const pts = overlay.points;
              if (!pts || pts.length < 3) return null;
              const pointsStr = pts.map(([px, py]) => `${px * 1000},${py * 1000}`).join(" ");

              return (
                <g key={checkId} data-testid={`overlay-polygon-${checkId}`}>
                  <polygon points={pointsStr} strokeWidth="3" className={strokeClass} />
                </g>
              );
            }

            return null;
          })}
        </svg>
      </div>
    </div>
  );
}
