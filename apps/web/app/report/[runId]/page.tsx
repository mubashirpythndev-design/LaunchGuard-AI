"use client";

import React, { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle2,
  FileText,
  Printer,
  Share2,
  Sparkles,
  AlertTriangle,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Disclaimer } from "@/components/verdict/Disclaimer";
import { VerdictBadge } from "@/components/verdict/VerdictBadge";
import { RiskGauge } from "@/components/report/RiskGauge";
import { AgentTimeline } from "@/components/report/AgentTimeline";
import {
  ManualInputsDialog,
  type ManualInputsFormData,
} from "@/components/report/ManualInputsDialog";
import { useRunStream } from "@/hooks/use-run-stream";
import type { ReportResponse, RunDetailResponse } from "@launchguard/contract";
import { QuadrantResults } from "@/components/inspection/QuadrantResults";

export default function ReportPage() {
  const params = useParams<{ runId: string }>();
  const runId = params.runId;
  const router = useRouter();

  const reportQuery = useQuery({
    queryKey: ["report", runId],
    queryFn: async ({ signal }): Promise<ReportResponse | null> => {
      const res = await fetch(`/api/runs/${encodeURIComponent(runId)}/report`, { signal });
      if (res.ok) return (await res.json()) as ReportResponse;
      if (res.status === 404) {
        const runRes = await fetch(`/api/runs/${encodeURIComponent(runId)}`, { signal });
        if (runRes.ok) {
          const run: RunDetailResponse = await runRes.json();
          if (run.status === "running" || run.status === "paused") return null;
        }
        throw new Error(
          "Report unavailable. This run may not exist, may have failed, or may lack saved results.",
        );
      }
      throw new Error(`Could not load report (HTTP ${res.status}). Please retry.`);
    },
    retry: false,
    refetchInterval: (query) =>
      query.state.error
        ? false
        : query.state.data == null || query.state.data.narrative.status === "pending"
          ? 2000
          : false,
  });
  const reportData = reportQuery.data;
  const streamState = useRunStream(
    runId,
    !reportQuery.error && (!reportData || reportData.narrative.status === "pending"),
  );
  const [dialogOpen, setDialogOpen] = useState(false);
  const [shareToken, setShareToken] = useState<string | null>(null);
  const [sharing, setSharing] = useState(false);
  const [imageFailed, setImageFailed] = useState(false);

  const { refetch } = reportQuery;
  useEffect(() => {
    if (streamState.status === "completed") {
      void refetch();
    }
    if (streamState.status === "paused" && streamState.awaitingInput) {
      setDialogOpen(true);
    }
  }, [streamState.status, streamState.awaitingInput, refetch]);

  const handleManualInputSubmit = async (formData: ManualInputsFormData) => {
    const res = await fetch(`/api/runs/${encodeURIComponent(runId)}/manual-inputs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formData),
    });

    if (!res.ok) {
      const errorData = await res.json();
      throw new Error(errorData.error?.message || "Failed to submit manual inputs.");
    }

    setDialogOpen(false);
  };

  const handleShare = async () => {
    setSharing(true);
    try {
      const res = await fetch(`/api/runs/${encodeURIComponent(runId)}/share`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setShareToken(data.token);
        if (navigator.clipboard) {
          await navigator.clipboard.writeText(`${window.location.origin}/share/${data.token}`);
        }
      }
    } catch (err) {
      console.error("Failed to generate share link:", err);
    } finally {
      setSharing(false);
    }
  };

  const isTerminal = reportData != null;
  const activeVerdict = reportData?.verdict || streamState.verdict;
  const activeRisk = reportData?.risk_score ?? streamState.riskScore ?? 0;
  const activeNarrative = reportData?.narrative || streamState.narrative;
  const displayReasons = reportData?.reasons ?? streamState.reasons ?? [];
  const displaySteps = reportData?.checklist ?? streamState.steps ?? [];
  const recommendedActions = reportData?.recommended_actions ?? [];

  return (
    <div className="min-h-screen bg-zinc-950 font-sans text-zinc-100 p-4 md:p-8">
      <div className="mx-auto max-w-6xl space-y-6">
        {/* Navigation & Header Controls */}
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-zinc-800 pb-4">
          <div className="flex items-center space-x-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push("/inspect")}
              className="border-zinc-800 text-zinc-300 hover:text-zinc-100"
            >
              <ArrowLeft className="mr-1.5 h-3.5 w-3.5" />
              <span>Back</span>
            </Button>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xs font-mono text-zinc-500 uppercase">RUN</span>
                <span className="text-xs font-mono font-medium text-zinc-300">
                  {runId.slice(0, 8)}...
                </span>
                <span className="inline-flex items-center rounded border border-zinc-800 bg-zinc-900 px-2 py-0.5 text-xs font-mono text-zinc-400">
                  {reportData ? "COMPLETED" : streamState.status.toUpperCase()}
                </span>
              </div>
              <h1 className="text-lg font-bold text-zinc-100">Range Safety Inspection Report</h1>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => window.print()}
              className="border-zinc-800 text-zinc-300 hover:text-zinc-100 font-mono text-xs"
            >
              <Printer className="mr-1.5 h-3.5 w-3.5" />
              <span>Print / Export</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleShare}
              disabled={sharing || !isTerminal}
              className="border-zinc-800 text-zinc-300 hover:text-zinc-100 font-mono text-xs"
            >
              <Share2 className="mr-1.5 h-3.5 w-3.5" />
              <span>{shareToken ? "Link Copied" : "Share"}</span>
            </Button>
          </div>
        </div>

        {/* Universal Mandated Disclaimer */}
        <div className="sticky top-0 z-20 flex flex-wrap justify-between items-center gap-2 bg-zinc-950 border border-zinc-800/80 rounded-md px-3.5 py-2">
          <Disclaimer />
          <span className="text-xs font-mono text-zinc-500">
            {reportData?.generated_at ? new Date(reportData.generated_at).toLocaleString() : ""}
          </span>
        </div>

        {reportQuery.error && (
          <div role="alert" className="rounded-md border border-border bg-card p-5 space-y-3">
            <h2 className="font-semibold">Report could not be loaded</h2>
            <p className="text-sm text-muted-foreground">{reportQuery.error.message}</p>
            <Button variant="outline" onClick={() => void refetch()}>
              Retry report
            </Button>
          </div>
        )}
        {/* Live Running / Paused State View */}
        {!isTerminal && !reportQuery.error && (
          <div className="space-y-6">
            <div className="rounded-md border border-zinc-800 bg-zinc-900/40 p-6 text-center space-y-4">
              <div className="flex justify-center">
                {streamState.status === "paused" ? (
                  <div className="h-10 w-10 rounded-full border border-amber-500/50 bg-amber-950/40 flex items-center justify-center text-amber-500">
                    <AlertTriangle className="h-5 w-5" />
                  </div>
                ) : (
                  <div className="h-10 w-10 rounded-full border border-blue-500/50 bg-blue-950/40 flex items-center justify-center text-blue-500">
                    <Loader2 className="h-5 w-5 animate-spin" />
                  </div>
                )}
              </div>
              <div>
                <h2 className="text-base font-semibold text-zinc-200">
                  {streamState.status === "paused"
                    ? "Inspection Paused: Waiting for Manual Range Clearance"
                    : "Automated Inspection in Progress..."}
                </h2>
                <p className="text-xs text-zinc-400 mt-1">
                  {streamState.status === "paused"
                    ? "Range environmental conditions and pad exclusion zone status required."
                    : "Executing deterministic computer vision pipeline and sensor analysis."}
                </p>
              </div>

              {streamState.status === "paused" && (
                <Button onClick={() => setDialogOpen(true)} className="font-mono text-xs uppercase">
                  Enter Manual Inputs
                </Button>
              )}
            </div>

            <AgentTimeline steps={streamState.steps} />
          </div>
        )}

        {/* Terminal Completed Report View */}
        {isTerminal && (
          <div className="space-y-6">
            {/* Top Score and Verdict Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="rounded-md border border-zinc-800 bg-zinc-900/60 p-4 space-y-2 flex flex-col justify-between">
                <div>
                  <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                    Launch Decision
                  </span>
                  <div className="mt-2">
                    {activeVerdict && <VerdictBadge verdict={activeVerdict} size="lg" />}
                  </div>
                </div>
                <p className="text-xs font-mono text-zinc-500 mt-2">
                  Verdict computed by rules; explanation by AI
                </p>
              </div>

              <RiskGauge score={activeRisk} className="bg-zinc-900/60" />

              <div className="rounded-md border border-zinc-800 bg-zinc-900/60 p-4 space-y-2 flex flex-col justify-between">
                <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                  Checklist Health
                </span>
                <div className="flex items-center space-x-2 text-2xl font-bold font-mono text-zinc-100">
                  <CheckCircle2 className="h-6 w-6 text-emerald-500" />
                  <span>{displaySteps.filter((s) => s.status === "passed").length} / 5 PASSED</span>
                </div>
                <p className="text-xs text-zinc-500 font-mono">
                  Review incomplete or flagged checks before launch.
                </p>
              </div>
            </div>

            {/* AI Executive Summary Narrative Card */}
            <div className="rounded-md border border-zinc-800 bg-zinc-900/60 p-4 space-y-2.5">
              <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
                <div className="flex items-center space-x-2">
                  <Sparkles className="h-4 w-4 text-blue-400" />
                  <h3 className="text-sm font-semibold text-zinc-200">
                    AI Safety Officer Executive Summary
                  </h3>
                </div>
                {activeNarrative?.status === "available" && activeNarrative.model && (
                  <span className="inline-flex items-center rounded border border-zinc-800 bg-zinc-900 px-2 py-0.5 text-xs font-mono text-zinc-400">
                    {activeNarrative.model}
                  </span>
                )}
              </div>

              {activeNarrative?.status === "available" && activeNarrative.text ? (
                <p className="text-sm text-zinc-300 leading-relaxed whitespace-pre-line">
                  {activeNarrative.text}
                </p>
              ) : activeNarrative?.status === "unavailable" ? (
                <div className="rounded border border-amber-900/40 bg-amber-950/20 p-3 text-xs text-amber-300">
                  Narrative unavailable — verdict unaffected. The deterministic verdict and findings
                  remain available.
                </div>
              ) : (
                <div className="flex items-center space-x-2 text-xs text-zinc-400 py-2">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span>Synthesizing safety narrative...</span>
                </div>
              )}
            </div>

            {/* Split Details: Timeline & Findings / Annotated Image */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Left Column: Timeline & Reasons */}
              <div className="space-y-6">
                <AgentTimeline steps={displaySteps} />

                {/* Ordered Reasons */}
                <div className="rounded-md border border-zinc-800 bg-zinc-900/60 p-4 space-y-3">
                  <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
                    <h3 className="text-sm font-semibold text-zinc-200">
                      Evaluated Findings & Reasons
                    </h3>
                    <span className="text-xs font-mono text-zinc-500">
                      {displayReasons.length} ITEMS
                    </span>
                  </div>

                  <div className="space-y-2.5">
                    {displayReasons.map((reason, idx) => (
                      <div
                        key={idx}
                        className="rounded border border-zinc-800 bg-zinc-900/40 p-3 text-xs space-y-1.5"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-zinc-400">{reason.check_id}</span>
                          <span
                            className={`font-mono uppercase font-medium ${
                              reason.severity === "critical"
                                ? "text-red-500"
                                : reason.severity === "warning"
                                  ? "text-amber-500"
                                  : "text-emerald-500"
                            }`}
                          >
                            {reason.severity}
                          </span>
                        </div>
                        <p className="text-zinc-200">{reason.message}</p>
                        {reason.ambiguous && (
                          <p className="text-zinc-400 text-xs italic">
                            Measurement sits within sensor error margin of safety threshold.
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Recommended Actions */}
                {recommendedActions.length > 0 && (
                  <div className="rounded-md border border-zinc-800 bg-zinc-900/60 p-4 space-y-3">
                    <div className="flex items-center space-x-2 border-b border-zinc-800 pb-2">
                      <FileText className="h-4 w-4 text-emerald-400" />
                      <h3 className="text-sm font-semibold text-zinc-200">
                        Recommended Corrective Actions
                      </h3>
                    </div>
                    <ul className="space-y-2 text-xs text-zinc-300">
                      {recommendedActions.map((act, idx) => (
                        <li
                          key={idx}
                          className="flex items-start space-x-2 rounded border border-zinc-800 bg-zinc-900/30 p-2.5"
                        >
                          <span className="font-mono font-semibold text-emerald-400 shrink-0">
                            [{act.check_id}]
                          </span>
                          <span>{act.action}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Right Column: Annotated Composite Image */}
              <div className="space-y-4">
                {reportData?.quadrants?.length ? (
                  <QuadrantResults
                    images={reportData.quadrants}
                    findings={reportData.findings}
                    compact
                  />
                ) : (
                  <div className="rounded-md border border-zinc-800 bg-zinc-900/60 p-4 space-y-3">
                    <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
                      <h3 className="text-sm font-semibold text-zinc-200">
                        Annotated Composite Verification
                      </h3>
                      <span className="text-xs font-mono text-zinc-500">SERVER-RENDERED</span>
                    </div>

                    <div className="aspect-video w-full rounded border border-zinc-800 bg-zinc-950 overflow-hidden flex items-center justify-center">
                      {imageFailed ? (
                        <div className="flex flex-col items-center justify-center p-6 text-zinc-500 text-xs font-mono space-y-1">
                          <FileText className="h-6 w-6 text-zinc-600" />
                          <span>VISUAL TELEMETRY ARCHIVE NOT AVAILABLE</span>
                          <span className="text-[11px] text-zinc-600">
                            Simulated test run without image artifact
                          </span>
                        </div>
                      ) : (
                        /* eslint-disable-next-line @next/next/no-img-element */
                        <img
                          src={`/api/runs/${encodeURIComponent(runId)}/annotated.png`}
                          alt="Annotated Inspection Composite"
                          className="h-full w-full object-contain"
                          onError={(e) => {
                            const target = e.currentTarget;
                            if (!target.dataset.fallback) {
                              target.dataset.fallback = "true";
                              target.src = `/api/runs/${encodeURIComponent(runId)}/image`;
                            } else {
                              target.onerror = null;
                              setImageFailed(true);
                            }
                          }}
                        />
                      )}
                    </div>

                    <p className="text-xs text-zinc-500">
                      Inspection overlay highlighting detected defects, danger exclusion zone
                      containment, and propellant cue indicators.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Modal Manual Input Dialog */}
        <ManualInputsDialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          runId={runId}
          awaitingInput={streamState.awaitingInput}
          onSubmit={handleManualInputSubmit}
        />
      </div>
    </div>
  );
}
