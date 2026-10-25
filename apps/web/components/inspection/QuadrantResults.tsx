"use client";

import React, { useState } from "react";
import type { FindingSchema, QuadrantImageSchema } from "@/lib/schemas";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AnnotatedViewer } from "./AnnotatedViewer";
import { ComparisonSlider } from "./ComparisonSlider";
import { FindingList } from "./FindingList";

export const ANGLES = [
  { key: "front", label: "Front", degrees: "0" },
  { key: "right", label: "Right", degrees: "90" },
  { key: "back", label: "Back", degrees: "180" },
  { key: "left", label: "Left", degrees: "270" },
] as const satisfies ReadonlyArray<{
  key: QuadrantImageSchema["quadrant"];
  label: string;
  degrees: string;
}>;

export function QuadrantResults({
  images,
  findings,
  compact = false,
}: {
  images: QuadrantImageSchema[];
  findings: FindingSchema[];
  compact?: boolean;
}) {
  const [selected, setSelected] = useState("front");
  const image = images.find((item) => item.quadrant === selected);
  const visibleFindings = findings.filter((finding) => finding.quadrant === selected);
  const referenceFinding = visibleFindings.find((finding) => finding.module === "cv.reference");

  return (
    <section className="space-y-4" aria-label="Quadrant inspection evidence">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-mono uppercase tracking-widest text-muted-foreground">
            Optical evidence
          </p>
          <h2 className="text-xl font-semibold">Every angle. One decision.</h2>
        </div>
        <p className="text-xs text-muted-foreground">
          Verdict includes findings from all four views.
        </p>
      </div>
      <Tabs value={selected} onValueChange={setSelected}>
        <TabsList className="grid h-auto w-full grid-cols-4 gap-1 p-1">
          {ANGLES.map((angle) => (
            <TabsTrigger key={angle.key} value={angle.key} className="flex flex-col gap-1 py-3">
              <span>
                {angle.label} {angle.degrees}&deg;
              </span>
              <span className="font-mono text-xs">
                {findings.filter((f) => f.quadrant === angle.key).length} findings
              </span>
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
      <div className={compact ? "space-y-5" : "grid gap-5 lg:grid-cols-2"}>
        <div className="min-w-0">
          {image?.reference_image_url && image.aligned_image_url ? (
            <ComparisonSlider
              key={selected}
              baselineUrl={image.reference_image_url}
              currentUrl={image.aligned_image_url}
              heatmapUrl={image.heatmap_image_url}
              findings={referenceFinding ? [referenceFinding] : []}
            />
          ) : image?.image_url ? (
            <AnnotatedViewer
              key={selected}
              imageUrl={image.image_url}
              findings={visibleFindings}
              showControls
            />
          ) : (
            <div className="flex min-h-64 items-center justify-center rounded-md border border-border bg-card p-8 text-center text-muted-foreground">
              No image for this quadrant. Coverage is incomplete.
            </div>
          )}
        </div>
        <FindingList key={selected} findings={visibleFindings} />
      </div>
    </section>
  );
}
