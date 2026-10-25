import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import React from "react";
import { LiveStatusBanner } from "@/components/monitor/LiveStatusBanner";
import { useMonitorStore } from "@/stores/monitor-store";

describe("LiveStatusBanner component (T080, T088, FR-016, UX-002)", () => {
  beforeEach(() => {
    act(() => {
      useMonitorStore.getState().reset();
    });
  });

  it("renders CLEAR status with text and Shield icon", () => {
    act(() => {
      useMonitorStore.getState().setLiveStatus("CLEAR");
      useMonitorStore.getState().setProcessingMs(145);
      useMonitorStore.getState().setFps(8.5);
    });

    render(<LiveStatusBanner />);

    const banner = screen.getByTestId("live-status-banner");
    expect(banner).toHaveAttribute("role", "status");
    expect(banner).toHaveAttribute("aria-live", "polite");

    expect(screen.getByTestId("status-label")).toHaveTextContent("CLEAR");
    expect(screen.getByTestId("status-icon-clear")).toBeInTheDocument();
    expect(screen.getByTestId("latency-display")).toHaveTextContent("145 ms");
    expect(screen.getByTestId("fps-display")).toHaveTextContent("8.5 FPS");
  });

  it("renders WARNING status with text and Triangle icon", () => {
    act(() => {
      useMonitorStore.getState().setLiveStatus("WARNING");
    });

    render(<LiveStatusBanner />);

    const banner = screen.getByTestId("live-status-banner");
    expect(banner).toHaveAttribute("aria-live", "polite");
    expect(screen.getByTestId("status-label")).toHaveTextContent("WARNING");
    expect(screen.getByTestId("status-icon-warning")).toBeInTheDocument();
  });

  it("renders DANGER status with assertive aria-live and Octagon icon", () => {
    act(() => {
      useMonitorStore.getState().setLiveStatus("DANGER");
      useMonitorStore.getState().setProcessingMs(420);
    });

    render(<LiveStatusBanner />);

    const banner = screen.getByTestId("live-status-banner");
    expect(banner).toHaveAttribute("aria-live", "assertive");
    expect(screen.getByTestId("status-label")).toHaveTextContent("DANGER");
    expect(screen.getByTestId("status-icon-danger")).toBeInTheDocument();
  });

  it("renders stale feed indicator when isStale is true", () => {
    act(() => {
      useMonitorStore.getState().setIsStale(true);
    });

    render(<LiveStatusBanner />);

    expect(screen.getByTestId("stale-indicator")).toBeInTheDocument();
    expect(screen.getByTestId("stale-indicator")).toHaveTextContent(/feed stale/i);
  });

  it("renders status transition history log without severity finding details", () => {
    act(() => {
      useMonitorStore.getState().setLiveStatus("DANGER");
      // Add transitions: CLEAR -> WARNING -> DANGER
      useMonitorStore.getState().addLogEntry({
        at: "2026-10-01T12:00:00.000Z",
        zone_status: "CLEAR",
        check_ids: [],
        max_severity: "ok",
      });
      useMonitorStore.getState().addLogEntry({
        at: "2026-10-01T12:00:01.000Z",
        zone_status: "WARNING",
        check_ids: ["zone.proximity"],
        max_severity: "warning",
      });
      useMonitorStore.getState().addLogEntry({
        at: "2026-10-01T12:00:02.000Z",
        zone_status: "DANGER",
        check_ids: ["zone.occupancy"],
        max_severity: "critical",
      });
    });

    render(<LiveStatusBanner />);

    expect(screen.getByTestId("transition-log-list")).toBeInTheDocument();
    expect(screen.getByTestId("transition-item-0")).toHaveTextContent(/WARNING.*DANGER/);
  });
});
