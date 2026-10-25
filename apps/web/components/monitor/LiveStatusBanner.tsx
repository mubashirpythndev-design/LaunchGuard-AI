"use client";

import React, { useMemo } from "react";
import { useMonitorStore, type ZoneStatus } from "@/stores/monitor-store";
import { ShieldCheck, AlertTriangle, AlertOctagon, WifiOff, Clock } from "lucide-react";
import { AnimatedList } from "@/components/react-bits/AnimatedList";

const STATUS_CONFIG: Record<
  ZoneStatus,
  {
    label: string;
    sublabel: string;
    icon: React.ComponentType<{ className?: string }>;
    testId: string;
    containerClass: string;
    badgeClass: string;
    iconClass: string;
  }
> = {
  CLEAR: {
    label: "CLEAR",
    sublabel: "No personnel inside exclusion zone",
    icon: ShieldCheck,
    testId: "status-icon-clear",
    containerClass: "border-go bg-go/10 text-foreground",
    badgeClass: "bg-go text-primary-foreground",
    iconClass: "text-go",
  },
  WARNING: {
    label: "WARNING",
    sublabel: "Proximity or advisory detected",
    icon: AlertTriangle,
    testId: "status-icon-warning",
    containerClass: "border-hold bg-hold/10 text-foreground",
    badgeClass: "bg-hold text-primary-foreground",
    iconClass: "text-hold",
  },
  DANGER: {
    label: "DANGER",
    sublabel: "Personnel intrusion detected inside exclusion zone",
    icon: AlertOctagon,
    testId: "status-icon-danger",
    containerClass: "border-destructive bg-destructive/10 text-foreground",
    badgeClass: "bg-destructive text-primary-foreground",
    iconClass: "text-destructive",
  },
};

export function LiveStatusBanner({ className = "" }: { className?: string }) {
  const { liveStatus, isStale, processingMs, fps, logs } = useMonitorStore();

  const config = STATUS_CONFIG[liveStatus] || STATUS_CONFIG.CLEAR;
  const IconComponent = config.icon;

  // Filter logs strictly for status transitions (UX-003, Constitution 2.I)
  const statusTransitions = useMemo(() => {
    const transitions: { at: string; from: string; to: string }[] = [];
    for (let i = 0; i < logs.length; i++) {
      const current = logs[i];
      const prev = logs[i + 1];
      if (prev && prev.zone_status !== current.zone_status) {
        transitions.push({
          at: current.at,
          from: prev.zone_status,
          to: current.zone_status,
        });
      }
    }
    return transitions.slice(0, 10);
  }, [logs]);

  return (
    <div className={`flex flex-col gap-3 ${className}`}>
      {/* Primary Status Banner */}
      <div
        role="status"
        aria-live={liveStatus === "DANGER" ? "assertive" : "polite"}
        data-testid="live-status-banner"
        className={`flex items-center justify-between p-4 rounded-md border ${config.containerClass} transition-colors`}
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-md bg-card border border-border shrink-0">
            <IconComponent
              className={`w-7 h-7 ${config.iconClass}`}
              data-testid={config.testId}
            />
          </div>

          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span
                data-testid="status-label"
                className="text-xl font-bold tracking-tight uppercase"
              >
                {config.label}
              </span>
              {isStale && (
                <span
                  data-testid="stale-indicator"
                  className="flex items-center gap-1 px-2 py-0.5 rounded-md border border-border bg-secondary text-[11px] font-mono text-muted-foreground"
                >
                  <WifiOff className="w-3 h-3" />
                  FEED STALE
                </span>
              )}
            </div>
            <span className="text-xs text-muted-foreground">{config.sublabel}</span>
          </div>
        </div>

        {/* Real-time Telemetry (NFR-002: <500ms budget display) */}
        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="flex flex-col items-end">
            <span className="text-muted-foreground text-[10px] uppercase">Latency</span>
            <span
              data-testid="latency-display"
              className={`font-semibold ${processingMs > 500 ? "text-destructive" : "text-foreground"}`}
            >
              {processingMs} ms
            </span>
          </div>

          <div className="flex flex-col items-end border-l border-border pl-4">
            <span className="text-muted-foreground text-[10px] uppercase">Rate</span>
            <span data-testid="fps-display" className="font-semibold text-foreground">
              {fps} FPS
            </span>
          </div>
        </div>
      </div>

      {/* Detection Log: Restricted strictly to Status Transitions */}
      {statusTransitions.length > 0 && (
        <div className="p-3 rounded-md border border-border bg-card">
          <div className="flex items-center gap-1.5 mb-2 text-xs font-medium text-muted-foreground">
            <Clock className="w-3.5 h-3.5" />
            <span>Zone Status Transition History</span>
          </div>

          <AnimatedList className="space-y-1.5" data-testid="transition-log-list">
            {statusTransitions.map((t, idx) => (
              <div
                key={idx}
                data-testid={`transition-item-${idx}`}
                className="flex items-center justify-between py-1 px-2 rounded-md bg-secondary/50 text-xs font-mono"
              >
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">
                    {new Date(t.at).toLocaleTimeString()}
                  </span>
                  <span className="text-foreground">
                    {t.from} &rarr;{" "}
                    <strong
                      className={
                        t.to === "DANGER"
                          ? "text-destructive"
                          : t.to === "WARNING"
                            ? "text-hold"
                            : "text-go"
                      }
                    >
                      {t.to}
                    </strong>
                  </span>
                </div>
              </div>
            ))}
          </AnimatedList>
        </div>
      )}
    </div>
  );
}
