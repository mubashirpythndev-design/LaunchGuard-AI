"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  FileText,
  Loader2,
  Printer,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Disclaimer } from "@/components/verdict/Disclaimer";
import { VerdictBadge, type VerdictType } from "@/components/verdict/VerdictBadge";
import { RiskGauge } from "@/components/report/RiskGauge";
import type { PublicReportResponse } from "@launchguard/contract";

export default function SharedReportPage() {
  const params = useParams<{ token: string }>();
  const token = params.token;

  const [report, setReport] = useState<PublicReportResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isGone, setIsGone] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadSharedReport() {
      setLoading(true);
      setError(null);
      setIsGone(false);

      try {
        const res = await fetch(`/api/share/${encodeURIComponent(token)}`);
        if (res.status === 410) {
          setIsGone(true);
          return;
        }

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData?.error?.message || "Failed to load shared safety report.");
        }

        const data: PublicReportResponse = await res.json();
        setReport(data);
      } catch (err: unknown) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("An unexpected error occurred.");
        }
      } finally {
        setLoading(false);
      }
    }

    if (token) {
      loadSharedReport();
    }
  }, [token]);

  // Explicit 410 Not Available State (FR-033, T126)
  if (isGone) {
    return (
      <div className="min-h-screen bg-zinc-950 font-sans text-zinc-100 p-4 md:p-8 flex flex-col justify-between">
        <div className="mx-auto max-w-xl text-center py-20 space-y-6">
          <div className="mx-auto h-16 w-16 rounded-full border border-amber-500/50 bg-amber-950/30 flex items-center justify-center text-amber-500">
            <AlertTriangle className="h-8 w-8" />
          </div>

          <div className="space-y-2">
            <span
              data-testid="status-410"
              className="inline-flex items-center rounded border border-amber-800 bg-amber-950/60 px-2.5 py-0.5 text-xs font-mono text-amber-400"
            >
              410 SHARE_NOT_AVAILABLE
            </span>
            <h1 className="text-xl font-bold text-zinc-100">Report No Longer Available</h1>
            <p className="text-xs text-zinc-400 max-w-md mx-auto">
              This shared inspection link has expired or the associated inspection run is no longer
              available on the server.
            </p>
          </div>

          <div>
            <Button
              asChild
              variant="outline"
              size="sm"
              className="border-zinc-800 text-zinc-300 hover:text-zinc-100 font-mono text-xs"
            >
              <Link href="/">
                <ArrowLeft className="mr-1.5 h-3.5 w-3.5" />
                <span>Return to Console</span>
              </Link>
            </Button>
          </div>
        </div>

        <footer className="border-t border-zinc-800/80 pt-4 flex justify-between items-center text-xs">
          <Disclaimer />
          <span className="font-mono text-zinc-500">Read-Only Capability</span>
        </footer>
      </div>
    );
  }

  const displayChecklist = report?.checklist ?? [];
  const displayReasons = report?.reasons ?? [];
  const displayRecommendedActions = report?.recommended_actions ?? [];

  return (
    <div className="min-h-screen bg-zinc-950 font-sans text-zinc-100 p-4 md:p-8">
      <div className="mx-auto max-w-5xl space-y-6">
        {/* Top Header Controls (Print only - NO run controls or other run listings) */}
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-zinc-800 pb-4">
          <div className="flex items-center space-x-3">
            <div className="h-8 w-8 rounded border border-zinc-800 bg-zinc-900 flex items-center justify-center text-zinc-400">
              <FileText className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xs font-mono text-zinc-500 uppercase">SHARED REPORT</span>
                <span className="inline-flex items-center rounded border border-blue-900 bg-blue-950/60 px-2 py-0.5 text-[10px] font-mono text-blue-300">
                  READ-ONLY
                </span>
              </div>
              <h1 className="text-lg font-bold text-zinc-100">Range Safety Inspection Report</h1>
            </div>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => window.print()}
            className="border-zinc-800 text-zinc-300 hover:text-zinc-100 font-mono text-xs"
          >
            <Printer className="mr-1.5 h-3.5 w-3.5" />
            <span>Print Report</span>
          </Button>
        </div>

        {/* Universal Mandated Disclaimer */}
        <div className="flex justify-between items-center bg-zinc-900/50 border border-zinc-800/80 rounded-md px-3.5 py-2">
          <Disclaimer />
          <span className="text-xs font-mono text-zinc-500">
            {report?.generated_at ? new Date(report.generated_at).toLocaleString() : ""}
          </span>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center p-20 space-y-3">
            <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
            <span className="text-xs font-mono text-zinc-500">Loading shared report document...</span>
          </div>
        ) : error ? (
          <div
            role="alert"
            className="p-8 text-center text-xs font-mono border rounded-md border-red-800/60 bg-red-950/20 text-red-400"
          >
            {error}
          </div>
        ) : report ? (
          <div className="space-y-6">
            {/* Verdict and Risk Summary Card */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-stretch">
              <Card className="p-4 border border-zinc-800 bg-zinc-900/50 flex flex-col justify-between space-y-2">
                <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                  Deterministic Verdict
                </span>
                <div className="py-2">
                  <VerdictBadge verdict={report.verdict as VerdictType} size="lg" />
                </div>
                <div className="text-[11px] font-mono text-zinc-500 pt-1 border-t border-zinc-800">
                  Computed by rule engine
                </div>
              </Card>

              <RiskGauge score={report.risk_score} />

              <Card className="p-4 border border-zinc-800 bg-zinc-900/50 flex flex-col justify-between space-y-2">
                <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                  Checklist Steps Audited
                </span>
                <div className="py-2">
                  <span className="text-2xl font-mono font-bold text-zinc-100">
                    {displayChecklist.filter((s) => s.status === "passed").length} /{" "}
                    {displayChecklist.length}
                  </span>
                  <span className="text-xs font-mono text-zinc-400 ml-2">Passed</span>
                </div>
                <div className="text-[11px] font-mono text-zinc-500 pt-1 border-t border-zinc-800">
                  Full 5-phase inspection
                </div>
              </Card>
            </div>

            {/* Decision Factors / Reasons */}
            {displayReasons.length > 0 && (
              <div className="rounded-md border border-amber-800/60 bg-amber-950/20 p-4 space-y-2">
                <div className="flex items-center space-x-2 text-xs font-semibold text-amber-400 font-mono">
                  <AlertCircle className="h-4 w-4" />
                  <span>Decision Factors ({displayReasons.length})</span>
                </div>
                <ul className="space-y-1.5 pl-5 list-disc text-xs text-zinc-300 font-mono">
                  {displayReasons.map((r, idx) => (
                    <li key={idx}>
                      <span className="font-semibold text-zinc-200">[{r.severity.toUpperCase()}]</span>{" "}
                      {r.message}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Recommended Safety Actions */}
            {displayRecommendedActions.length > 0 && (
              <div className="rounded-md border border-zinc-800 bg-zinc-900/40 p-4 space-y-2">
                <div className="flex items-center space-x-2 text-xs font-semibold text-zinc-300 font-mono">
                  <CheckCircle2 className="h-4 w-4 text-blue-400" />
                  <span>Mandated Actions</span>
                </div>
                <ul className="space-y-1.5 pl-5 list-disc text-xs text-zinc-300 font-mono">
                  {displayRecommendedActions.map((act, idx) => (
                    <li key={idx}>{act.action}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* AI Narrative Context Card */}
            <div className="rounded-md border border-zinc-800 bg-zinc-900/30 p-5 space-y-3">
              <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
                <div className="flex items-center space-x-2 text-xs font-semibold text-zinc-200">
                  <Sparkles className="h-4 w-4 text-purple-400" />
                  <span>Range Safety Officer Summary</span>
                </div>
                <span className="text-[11px] font-mono text-zinc-500">
                  {report.narrative.model || "Template Fallback"}
                </span>
              </div>
              <p className="text-xs text-zinc-300 leading-relaxed font-sans">
                {report.narrative.text ||
                  "Detailed explanation unavailable. Deterministic rule evaluation preserved."}
              </p>
              <div className="pt-2 border-t border-zinc-800/60 flex items-center justify-between text-[11px] font-mono text-zinc-500">
                <span>Verdict computed by rules; explanation by AI</span>
                <span>Status: {report.narrative.status.toUpperCase()}</span>
              </div>
            </div>

            {/* Checklist Execution Summary */}
            <div className="rounded-md border border-zinc-800 bg-zinc-900/30 p-4 space-y-3">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Audited Checklist Phases
              </h2>
              <div className="space-y-2">
                {displayChecklist.map((step) => (
                  <div
                    key={step.position}
                    className="flex items-center justify-between border-b border-zinc-800/40 pb-2 text-xs"
                  >
                    <div className="flex items-center space-x-2.5">
                      <span className="font-mono text-zinc-500">{step.position}.</span>
                      <span className="font-medium text-zinc-200">{step.label}</span>
                    </div>
                    <span
                      className={`font-mono text-[11px] uppercase px-2 py-0.5 rounded border ${
                        step.status === "passed"
                          ? "border-emerald-800 bg-emerald-950/40 text-emerald-400"
                          : step.status === "failed"
                          ? "border-red-800 bg-red-950/40 text-red-400"
                          : "border-zinc-800 bg-zinc-900 text-zinc-400"
                      }`}
                    >
                      {step.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
