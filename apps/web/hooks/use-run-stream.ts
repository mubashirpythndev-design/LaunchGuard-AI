/**
 * Custom React hook for subscribing to a run's SSE stream and maintaining live state.
 *
 * Constitution 3.IV, Research R2, R5, contracts/events.md.
 */

import { useEffect, useReducer } from "react";
import {
  type AwaitingInputPayload,
  type FindingRaisedPayload,
  type LaunchGuardEvent,
  subscribeToRunEvents,
} from "@/lib/sse";

export interface StreamStep {
  position: number;
  step_key: string;
  label: string;
  status: "pending" | "running" | "passed" | "failed" | "blocked";
  finding_count: number;
}

export interface StreamState {
  steps: StreamStep[];
  findings: FindingRaisedPayload[];
  awaitingInput: AwaitingInputPayload | null;
  verdict: "GO" | "HOLD" | "NO-GO" | null;
  riskScore: number | null;
  reportId: string | null;
  reasons: Array<{
    check_id: string;
    severity: string;
    message: string;
    confidence: number;
    ambiguous?: boolean;
  }>;
  narrative: {
    status: "pending" | "available" | "unavailable";
    text: string | null;
    model: string | null;
  } | null;
  status: "idle" | "running" | "paused" | "completed" | "failed";
  failure: { reason: string; message: string } | null;
  connected: boolean;
  lastSeq: number;
}

const DEFAULT_STEPS: StreamStep[] = [
  { position: 1, step_key: "body", label: "Inspect body", status: "pending", finding_count: 0 },
  { position: 2, step_key: "fins", label: "Check fins", status: "pending", finding_count: 0 },
  {
    position: 3,
    step_key: "launchpad_area",
    label: "Check launchpad area",
    status: "pending",
    finding_count: 0,
  },
  {
    position: 4,
    step_key: "weather_manual",
    label: "Weather & manual inputs",
    status: "pending",
    finding_count: 0,
  },
  {
    position: 5,
    step_key: "decision",
    label: "Generate decision",
    status: "pending",
    finding_count: 0,
  },
];

const initialState: StreamState = {
  steps: DEFAULT_STEPS,
  findings: [],
  awaitingInput: null,
  verdict: null,
  riskScore: null,
  reportId: null,
  reasons: [],
  narrative: null,
  status: "idle",
  failure: null,
  connected: false,
  lastSeq: 0,
};

type StreamAction =
  | { type: "SSE_EVENT"; event: LaunchGuardEvent }
  | { type: "SET_CONNECTED"; connected: boolean }
  | { type: "RESET" };

function streamReducer(state: StreamState, action: StreamAction): StreamState {
  switch (action.type) {
    case "SET_CONNECTED":
      return { ...state, connected: action.connected };

    case "RESET":
      return initialState;

    case "SSE_EVENT": {
      const { event } = action;
      const nextSeq = Math.max(state.lastSeq, event.seq);

      switch (event.type) {
        case "run.started": {
          const rawSteps = event.payload?.steps;
          const initializedSteps: StreamStep[] = Array.isArray(rawSteps)
            ? rawSteps.map((s) => ({
                position: s.position,
                step_key: s.step_key,
                label: s.label,
                status: "pending",
                finding_count: 0,
              }))
            : [];
          return {
            ...state,
            steps: initializedSteps.length > 0 ? initializedSteps : (state.steps ?? DEFAULT_STEPS),
            status: "running",
            lastSeq: nextSeq,
          };
        }

        case "checklist.step.started": {
          const currentSteps = state.steps ?? DEFAULT_STEPS;
          const updatedSteps = currentSteps.map((step) =>
            step.position === event.payload?.position
              ? { ...step, status: "running" as const }
              : step,
          );
          return {
            ...state,
            steps: updatedSteps,
            lastSeq: nextSeq,
          };
        }

        case "finding.raised": {
          return {
            ...state,
            findings: event.payload
              ? [...(state.findings ?? []), event.payload]
              : (state.findings ?? []),
            lastSeq: nextSeq,
          };
        }

        case "checklist.step.finished": {
          const currentSteps = state.steps ?? DEFAULT_STEPS;
          const updatedSteps = currentSteps.map((step) =>
            step.position === event.payload?.position
              ? {
                  ...step,
                  status: event.payload.status,
                  finding_count: event.payload.finding_count ?? 0,
                }
              : step,
          );
          return {
            ...state,
            steps: updatedSteps,
            lastSeq: nextSeq,
          };
        }

        case "run.awaiting_input": {
          const currentSteps = state.steps ?? DEFAULT_STEPS;
          const updatedSteps = currentSteps.map((step) =>
            step.step_key === "weather_manual" ? { ...step, status: "blocked" as const } : step,
          );
          return {
            ...state,
            awaitingInput: event.payload,
            steps: updatedSteps,
            status: "paused",
            lastSeq: nextSeq,
          };
        }

        case "run.completed": {
          return {
            ...state,
            verdict: event.payload?.verdict ?? null,
            riskScore: event.payload?.risk_score ?? null,
            reportId: event.payload?.report_id ?? null,
            reasons: Array.isArray(event.payload?.reasons) ? event.payload.reasons : [],
            narrative: {
              status: "pending",
              text: null,
              model: null,
            },
            awaitingInput: null,
            status: "completed",
            lastSeq: nextSeq,
          };
        }

        case "report.narrative_ready": {
          return {
            ...state,
            narrative: event.payload.narrative,
            lastSeq: nextSeq,
          };
        }

        case "run.failed": {
          return {
            ...state,
            status: "failed",
            failure: event.payload,
            lastSeq: nextSeq,
          };
        }

        default:
          return state;
      }
    }

    default:
      return state;
  }
}

export function useRunStream(runId: string | null, enabled = true) {
  const [state, dispatch] = useReducer(streamReducer, initialState);

  useEffect(() => {
    dispatch({ type: "RESET" });
    if (!runId || !enabled) return;

    const unsubscribe = subscribeToRunEvents(runId, {
      onOpen: () => dispatch({ type: "SET_CONNECTED", connected: true }),
      onEvent: (event) => dispatch({ type: "SSE_EVENT", event }),
      onError: () => dispatch({ type: "SET_CONNECTED", connected: false }),
    });

    return () => {
      unsubscribe();
    };
  }, [runId, enabled]);

  return state;
}
