import React from "react";
import { AlertOctagon, AlertTriangle, CheckCircle2 } from "lucide-react";

export type SeverityType = "ok" | "warning" | "critical";

interface SeverityIndicatorProps {
  severity: SeverityType;
  showText?: boolean;
  className?: string;
  size?: "sm" | "md";
}

const SEVERITY_CONFIG: Record<
  SeverityType,
  {
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    styles: string;
  }
> = {
  ok: {
    label: "OK",
    icon: CheckCircle2,
    styles: "text-go bg-go/10 border-go/30",
  },
  warning: {
    label: "WARNING",
    icon: AlertTriangle,
    styles: "text-hold bg-hold/10 border-hold/30",
  },
  critical: {
    label: "CRITICAL",
    icon: AlertOctagon,
    styles: "text-nogo bg-nogo/10 border-nogo/30",
  },
};

/**
 * Severity indicator rendering text + icon + colour (Constitution 4.VI).
 * Never conveys state by colour alone so it remains legible in black and white.
 */
export function SeverityIndicator({
  severity,
  showText = true,
  className = "",
  size = "sm",
}: SeverityIndicatorProps) {
  const config = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.warning;
  const Icon = config.icon;

  const sizeStyles =
    size === "sm"
      ? "text-xs px-2 py-0.5 gap-1.5 font-medium"
      : "text-sm px-2.5 py-1 gap-2 font-semibold";
  const iconSize = size === "sm" ? "h-3.5 w-3.5" : "h-4 w-4";

  return (
    <span
      data-testid={`severity-indicator-${severity}`}
      className={`inline-flex items-center border rounded font-mono select-none ${config.styles} ${sizeStyles} ${className}`}
    >
      <Icon className={`${iconSize} shrink-0`} aria-hidden="true" />
      {showText && <span>{config.label}</span>}
    </span>
  );
}
