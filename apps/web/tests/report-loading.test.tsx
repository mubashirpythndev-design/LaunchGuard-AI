import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReportResponse } from "@launchguard/contract";
import ReportPage from "../app/report/[runId]/page";

vi.mock("next/navigation", () => ({
  useParams: () => ({ runId: "test-report" }),
  useRouter: () => ({ push: vi.fn() }),
}));
vi.mock("@/hooks/use-run-stream", () => ({
  useRunStream: () => ({
    status: "completed",
    awaitingInput: null,
    steps: [],
    verdict: "HOLD",
    riskScore: 47,
    narrative: null,
    reasons: [],
  }),
}));

const report: ReportResponse = {
  report_id: "report-id",
  run_id: "test-report",
  verdict: "HOLD",
  risk_score: 47,
  verdict_attribution: "Verdict computed by rules; explanation by AI",
  disclaimer: "Decision-support tool. Not a replacement for certified range safety.",
  checklist: [],
  reasons: [],
  recommended_actions: [],
  findings: [],
  narrative: { status: "unavailable", text: null, model: null },
  annotated_image_url: null,
  generated_at: "2026-10-18T00:00:00Z",
  share_token: null,
};

function showPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ReportPage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
  vi.stubGlobal(
    "matchMedia",
    vi.fn().mockReturnValue({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
    }),
  );
});
afterEach(() => vi.unstubAllGlobals());

describe("historical report loading", () => {
  it("shows an actionable error instead of an endless inspection loader after 404", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", { status: 404 })));
    showPage();
    expect(await screen.findByRole("alert")).toHaveTextContent("Report could not be loaded");
    expect(screen.getByRole("button", { name: "Retry report" })).toBeVisible();
    expect(screen.queryByText("Automated Inspection in Progress...")).not.toBeInTheDocument();
    expect(screen.getByTestId("disclaimer")).toBeVisible();
  });

  it("can retry a failed request and render a report with unavailable narrative", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockRejectedValueOnce(new Error("Offline"))
        .mockResolvedValue({ ok: true, json: async () => report }),
    );
    showPage();
    await screen.findByRole("alert");
    fireEvent.click(screen.getByRole("button", { name: "Retry report" }));
    expect(await screen.findByTestId("verdict-badge")).toHaveTextContent("HOLD");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByText("Synthesizing safety narrative...")).not.toBeInTheDocument();
  });
});
