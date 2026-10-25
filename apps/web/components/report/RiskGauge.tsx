"use client";

import React from "react";
import { CheckCircle2, AlertTriangle, AlertOctagon } from "lucide-react";
import { CountUp } from "@/components/react-bits/CountUp";
import { MotionSafe } from "@/components/verdict/MotionSafe";
import { cn } from "@/lib/utils";

export interface RiskGaugeProps {
  score: number;
  className?: string;
  showBar?: boolean;
}

export function RiskGauge({ score, className, showBar = true }: RiskGaugeProps) {
  const clampedScore = Math.max(0, Math.min(100, Math.round(score)));

  let bandLabel = "LOW RISK";
  let bandClass = "text-go bg-go/10 border-go/30";
  let barClass = "bg-go";
  let Icon = CheckCircle2;

  if (clampedScore >= 70) {
    bandLabel = "HIGH RISK";
    bandClass = "text-nogo bg-nogo/10 border-nogo/30";
    barClass = "bg-nogo";
    Icon = AlertOctagon;
  } else if (clampedScore >= 31) {
    bandLabel = "MODERATE RISK";
    bandClass = "text-hold bg-hold/10 border-hold/30";
    barClass = "bg-hold";
    Icon = AlertTriangle;
  }

  return (
    <div
      data-testid="risk-gauge"
      className={cn(
        "p-3.5 border rounded-md border-border bg-card space-y-2.5",
        className
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          Risk Index
        </span>
        <div
          data-testid="risk-band"
          className={cn(
            "inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-mono font-medium border rounded select-none",
            bandClass
          )}
        >
          <Icon className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
          <span>{bandLabel}</span>
        </div>
      </div>

      <div className="flex items-baseline gap-1.5">
        <MotionSafe
          fallback={
            <span className="text-3xl font-mono font-bold tracking-tight num">
              {clampedScore}
            </span>
          }
        >
          <CountUp
            to={clampedScore}
            duration={0.8}
            className="text-3xl font-mono font-bold tracking-tight num"
          />
        </MotionSafe>
        <span className="text-xs font-mono text-muted-foreground">/ 100</span>
      </div>

      {showBar && (
        <div className="space-y-1">
          <div className="w-full h-1.5 rounded bg-secondary overflow-hidden border border-border">
            <div
              className={cn("h-full transition-all duration-500", barClass)}
              style={{ width: `${clampedScore}%` }}
            />
          </div>
          <div className="flex justify-between text-[10px] font-mono text-muted-foreground num">
            <span>0</span>
            <span>30</span>
            <span>70</span>
            <span>100</span>
          </div>
        </div>
      )}
    </div>
  );
}
