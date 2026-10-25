"use client";

import React, { useState, useCallback, useEffect } from "react";
import Link from "next/link";
import { ArrowLeft, RotateCcw, AlertCircle, Loader2, FileSearch, FileText } from "lucide-react";
import type {
  CreateRunResponse,
  EventMessageResponse,
  FindingSchema,
  RunDetailResponse,
} from "@/lib/schemas";
import { Uploader } from "@/components/inspection/Uploader";
import { AnnotatedViewer } from "@/components/inspection/AnnotatedViewer";
import { FindingList } from "@/components/inspection/FindingList";
import { VerdictBadge, type VerdictType } from "@/components/verdict/VerdictBadge";
import { RiskGauge } from "@/components/report/RiskGauge";
import { Disclaimer } from "@/components/verdict/Disclaimer";
import { DemoScenarioMenu } from "@/components/demo/DemoScenarioMenu";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MultiAngleInspection } from "@/components/inspection/MultiAngleInspection";
import { decisionReasonMessages } from "@/lib/sse";

export default function InspectPage() {
  const [inspectionMode, setInspectionMode] = useState("multi");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [isInspecting, setIsInspecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [verdict, setVerdict] = useState<VerdictType | null>(null);
  const [riskScore, setRiskScore] = useState<number | null>(null);
  const [findings, setFindings] = useState<FindingSchema[]>([]);
  const [reasons, setReasons] = useState<string[]>([]);
  const [selectedCheckId, setSelectedCheckId] = useState<string | null>(null);

  useEffect(
    () => () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    },
    [previewUrl],
  );

  const handleFileSelect = useCallback(async (file: File) => {
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setError(null);
    setIsInspecting(true);
    setVerdict(null);
    setRiskScore(null);
    setFindings([]);
    setReasons([]);
    setSelectedCheckId(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch("/api/inspections", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        const message =
          errData?.error?.message ||
          errData?.detail ||
          "Inspection processing failed on the server.";
        throw new Error(message);
      }

      const data: CreateRunResponse = await res.json();
      setRunId(data.run_id);

      // Fetch run details for verdict and risk score
      const runRes = await fetch(`/api/runs/${data.run_id}`);
      if (runRes.ok) {
        const runDetail: RunDetailResponse = await runRes.json();
        if (runDetail.verdict) {
          setVerdict(runDetail.verdict as VerdictType);
        }
        if (runDetail.risk_score !== null && runDetail.risk_score !== undefined) {
          setRiskScore(runDetail.risk_score);
        }
      }

      // Fetch detected findings
      const findingsRes = await fetch(`/api/runs/${data.run_id}/findings`);
      if (findingsRes.ok) {
        const findingsData: FindingSchema[] = await findingsRes.json();
        setFindings(findingsData);
      }

      // Fetch run events to extract deterministic decision reasons
      const eventsRes = await fetch(`/api/runs/${data.run_id}/events`);
      if (eventsRes.ok) {
        const eventsData: EventMessageResponse[] = await eventsRes.json();
        const completedEvent = eventsData.find((e) => e.event_type === "run.completed");
        if (completedEvent?.payload && Array.isArray(completedEvent.payload.reasons)) {
          setReasons(decisionReasonMessages(completedEvent.payload.reasons));
        }
      }
    } catch (err: unknown) {
      setError((err as Error).message || "An unexpected error occurred during inspection.");
    } finally {
      setIsInspecting(false);
    }
  }, []);

  const handleReset = useCallback(() => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setRunId(null);
    setIsInspecting(false);
    setError(null);
    setVerdict(null);
    setRiskScore(null);
    setFindings([]);
    setReasons([]);
    setSelectedCheckId(null);
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      {/* Slim Operational Top Bar */}
      <header className="border-b border-border bg-card/60 px-6 py-3 shrink-0">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors font-medium"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Console home</span>
            </Link>
            <span className="text-border">|</span>
            <div className="flex items-center gap-2">
              <FileSearch className="w-4 h-4 text-steel" />
              <h1 className="text-sm font-semibold tracking-tight text-foreground">
                Pre-launch inspection
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {inspectionMode === "single" && runId && (
              <>
                <span className="text-xs font-mono text-muted-foreground">
                  Run ID: <span className="text-foreground">{runId.slice(0, 8)}</span>
                </span>
                <Button
                  asChild
                  variant="outline"
                  size="sm"
                  className="h-7 px-2.5 text-xs gap-1.5 border-zinc-700 hover:bg-zinc-800"
                >
                  <Link href={`/report/${runId}`} data-testid="view-report-link">
                    <FileText className="w-3 h-3" />
                    <span>View report</span>
                  </Link>
                </Button>
              </>
            )}
            {inspectionMode === "single" && selectedFile && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleReset}
                disabled={isInspecting}
                className="h-7 px-2.5 text-xs gap-1.5"
              >
                <RotateCcw className="w-3 h-3" />
                <span>New inspection</span>
              </Button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full space-y-6">
        <aside
          aria-label="Inspection applicability"
          className="rounded-md border border-border bg-card p-4 text-sm text-muted-foreground"
        >
          <p className="font-medium text-foreground">Image applicability and limits</p>
          <p className="mt-1">
            Use a clear, upright side view with the nose, body and both fins visible. Unverified
            geometry produces a degraded warning, not a defect diagnosis. Surface checks sample the
            visible body; seams, paint and shadows can resemble damage. Use the golden-reference
            comparison and manual inspection to investigate anomalies. This geometry check is not a
            trained rocket classifier or a complete parts inspection.
          </p>
        </aside>
        <Tabs value={inspectionMode} onValueChange={setInspectionMode}>
          <TabsList>
            <TabsTrigger value="multi">Four-angle inspection</TabsTrigger>
            <TabsTrigger value="single" disabled={isInspecting}>
              Single image / Demo
            </TabsTrigger>
          </TabsList>
        </Tabs>
        <div hidden={inspectionMode !== "multi"}>
          <MultiAngleInspection />
        </div>
        {inspectionMode === "single" && (
          <>
            {error && (
              <div
                role="alert"
                className="flex items-center gap-2.5 p-3 text-xs border rounded-md border-destructive/40 bg-destructive/10 text-destructive font-mono"
              >
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {!selectedFile ? (
              /* Step 1: Upload state */
              <div className="max-w-2xl mx-auto py-10 space-y-6">
                <div className="text-center space-y-1.5">
                  <h2 className="text-lg font-semibold tracking-tight text-foreground">
                    Launch vehicle inspection
                  </h2>
                  <p className="text-xs text-muted-foreground">
                    Upload high-resolution rocket imagery for automated fuselage skin and fin
                    alignment evaluation.
                  </p>
                </div>

                <Uploader onFileSelect={handleFileSelect} />

                {/* Offline Demo Scenarios Menu (FR-034, T134) */}
                <DemoScenarioMenu />
              </div>
            ) : (
              /* Step 2: Inspection Evaluation Console */
              <div className="space-y-6">
                {/* Top Summary Banner */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-stretch">
                  {/* Verdict Card */}
                  <Card className="p-4 border border-border bg-card flex flex-col justify-between space-y-2">
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Launch Safety Verdict
                    </span>
                    <div className="py-1">
                      {isInspecting ? (
                        <div className="flex items-center gap-2 text-muted-foreground text-xs font-mono">
                          <Loader2 className="w-4 h-4 animate-spin text-steel" />
                          <span>Evaluating subsystems...</span>
                        </div>
                      ) : verdict ? (
                        <VerdictBadge verdict={verdict} size="lg" />
                      ) : (
                        <span className="text-xs font-mono text-muted-foreground">Pending</span>
                      )}
                    </div>
                    <div className="text-[11px] font-mono text-muted-foreground pt-1 border-t border-border">
                      Rule engine deterministic verdict
                    </div>
                  </Card>

                  {/* Risk Gauge */}
                  <RiskGauge score={riskScore ?? 0} />

                  {/* Inspection Metrics Card */}
                  <Card className="p-4 border border-border bg-card flex flex-col justify-between space-y-2">
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Inspection checks
                    </span>
                    <div className="grid grid-cols-2 gap-2 py-1 font-mono text-xs">
                      <div className="flex flex-col">
                        <span className="text-muted-foreground text-[11px]">Findings</span>
                        <span className="text-base font-semibold num text-foreground">
                          {findings.length}
                        </span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-muted-foreground text-[11px]">Status</span>
                        <span className="text-base font-semibold text-steel">
                          {isInspecting
                            ? "Analysing"
                            : findings.length > 0 && findings.every((finding) => finding.degraded)
                              ? "Not evaluated"
                              : findings.some((finding) => finding.degraded)
                                ? "Incomplete"
                                : "Complete"}
                        </span>
                      </div>
                    </div>
                    <div className="text-[11px] font-mono text-muted-foreground pt-1 border-t border-border">
                      Body · Fins · Launchpad area
                    </div>
                  </Card>
                </div>

                {/* Reasons Banner (if present) */}
                {reasons.length > 0 && (
                  <div className="p-3.5 border rounded-md border-hold/40 bg-hold/5 space-y-1.5">
                    <div className="flex items-center gap-2 text-xs font-semibold text-hold font-mono">
                      <AlertCircle className="w-4 h-4 shrink-0" />
                      <span>Decision factors ({reasons.length})</span>
                    </div>
                    <ul className="list-disc list-inside space-y-1 text-xs text-foreground/90 font-mono">
                      {reasons.map((reason, idx) => (
                        <li key={idx} className="leading-snug">
                          {reason}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Split Operational View */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                  {/* Left Pane: Image & Overlays */}
                  <div className="lg:col-span-7 space-y-3">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span className="font-semibold text-foreground">Optical telemetry view</span>
                      <span className="font-mono">Normalized SVG overlay layer</span>
                    </div>

                    <AnnotatedViewer
                      imageUrl={runId ? `/api/runs/${runId}/image` : previewUrl!}
                      findings={findings}
                      showControls={true}
                    />
                  </div>

                  {/* Right Pane: Findings List */}
                  <div className="lg:col-span-5 space-y-3">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span className="font-semibold text-foreground">
                        Subsystem telemetry list
                      </span>
                      <span className="font-mono num">{findings.length} findings</span>
                    </div>

                    <FindingList
                      findings={findings}
                      selectedCheckId={selectedCheckId}
                      onSelectFinding={(f) => setSelectedCheckId(f.check_id)}
                    />
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </main>

      {/* Mandatory Range Safety Disclaimer (Constitution 2.I, 4.VI) */}
      <footer className="sticky bottom-0 z-20 border-t border-border bg-card px-6 py-3 mt-auto shrink-0">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-muted-foreground">
          <Disclaimer />
          <span className="font-mono text-[11px]">System: Offline-first · Rules deterministic</span>
        </div>
      </footer>
    </div>
  );
}
