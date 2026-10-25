"use client";

import React, { useRef, useCallback } from "react";
import { useMonitorStore, type Point2D } from "@/stores/monitor-store";
import { AlertCircle, Trash2, Edit3, Check, MousePointer } from "lucide-react";

function ccw(a: Point2D, b: Point2D, c: Point2D): number {
  return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0]);
}

function segmentsProperlyIntersect(
  p1: Point2D,
  p2: Point2D,
  p3: Point2D,
  p4: Point2D
): boolean {
  const d1 = ccw(p3, p4, p1);
  const d2 = ccw(p3, p4, p2);
  const d3 = ccw(p1, p2, p3);
  const d4 = ccw(p1, p2, p4);
  const eps = 1e-7;
  return (
    ((d1 > eps && d2 < -eps) || (d1 < -eps && d2 > eps)) &&
    ((d3 > eps && d4 < -eps) || (d3 < -eps && d4 > eps))
  );
}

export function validateZonePolygon(points: Point2D[]): string | null {
  if (points.length < 3) {
    return "Danger zone polygon must contain at least 3 points.";
  }
  const n = points.length;
  for (let i = 0; i < n; i++) {
    const p1 = points[i];
    const p2 = points[(i + 1) % n];
    for (let j = i + 1; j < n; j++) {
      if (Math.abs(i - j) <= 1 || (i === 0 && j === n - 1)) {
        continue;
      }
      const p3 = points[j];
      const p4 = points[(j + 1) % n];
      if (segmentsProperlyIntersect(p1, p2, p3, p4)) {
        return "Danger zone polygon outline is self-intersecting.";
      }
    }
  }
  let area = 0.0;
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n;
    area += points[i][0] * points[j][1];
    area -= points[j][0] * points[i][1];
  }
  const shoelaceArea = Math.abs(area) * 0.5;
  if (shoelaceArea <= 1e-7) {
    return "Danger zone polygon has zero area.";
  }
  return null;
}

interface ZoneEditorProps {
  children?: React.ReactNode;
  className?: string;
  onSaveZone?: (points: Point2D[]) => Promise<void> | void;
}

export function ZoneEditor({ children, className = "", onSaveZone }: ZoneEditorProps) {
  const {
    zonePoints,
    isZoneEditing,
    validationError,
    addZonePoint,
    updateZonePoint,
    clearZonePoints,
    setIsZoneEditing,
    setValidationError,
  } = useMonitorStore();

  const svgRef = useRef<SVGSVGElement | null>(null);
  const draggingIndexRef = useRef<number | null>(null);

  const getNormalizedPoint = useCallback((e: React.MouseEvent<SVGSVGElement>): Point2D | null => {
    if (!svgRef.current) return null;
    const rect = svgRef.current.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return null;
    const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
    return [Math.round(x * 1000) / 1000, Math.round(y * 1000) / 1000];
  }, []);

  const handleSvgClick = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!isZoneEditing) return;
    if (draggingIndexRef.current !== null) {
      draggingIndexRef.current = null;
      return;
    }
    const pt = getNormalizedPoint(e);
    if (pt) {
      addZonePoint(pt);
    }
  };

  const handlePointMouseDown = (index: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!isZoneEditing) return;
    draggingIndexRef.current = index;
  };

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!isZoneEditing || draggingIndexRef.current === null) return;
    const pt = getNormalizedPoint(e);
    if (pt) {
      updateZonePoint(draggingIndexRef.current, pt);
    }
  };

  const handleMouseUp = () => {
    draggingIndexRef.current = null;
  };

  const handleSave = async () => {
    const error = validateZonePolygon(zonePoints);
    if (error) {
      setValidationError(error);
      return;
    }
    setValidationError(null);
    setIsZoneEditing(false);
    if (onSaveZone) {
      await onSaveZone(zonePoints);
    }
  };

  const handleClear = () => {
    clearZonePoints();
    setValidationError(null);
  };

  const polygonSvgPoints = zonePoints.map((p) => `${p[0] * 100},${p[1] * 100}`).join(" ");

  return (
    <div
      data-testid="zone-editor-container"
      className={`relative rounded-md border border-border bg-card overflow-hidden select-none ${className}`}
    >
      {/* Underlying media content */}
      <div className="relative w-full aspect-video flex items-center justify-center bg-muted/40">
        {children}

        {/* SVG Drawing & Overlay Layer */}
        <svg
          ref={svgRef}
          data-testid="zone-editor-svg"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          className={`absolute inset-0 w-full h-full ${isZoneEditing ? "cursor-crosshair" : "cursor-default"}`}
          onClick={handleSvgClick}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
        >
          {zonePoints.length >= 3 && (
            <polygon
              data-testid="zone-polygon"
              points={polygonSvgPoints}
              className="fill-destructive/20 stroke-destructive"
              strokeWidth="0.8"
            />
          )}

          {zonePoints.length === 2 && (
            <line
              x1={zonePoints[0][0] * 100}
              y1={zonePoints[0][1] * 100}
              x2={zonePoints[1][0] * 100}
              y2={zonePoints[1][1] * 100}
              className="stroke-destructive"
              strokeWidth="0.8"
              strokeDasharray="2,2"
            />
          )}

          {/* Interactive Point Handles */}
          {zonePoints.map((pt, idx) => (
            <circle
              key={idx}
              data-testid={`zone-point-handle-${idx}`}
              cx={pt[0] * 100}
              cy={pt[1] * 100}
              r={isZoneEditing ? "1.5" : "1"}
              className="fill-background stroke-destructive cursor-pointer hover:fill-destructive"
              strokeWidth="0.6"
              onMouseDown={(e) => handlePointMouseDown(idx, e)}
            />
          ))}
        </svg>
      </div>

      {/* Inline Validation Alert */}
      {validationError && (
        <div
          role="alert"
          data-testid="zone-validation-error"
          className="flex items-center gap-2 p-2 bg-destructive/10 border-t border-destructive text-destructive text-xs font-mono"
        >
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{validationError}</span>
        </div>
      )}

      {/* Editor Controls Bar */}
      <div className="flex items-center justify-between p-2.5 border-t border-border bg-card text-xs">
        <div className="flex items-center gap-2">
          <button
            type="button"
            data-testid="toggle-edit-btn"
            onClick={() => setIsZoneEditing(!isZoneEditing)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md border font-medium transition-colors ${
              isZoneEditing
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-secondary text-secondary-foreground border-border hover:bg-muted"
            }`}
          >
            {isZoneEditing ? (
              <>
                <MousePointer className="w-3.5 h-3.5" />
                <span>Locking / Active</span>
              </>
            ) : (
              <>
                <Edit3 className="w-3.5 h-3.5" />
                <span>Draw Danger Zone</span>
              </>
            )}
          </button>

          <span className="text-muted-foreground font-mono">
            {zonePoints.length} point{zonePoints.length === 1 ? "" : "s"}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {zonePoints.length > 0 && (
            <button
              type="button"
              data-testid="clear-zone-btn"
              onClick={handleClear}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-md border border-border text-muted-foreground hover:text-foreground hover:bg-muted"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Clear</span>
            </button>
          )}

          {isZoneEditing && (
            <button
              type="button"
              data-testid="save-zone-btn"
              onClick={handleSave}
              className="flex items-center gap-1 px-3 py-1.5 rounded-md border border-border bg-foreground text-background font-medium hover:opacity-90"
            >
              <Check className="w-3.5 h-3.5" />
              <span>Save Zone</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
