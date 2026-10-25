"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Clock,
  FileSearch,
  History,
  MonitorPlay,
  ShieldCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Disclaimer } from "@/components/verdict/Disclaimer";
import { VerdictBadge, type VerdictType } from "@/components/verdict/VerdictBadge";
import { RiskGauge } from "@/components/report/RiskGauge";
import { DemoScenarioMenu } from "@/components/demo/DemoScenarioMenu";
import type { LatestRunSummaryResponse, RunListItem } from "@launchguard/contract";

export default function DashboardPage() {
  const [latestSummary, setLatestSummary] = useState<LatestRunSummaryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function fetchLatestSummary() {
      setLoading(true);
      try {
        const res = await fetch("/api/runs/latest");
        if (res.ok) {
          const data: LatestRunSummaryResponse = await res.json();
          setLatestSummary(data);
        }
      } catch (err: unknown) {
        console.error("Failed to load latest run summary:", err);
      } finally {
        setLoading(false);
      }
    }

    fetchLatestSummary();
  }, []);

  const latestRun = latestSummary?.latest_runs?.[0];
  const checklist = latestSummary?.checklist ?? [];

  return (
    <div className="min-h-screen bg-zinc-950 font-sans text-zinc-100 p-4 md:p-8">
      <div className="mx-auto max-w-6xl space-y-8">
        {/* Dashboard Header Bar */}
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-zinc-800 pb-5">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-xs font-mono uppercase tracking-wider text-zinc-400">
                Range Safety Mission Console
              </span>
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-zinc-100">
              LaunchGuard AI
            </h1>
            <p className="text-xs text-zinc-400">
              Deterministic pre-flight optical inspection and hazard detection
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <Button
              asChild
              variant="outline"
              size="sm"
              className="border-zinc-800 text-zinc-300 hover:text-zinc-100 font-mono text-xs"
            >
              <Link href="/history">
                <History className="mr-1.5 h-3.5 w-3.5" />
                <span>Audit History</span>
              </Link>
            </Button>
            <Button
              asChild
              size="sm"
              className="bg-blue-600 hover:bg-blue-500 font-mono text-xs uppercase"
            >
              <Link href="/inspect">
                <span>Start Inspection</span>
                <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
              </Link>
            </Button>
          </div>
        </header>

        {/* Universal Mandated Disclaimer */}
        <div className="flex justify-between items-center bg-zinc-900/50 border border-zinc-800/80 rounded-md px-3.5 py-2">
          <Disclaimer />
          <span className="text-xs font-mono text-zinc-500">Decision-Support</span>
        </div>

        {/* Demo Scenario Quick Access */}
        <DemoScenarioMenu />

        {/* Quick Action Navigation Tiles */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            href="/inspect"
            className="group p-5 rounded-md border border-zinc-800 bg-zinc-900/40 hover:bg-zinc-900/70 hover:border-zinc-700 transition-all flex flex-col justify-between space-y-4"
          >
            <div className="space-y-2">
              <div className="h-9 w-9 rounded-md border border-zinc-800 bg-zinc-900 flex items-center justify-center text-zinc-300 group-hover:text-blue-400 group-hover:border-blue-900/50 transition-colors">
                <FileSearch className="h-5 w-5" />
              </div>
              <h2 className="text-sm font-semibold text-zinc-100 group-hover:text-blue-300 transition-colors">
                Pre-Launch Inspection
              </h2>
              <p className="text-xs text-zinc-400 leading-relaxed">
                Upload launch vehicle optical imagery to evaluate fuselage skin defects and fin
                alignment against FAA safety margins.
              </p>
            </div>
            <div className="flex items-center text-xs font-mono text-zinc-500 group-hover:text-zinc-300">
              <span>Execute pipeline</span>
              <ArrowRight className="ml-1.5 h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
            </div>
          </Link>

          <Link
            href="/monitor"
            className="group p-5 rounded-md border border-zinc-800 bg-zinc-900/40 hover:bg-zinc-900/70 hover:border-zinc-700 transition-all flex flex-col justify-between space-y-4"
          >
            <div className="space-y-2">
              <div className="h-9 w-9 rounded-md border border-zinc-800 bg-zinc-900 flex items-center justify-center text-zinc-300 group-hover:text-amber-400 group-hover:border-amber-900/50 transition-colors">
                <MonitorPlay className="h-5 w-5" />
              </div>
              <h2 className="text-sm font-semibold text-zinc-100 group-hover:text-amber-300 transition-colors">
                Launchpad Danger Zone Monitor
              </h2>
              <p className="text-xs text-zinc-400 leading-relaxed">
                Draw exclusion zone polygons over live feeds to detect unauthorized personnel and
                optical hazard cues in under 500 ms.
              </p>
            </div>
            <div className="flex items-center text-xs font-mono text-zinc-500 group-hover:text-zinc-300">
              <span>Open live monitor</span>
              <ArrowRight className="ml-1.5 h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
            </div>
          </Link>

          <Link
            href="/history"
            className="group p-5 rounded-md border border-zinc-800 bg-zinc-900/40 hover:bg-zinc-900/70 hover:border-zinc-700 transition-all flex flex-col justify-between space-y-4"
          >
            <div className="space-y-2">
              <div className="h-9 w-9 rounded-md border border-zinc-800 bg-zinc-900 flex items-center justify-center text-zinc-300 group-hover:text-emerald-400 group-hover:border-emerald-900/50 transition-colors">
                <History className="h-5 w-5" />
              </div>
              <h2 className="text-sm font-semibold text-zinc-100 group-hover:text-emerald-300 transition-colors">
                Mission Audit History
              </h2>
              <p className="text-xs text-zinc-400 leading-relaxed">
                Filter and inspect all completed range evaluations, verified decision factors, and
                sharable capability reports.
              </p>
            </div>
            <div className="flex items-center text-xs font-mono text-zinc-500 group-hover:text-zinc-300">
              <span>View past audits</span>
              <ArrowRight className="ml-1.5 h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
            </div>
          </Link>
        </section>

        {/* Latest Mission Status Overview */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <ShieldCheck className="h-4 w-4 text-zinc-400" />
              <h2 className="text-sm font-semibold tracking-tight uppercase text-zinc-300 font-mono">
                Latest Mission Safety Assessment
              </h2>
            </div>
            {latestRun && (
              <span className="text-xs font-mono text-zinc-500">
                Run ID: {latestRun.run_id.slice(0, 8)}...
              </span>
            )}
          </div>

          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="h-28 rounded-md bg-zinc-900/60 border border-zinc-800 animate-pulse" />
              <div className="h-28 rounded-md bg-zinc-900/60 border border-zinc-800 animate-pulse" />
              <div className="h-28 rounded-md bg-zinc-900/60 border border-zinc-800 animate-pulse" />
            </div>
          ) : latestSummary?.verdict ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-stretch">
                {/* Latest Verdict Card */}
                <Card className="p-4 border border-zinc-800 bg-zinc-900/50 flex flex-col justify-between space-y-2">
                  <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                    Latest Verdict
                  </span>
                  <div className="py-2">
                    <VerdictBadge verdict={latestSummary.verdict as VerdictType} size="lg" />
                  </div>
                  <div className="text-[11px] font-mono text-zinc-500 pt-1 border-t border-zinc-800">
                    Deterministic rule evaluation
                  </div>
                </Card>

                {/* Risk Gauge */}
                <RiskGauge score={latestSummary.risk_score ?? 0} />

                {/* Checklist Summary Card */}
                <Card className="p-4 border border-zinc-800 bg-zinc-900/50 flex flex-col justify-between space-y-2">
                  <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                    Checklist Execution
                  </span>
                  <div className="py-2">
                    <span className="text-2xl font-mono font-bold text-zinc-100">
                      {checklist.filter((s) => s.status === "passed").length} /{" "}
                      {checklist.length}
                    </span>
                    <span className="text-xs font-mono text-zinc-400 ml-2">Phases Passed</span>
                  </div>
                  <div className="text-[11px] font-mono text-zinc-500 pt-1 border-t border-zinc-800">
                    {latestRun ? (
                      <Link
                        href={`/report/${latestRun.run_id}`}
                        className="text-blue-400 hover:underline flex items-center gap-1"
                      >
                        <span>Open full report</span>
                        <ArrowRight className="h-3 w-3" />
                      </Link>
                    ) : (
                      "All 5 phases evaluated"
                    )}
                  </div>
                </Card>
              </div>

              {/* Checklist Step Badges */}
              {checklist.length > 0 && (
                <div className="rounded-md border border-zinc-800 bg-zinc-900/30 p-3.5">
                  <div className="grid grid-cols-1 sm:grid-cols-5 gap-2 text-xs">
                    {checklist.map((step) => (
                      <div
                        key={step.position}
                        className="rounded border border-zinc-800/80 bg-zinc-900/80 p-2 space-y-1"
                      >
                        <div className="flex items-center justify-between text-[11px] font-mono text-zinc-400">
                          <span>STEP 0{step.position}</span>
                          <span
                            className={`uppercase font-semibold ${
                              step.status === "passed"
                                ? "text-emerald-400"
                                : step.status === "failed"
                                ? "text-red-400"
                                : "text-zinc-500"
                            }`}
                          >
                            {step.status}
                          </span>
                        </div>
                        <p className="text-xs font-medium text-zinc-200 truncate">{step.label}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-md border border-zinc-800 bg-zinc-900/20 p-8 text-center space-y-3">
              <Clock className="h-6 w-6 text-zinc-500 mx-auto" />
              <p className="text-xs text-zinc-400 font-mono">
                No recent inspection records available. Start an inspection to generate baseline
                telemetry.
              </p>
              <Button asChild size="sm" variant="outline" className="border-zinc-800 text-xs">
                <Link href="/inspect">Start Pre-Launch Inspection</Link>
              </Button>
            </div>
          )}
        </section>

        {/* Recent Runs Table */}
        {latestSummary?.latest_runs && latestSummary.latest_runs.length > 0 && (
          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-semibold tracking-tight uppercase text-zinc-400 font-mono">
                Recent Range Operations
              </h2>
              <Link
                href="/history"
                className="text-xs font-mono text-blue-400 hover:underline flex items-center gap-1"
              >
                <span>View all in history</span>
                <ArrowRight className="h-3 w-3" />
              </Link>
            </div>

            <div className="rounded-md border border-zinc-800 bg-zinc-900/30 overflow-hidden">
              <div className="divide-y divide-zinc-800/60">
                {latestSummary.latest_runs.map((r: RunListItem) => (
                  <div
                    key={r.run_id}
                    className="flex items-center justify-between p-3.5 hover:bg-zinc-900/50 transition-colors text-xs"
                  >
                    <div className="flex items-center space-x-3">
                      <span className="font-mono font-medium text-zinc-300">
                        {r.run_id.slice(0, 8)}...
                      </span>
                      <span className="rounded border border-zinc-800 bg-zinc-900 px-2 py-0.5 text-[10px] font-mono text-zinc-400 uppercase">
                        {r.status}
                      </span>
                      <span className="text-zinc-500 font-mono hidden sm:inline">
                        {new Date(r.created_at).toLocaleTimeString()}
                      </span>
                    </div>

                    <div className="flex items-center space-x-4">
                      {r.risk_score !== null && r.risk_score !== undefined && (
                        <span className="font-mono text-zinc-400 hidden sm:inline">
                          Risk: <strong className="text-zinc-200">{r.risk_score}</strong>
                        </span>
                      )}
                      {r.verdict && (
                        <VerdictBadge verdict={r.verdict as VerdictType} size="sm" />
                      )}
                      <Button
                        asChild
                        variant="ghost"
                        size="sm"
                        className="h-7 text-xs font-mono text-zinc-300 hover:text-zinc-100 hover:bg-zinc-800"
                      >
                        <Link href={`/report/${r.run_id}`}>
                          <span>Report</span>
                        </Link>
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
