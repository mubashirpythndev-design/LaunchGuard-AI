import React from "react";

export function CameraGuideHUD({ label }: { label: string }) {
  return (
    <div className="pointer-events-none absolute inset-3" aria-hidden="true">
      <svg viewBox="0 0 100 75" className="h-full w-full text-steel" fill="none">
        <path
          d="M5 16V5h11M84 5h11v11M95 59v11H84M16 70H5V59"
          stroke="currentColor"
          strokeWidth="0.8"
        />
        <path d="M50 5V70M8 37.5H92" stroke="currentColor" strokeWidth="0.35" strokeDasharray="2 3" />
        <path
          d="M50 10 44 21v34l-9 10 10-3h10l10 3-9-10V21L50 10Z"
          stroke="currentColor"
          strokeWidth="0.7"
          strokeDasharray="2 2"
        />
        <circle cx="50" cy="37.5" r="2" stroke="currentColor" strokeWidth="0.6" />
      </svg>
      <span className="absolute bottom-1 left-1/2 -translate-x-1/2 whitespace-nowrap rounded border border-border bg-background/90 px-2 py-1 text-[9px] font-mono uppercase tracking-widest text-muted-foreground">
        Align {label.toLowerCase()} centerline
      </span>
    </div>
  );
}
