/**
 * Typed EventSource wrapper and LaunchGuard event union (Constitution 3.IV, contracts/events.md).
 */

export interface RunStartedPayload {
  run_id: string;
  mode: string;
  source_type: string;
  steps: Array<{ position: number; step_key: string; label: string }>;
}

export interface StepStartedPayload {
  position: number;
  step_key: string;
  label: string;
}

export type FindingRaisedPayload = import("@/lib/schemas").FindingSchema;

export interface StepFinishedPayload {
  position: number;
  step_key: string;
  status: "pending" | "running" | "passed" | "failed" | "blocked";
  finding_count: number;
}

export interface AwaitingInputPayload {
  missing: string[];
  fields: Array<{
    name: string;
    label: string;
    type: string;
    unit?: string;
    min?: number;
    max?: number;
    options?: string[];
    max_length?: number;
    required: boolean;
  }>;
}

export interface RunCompletedPayload {
  verdict: "GO" | "HOLD" | "NO-GO";
  risk_score: number;
  report_id: string;
  narrative: { status: "pending" };
  reasons: Array<{
    check_id: string;
    severity: string;
    message: string;
    confidence: number;
    ambiguous?: boolean;
  }>;
}

export interface NarrativeReadyPayload {
  narrative: {
    status: "available" | "unavailable";
    text: string | null;
    model: string | null;
  };
}

export interface RunFailedPayload {
  reason: string;
  message: string;
}

export type LaunchGuardEvent =
  | { type: "run.started"; seq: number; at: string; payload: RunStartedPayload }
  | { type: "checklist.step.started"; seq: number; at: string; payload: StepStartedPayload }
  | { type: "finding.raised"; seq: number; at: string; payload: FindingRaisedPayload }
  | { type: "checklist.step.finished"; seq: number; at: string; payload: StepFinishedPayload }
  | { type: "run.awaiting_input"; seq: number; at: string; payload: AwaitingInputPayload }
  | { type: "run.completed"; seq: number; at: string; payload: RunCompletedPayload }
  | { type: "report.narrative_ready"; seq: number; at: string; payload: NarrativeReadyPayload }
  | { type: "run.failed"; seq: number; at: string; payload: RunFailedPayload };

export interface EventEnvelope<T = unknown> {
  seq: number;
  at: string;
  payload: T;
}

export interface SseSubscriptionOptions {
  onEvent: (event: LaunchGuardEvent) => void;
  onError?: (err: Event) => void;
  onOpen?: () => void;
}

export function subscribeToRunEvents(runId: string, options: SseSubscriptionOptions): () => void {
  const url = `/api/runs/${encodeURIComponent(runId)}/stream`;
  const eventSource = new EventSource(url);

  const eventTypes = [
    "run.started",
    "checklist.step.started",
    "finding.raised",
    "checklist.step.finished",
    "run.awaiting_input",
    "run.completed",
    "report.narrative_ready",
    "run.failed",
  ] as const;

  const handleMessage = (type: LaunchGuardEvent["type"], event: MessageEvent<string>) => {
    try {
      const data = JSON.parse(event.data) as EventEnvelope;
      const typedEvent = {
        type,
        seq: data.seq,
        at: data.at,
        payload: data.payload,
      } as LaunchGuardEvent;

      options.onEvent(typedEvent);

      if (type === "report.narrative_ready" || type === "run.failed") {
        eventSource.close();
      }
    } catch (err) {
      console.error("Failed to parse SSE event payload:", err);
    }
  };

  for (const type of eventTypes) {
    eventSource.addEventListener(type, (e: MessageEvent<string>) => handleMessage(type, e));
  }

  if (options.onOpen) {
    eventSource.onopen = options.onOpen;
  }
  if (options.onError) {
    eventSource.onerror = options.onError;
  }

  return () => {
    eventSource.close();
  };
}
/** Normalize historical text reasons and current structured reasons for text-only views. */
export function decisionReasonMessages(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((reason: unknown) => {
    if (typeof reason === "string") return [reason];
    if (
      typeof reason === "object" &&
      reason !== null &&
      "message" in reason &&
      typeof reason.message === "string"
    )
      return [reason.message];
    return [];
  });
}
