import React from "react";
import { AlertOctagon, AlertTriangle, CheckCircle2 } from "lucide-react";

export type VerdictType = "GO" | "HOLD" | "NO-GO";

export interface VerdictBadgeProps {
  verdict: VerdictType;
  className?: string;
  size?: "sm" | "md" | "lg";
}

const VERDICT_CONFIG: Record<
  VerdictType,
  {
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    styles: string;
  }
> = {
  GO: {
    label: "GO",
    icon: CheckCircle2,
    styles: "bg-go/15 text-go border-go/40",
  },
  HOLD: {
    label: "HOLD",
    icon: AlertTriangle,
    styles: "bg-hold/15 text-hold border-hold/40",
  },
  "NO-GO": {
    label: "NO-GO",
    icon: AlertOctagon,
    styles: "bg-nogo/15 text-nogo border-nogo/40",
  },
};

const SIZE_STYLES = {
  sm: "text-xs px-2 py-0.5 gap-1.5 font-medium",
  md: "text-sm px-2.5 py-1 gap-2 font-semibold",
  lg: "text-base px-3.5 py-1.5 gap-2.5 font-bold",
};

const ICON_SIZES = {
  sm: "h-3.5 w-3.5",
  md: "h-4 w-4",
  lg: "h-5 w-5",
};

/**
 * Static verdict badge rendering text + icon + colour (Constitution 2.I, 4.III).
 * React Bits and animations are strictly prohibited on this component.
 */
export function VerdictBadge({
  verdict,
  className = "",
  size = "md",
}: VerdictBadgeProps) {
  const config = VERDICT_CONFIG[verdict] || VERDICT_CONFIG.HOLD;
  const Icon = config.icon;

  return (
    <div data-testid="verdict-badge" className="inline-flex">
      <span
        data-testid={`verdict-badge-${verdict.toLowerCase()}`}
        className={`inline-flex items-center border rounded-md font-mono tracking-wider select-none ${config.styles} ${SIZE_STYLES[size]} ${className}`}
      >
        <Icon className={`${ICON_SIZES[size]} shrink-0`} aria-hidden="true" />
        <span>{config.label}</span>
      </span>
    </div>
  );
}
