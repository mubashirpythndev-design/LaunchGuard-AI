"use client";

import React, { useState } from "react";
import { Eye, Layers, ScanLine } from "lucide-react";
import type { FindingSchema } from "@/lib/schemas";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { AnnotatedViewer } from "./AnnotatedViewer";

type EvidenceMode = "comparison" | "heatmap" | "contours";

export function ComparisonSlider({
  baselineUrl,
  currentUrl,
  heatmapUrl,
  findings,
  className,
}: {
  baselineUrl: string;
  currentUrl: string;
  heatmapUrl?: string | null;
  findings: FindingSchema[];
  className?: string;
}) {
  const [position, setPosition] = useState(50);
  const [mode, setMode] = useState<EvidenceMode>("comparison");
  const [showContours, setShowContours] = useState(false);
  function reveal(event: React.PointerEvent<HTMLDivElement>) {
    const bounds = event.currentTarget.getBoundingClientRect();
    if (bounds.width > 0)
      setPosition(
        Math.round(
          Math.max(0, Math.min(100, ((event.clientX - bounds.left) / bounds.width) * 100)),
        ),
      );
  }

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border bg-card p-2">
        <div className="flex items-center gap-2 px-1 text-xs font-medium text-muted-foreground">
          <ScanLine className="h-3.5 w-3.5 text-steel" />
          Reference comparison
        </div>
        <div className="flex flex-wrap gap-1" aria-label="Evidence view">
          <Button
            type="button"
            size="sm"
            variant="outline"
            aria-pressed={showContours}
            onClick={() => setShowContours(!showContours)}
          >
            {showContours ? "Hide difference contours" : "Show difference contours"}
          </Button>
          <Button
            type="button"
            size="sm"
            variant={mode === "comparison" ? "secondary" : "ghost"}
            onClick={() => setMode("comparison")}
          >
            <Eye className="mr-1.5 h-3.5 w-3.5" /> Comparison
          </Button>
          <Button
            type="button"
            size="sm"
            variant={mode === "contours" ? "secondary" : "ghost"}
            onClick={() => setMode("contours")}
          >
            <Layers className="mr-1.5 h-3.5 w-3.5" /> Contours
          </Button>
          {heatmapUrl && (
            <Button
              type="button"
              size="sm"
              variant={mode === "heatmap" ? "secondary" : "ghost"}
              onClick={() => setMode("heatmap")}
            >
              Difference map
            </Button>
          )}
        </div>
      </div>

      {mode === "contours" ? (
        <AnnotatedViewer imageUrl={currentUrl} findings={findings} showControls={false} />
      ) : mode === "heatmap" && heatmapUrl ? (
        <div className="overflow-hidden rounded-md border border-border bg-black/30">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={heatmapUrl}
            alt="Reference comparison difference map"
            className="block max-h-[600px] w-full object-contain"
          />
        </div>
      ) : (
        <div className="space-y-3">
          <div
            className="relative isolate overflow-hidden rounded-md border border-border bg-black/30 touch-none cursor-col-resize"
            data-testid="comparison-surface"
            onPointerDown={(event) => {
              event.currentTarget.setPointerCapture(event.pointerId);
              reveal(event);
            }}
            onPointerMove={(event) => {
              if (event.currentTarget.hasPointerCapture(event.pointerId)) reveal(event);
            }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={baselineUrl}
              alt="Golden reference"
              className="block h-auto w-full select-none"
              draggable={false}
            />
            {showContours && (
              <svg
                viewBox="0 0 1000 1000"
                preserveAspectRatio="none"
                className="pointer-events-none absolute inset-0 z-10 h-full w-full"
                aria-label="Reference difference contours"
              >
                {findings
                  .filter((finding) => finding.severity !== "ok")
                  .map((finding) => {
                    const overlay = finding.overlay;
                    if (!overlay?.points || overlay.points.length < 2) return null;
                    if (overlay.kind === "bbox") {
                      const [first, second] = overlay.points;
                      return (
                        <rect
                          key={finding.check_id}
                          x={Math.min(first[0], second[0]) * 1000}
                          y={Math.min(first[1], second[1]) * 1000}
                          width={Math.abs(first[0] - second[0]) * 1000}
                          height={Math.abs(first[1] - second[1]) * 1000}
                          className="stroke-nogo fill-none"
                          strokeWidth="3"
                        />
                      );
                    }
                    return (
                      <polygon
                        key={finding.check_id}
                        points={overlay.points.map(([x, y]) => `${x * 1000},${y * 1000}`).join(" ")}
                        className="stroke-nogo fill-none"
                        strokeWidth="3"
                      />
                    );
                  })}
              </svg>
            )}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={currentUrl}
              alt="Aligned current capture"
              className="absolute inset-0 h-full w-full select-none object-contain"
              style={{ clipPath: `inset(0 0 0 ${position}%)` }}
              draggable={false}
            />
            <div
              aria-hidden="true"
              className="pointer-events-none absolute inset-y-0 w-px bg-foreground"
              style={{ left: `${position}%` }}
            >
              <span className="absolute left-1/2 top-1/2 h-9 w-3 -translate-x-1/2 -translate-y-1/2 rounded-sm border border-foreground bg-background" />
            </div>
            <span className="absolute left-3 top-3 rounded border border-border bg-background/90 px-2 py-1 text-[10px] font-mono uppercase tracking-widest">
              Golden reference
            </span>
            <span className="absolute right-3 top-3 rounded border border-border bg-background/90 px-2 py-1 text-[10px] font-mono uppercase tracking-widest">
              Current
            </span>
          </div>
          <label className="block space-y-2 text-xs text-muted-foreground">
            <span className="sr-only">Reveal current capture over golden reference</span>
            <input
              type="range"
              min="0"
              max="100"
              value={position}
              onChange={(event) => setPosition(Number(event.target.value))}
              className="w-full accent-[var(--steel)]"
              aria-label="Comparison reveal position"
            />
            <span className="flex justify-between font-mono uppercase tracking-wider">
              <span>Reference</span>
              <span>Aligned current</span>
            </span>
          </label>
        </div>
      )}
    </div>
  );
}
