import React from "react";
import { ShieldAlert } from "lucide-react";

export const MANDATED_DISCLAIMER_TEXT =
  "Decision-support tool. Not a replacement for certified range safety.";

interface DisclaimerProps {
  className?: string;
  showIcon?: boolean;
}

/**
 * Universal compliance disclaimer required across all 5 views (Constitution 1.II, FR-037).
 */
export function Disclaimer({ className = "", showIcon = true }: DisclaimerProps) {
  return (
    <div
      data-testid="disclaimer"
      className={`inline-flex items-center gap-2 text-xs text-muted-foreground select-none ${className}`}
    >
      {showIcon && <ShieldAlert className="h-3.5 w-3.5 shrink-0 text-steel" aria-hidden="true" />}
      <span>{MANDATED_DISCLAIMER_TEXT}</span>
    </div>
  );
}
