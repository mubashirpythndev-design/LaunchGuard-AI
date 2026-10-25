"use client";

import React from "react";
import {
  AlertCircle,
  CheckCircle2,
  Circle,
  Loader2,
  XCircle,
} from "lucide-react";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { cn } from "@/lib/utils";

export interface TimelineStep {
  position: number;
  step_key: string;
  label: string;
  status: string;
  finding_count?: number;
}

interface AgentTimelineProps {
  steps: TimelineStep[];
  currentStepPosition?: number;
  className?: string;
}

export function AgentTimeline({
  steps,
  currentStepPosition,
  className,
}: AgentTimelineProps) {
  const prefersReducedMotion = useReducedMotion();

  const getStepIcon = (status: string) => {
    switch (status) {
      case "passed":
        return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-red-500" />;
      case "running":
        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
      case "blocked":
        return <AlertCircle className="h-4 w-4 text-amber-500" />;
      case "pending":
      default:
        return <Circle className="h-4 w-4 text-zinc-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "passed":
        return (
          <span className="text-xs font-mono font-medium text-emerald-500 uppercase">
            PASSED
          </span>
        );
      case "failed":
        return (
          <span className="text-xs font-mono font-medium text-red-500 uppercase">
            FAILED
          </span>
        );
      case "running":
        return (
          <span className="text-xs font-mono font-medium text-blue-500 uppercase">
            RUNNING
          </span>
        );
      case "blocked":
        return (
          <span className="text-xs font-mono font-medium text-amber-500 uppercase">
            PAUSED
          </span>
        );
      case "pending":
      default:
        return (
          <span className="text-xs font-mono font-medium text-zinc-500 uppercase">
            PENDING
          </span>
        );
    }
  };

  return (
    <div
      className={cn(
        "rounded-md border border-zinc-800 bg-zinc-950 p-4 font-sans",
        className,
      )}
      aria-label="Agent execution checklist"
    >
      <div className="flex items-center justify-between border-b border-zinc-800 pb-3 mb-4">
        <h3 className="text-sm font-semibold text-zinc-200">
          Inspection Checklist
        </h3>
        <span className="text-xs font-mono text-zinc-500">5 STEPS</span>
      </div>

      <div className="space-y-3">
        {steps.map((step) => {
          const isCurrent =
            step.position === currentStepPosition || step.status === "running";

          return (
            <div
              key={step.position}
              className={cn(
                "flex items-center justify-between rounded-md border p-3 transition-colors",
                isCurrent
                  ? "border-blue-500/50 bg-blue-950/20"
                  : "border-zinc-800/80 bg-zinc-900/40",
                !prefersReducedMotion && "duration-200",
              )}
            >
              <div className="flex items-center space-x-3">
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-zinc-900 border border-zinc-700">
                  {getStepIcon(step.status)}
                </div>
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-mono text-zinc-400">
                      STEP {step.position}
                    </span>
                    <span className="text-sm font-medium text-zinc-200">
                      {step.label}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                {(step.finding_count ?? 0) > 0 && (
                  <span className="inline-flex items-center rounded-md border border-zinc-700 bg-zinc-800 px-2 py-0.5 text-xs font-mono text-zinc-300">
                    {step.finding_count}{" "}
                    {step.finding_count === 1 ? "finding" : "findings"}
                  </span>
                )}
                {getStatusBadge(step.status)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
