"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { VerdictBadge, type VerdictType } from "@/components/verdict/VerdictBadge";
import type { CreateRunResponse, DemoScenarioItem, DemoScenariosResponse } from "@launchguard/contract";

interface DemoScenarioMenuProps {
  className?: string;
  onRunTriggered?: (runId: string) => void;
}

export function DemoScenarioMenu({ className = "", onRunTriggered }: DemoScenarioMenuProps) {
  const router = useRouter();
  const [scenarios, setScenarios] = useState<DemoScenarioItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [triggeringKey, setTriggeringKey] = useState<string | null>(null);

  useEffect(() => {
    async function loadScenarios() {
      try {
        const res = await fetch("/api/demo/scenarios");
        if (res.ok) {
          const data: DemoScenariosResponse = await res.json();
          setScenarios(data.scenarios);
        }
      } catch (err) {
        console.error("Failed to load demo scenarios:", err);
      } finally {
        setLoading(false);
      }
    }

    loadScenarios();
  }, []);

  const handleRunScenario = async (key: string) => {
    setTriggeringKey(key);
    try {
      const res = await fetch(`/api/demo/scenarios/${encodeURIComponent(key)}/run`, {
        method: "POST",
      });
      if (res.ok) {
        const data: CreateRunResponse = await res.json();
        if (onRunTriggered) {
          onRunTriggered(data.run_id);
        } else {
          router.push(`/report/${data.run_id}`);
        }
      }
    } catch (err) {
      console.error("Failed to execute demo scenario:", err);
    } finally {
      setTriggeringKey(null);
    }
  };

  if (loading) {
    return (
      <div className={`flex items-center space-x-2 text-xs font-mono text-zinc-500 ${className}`}>
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        <span>Loading bundled scenarios...</span>
      </div>
    );
  }

  if (scenarios.length === 0) {
    return null;
  }

  return (
    <div
      data-testid="demo-scenario-menu"
      className={`rounded-md border border-zinc-800 bg-zinc-900/40 p-4 space-y-3 ${className}`}
    >
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-300 font-mono">
              Offline Demo Scenarios
            </span>
            <span className="rounded border border-emerald-900 bg-emerald-950/60 px-1.5 py-0.2 text-[10px] font-mono text-emerald-400">
              100% Deterministic
            </span>
          </div>
          <p className="text-[11px] text-zinc-400">
            One-click offline demonstration of the 3 canonical FAA range safety scenarios
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 pt-1">
        {scenarios.map((sc) => {
          const isTriggering = triggeringKey === sc.key;
          return (
            <div
              key={sc.key}
              data-testid={`demo-scenario-${sc.key}`}
              className="flex flex-col justify-between rounded border border-zinc-800 bg-zinc-900/60 p-3 space-y-3 hover:border-zinc-700 transition-colors"
            >
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-zinc-200">{sc.label}</span>
                  <VerdictBadge verdict={sc.expected_verdict as VerdictType} size="sm" />
                </div>
                <div className="text-[11px] font-mono text-zinc-500">
                  Target verdict: {sc.expected_verdict}
                </div>
              </div>

              <Button
                size="sm"
                variant="outline"
                disabled={triggeringKey !== null}
                onClick={() => handleRunScenario(sc.key)}
                className="w-full h-7 border-zinc-800 font-mono text-[11px] text-zinc-300 hover:text-zinc-100 hover:bg-zinc-800 justify-center"
              >
                {isTriggering ? (
                  <>
                    <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />
                    <span>Executing...</span>
                  </>
                ) : (
                  <>
                    <Play className="mr-1.5 h-3 w-3 text-zinc-400" />
                    <span>Run Scenario</span>
                  </>
                )}
              </Button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
