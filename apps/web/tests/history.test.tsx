import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import HistoryPage from "@/app/history/page";

describe("HistoryPage (T119, US5, FR-032)", () => {
  const mockRunsResponse = {
    total: 25,
    items: [
      {
        run_id: "run-1111-aaaa",
        verdict: "GO",
        risk_score: 12,
        status: "completed",
        created_at: "2026-10-01T12:00:00Z",
        max_severity: null,
      },
      {
        run_id: "run-2222-bbbb",
        verdict: "HOLD",
        risk_score: 55,
        status: "completed",
        created_at: "2026-10-01T12:15:00Z",
        max_severity: null,
      },
      {
        run_id: "run-3333-cccc",
        verdict: "NO-GO",
        risk_score: 85,
        status: "completed",
        created_at: "2026-10-01T12:30:00Z",
        max_severity: null,
      },
    ],
  };

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders history table and mandatory range safety disclaimer", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => mockRunsResponse,
    } as Response);

    render(<HistoryPage />);

    // Verify disclaimer presence
    expect(
      screen.getByText(/Decision-support tool\. Not a replacement for certified range safety\./)
    ).toBeInTheDocument();

    // Verify table rendered with rows
    await waitFor(() => {
      expect(screen.getByTestId("history-table")).toBeInTheDocument();
      expect(screen.getByText("run-1111...")).toBeInTheDocument();
      expect(screen.getByText("run-2222...")).toBeInTheDocument();
      expect(screen.getByText("run-3333...")).toBeInTheDocument();
    });
  });

  it("filters runs when a verdict filter button is clicked", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation(async (url) => {
      const urlStr = url.toString();
      if (urlStr.includes("verdict=GO")) {
        return {
          ok: true,
          json: async () => ({
            total: 1,
            items: [mockRunsResponse.items[0]],
          }),
        } as Response;
      }
      return {
        ok: true,
        json: async () => mockRunsResponse,
      } as Response;
    });

    render(<HistoryPage />);

    await waitFor(() => {
      expect(screen.getByText("run-1111...")).toBeInTheDocument();
    });

    // Click GO filter
    const goFilterBtn = screen.getByTestId("filter-go");
    fireEvent.click(goFilterBtn);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("verdict=GO"));
      expect(screen.getByText("run-1111...")).toBeInTheDocument();
      expect(screen.queryByText("run-2222...")).not.toBeInTheDocument();
    });
  });

  it("handles pagination when next button is clicked", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => mockRunsResponse,
    } as Response);

    render(<HistoryPage />);

    await waitFor(() => {
      expect(screen.getByTestId("pagination-next")).toBeInTheDocument();
    });

    const nextBtn = screen.getByTestId("pagination-next");
    fireEvent.click(nextBtn);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("offset=10"));
    });
  });
});
