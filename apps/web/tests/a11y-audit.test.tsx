import React from "react";
import { describe, it, expect } from "vitest";
import { render, act } from "@testing-library/react";

import { VerdictBadge } from "../components/verdict/VerdictBadge";
import { SeverityIndicator } from "../components/verdict/SeverityIndicator";
import { Disclaimer } from "../components/verdict/Disclaimer";
import { LiveStatusBanner } from "../components/monitor/LiveStatusBanner";
import { useMonitorStore } from "../stores/monitor-store";

describe("Accessibility Pass (T136, Constitution 4.VI, FR-041, FR-042, UX-004, SC-009)", () => {
  it("verifies VerdictBadge always provides text and icon alongside color", () => {
    for (const v of ["GO", "HOLD", "NO-GO"] as const) {
      const { container } = render(<VerdictBadge verdict={v} />);
      const badge = container.querySelector("[data-testid='verdict-badge']");
      expect(badge).toBeInTheDocument();
      // Must contain visible text
      expect(badge?.textContent).toContain(v);
      // Must contain SVG icon
      const svg = badge?.querySelector("svg");
      expect(svg, `VerdictBadge for ${v} must contain an SVG icon`).toBeInTheDocument();
    }
  });

  it("verifies SeverityIndicator always provides text and icon alongside color", () => {
    for (const s of ["ok", "warning", "critical"] as const) {
      const { container } = render(<SeverityIndicator severity={s} />);
      const indicator = container.querySelector(`[data-testid='severity-indicator-${s}']`);
      expect(indicator).toBeInTheDocument();
      expect(indicator?.textContent?.toUpperCase()).toContain(s.toUpperCase());
      const svg = indicator?.querySelector("svg");
      expect(svg, `SeverityIndicator for ${s} must contain an SVG icon`).toBeInTheDocument();
    }
  });

  it("verifies LiveStatusBanner contains aria-live for screen reader announcements", () => {
    act(() => {
      useMonitorStore.getState().setLiveStatus("CLEAR");
    });
    const { container: clearContainer } = render(<LiveStatusBanner />);
    const clearBanner = clearContainer.querySelector("[data-testid='live-status-banner']");
    expect(clearBanner).toBeInTheDocument();
    expect(clearBanner?.getAttribute("aria-live")).toBe("polite");

    act(() => {
      useMonitorStore.getState().setLiveStatus("DANGER");
    });
    const { container: dangerContainer } = render(<LiveStatusBanner />);
    const dangerBanner = dangerContainer.querySelector("[data-testid='live-status-banner']");
    expect(dangerBanner).toBeInTheDocument();
    expect(dangerBanner?.getAttribute("aria-live")).toBe("assertive");
  });

  it("verifies Disclaimer has role and non-empty accessible text", () => {
    const { container } = render(<Disclaimer />);
    const disclaimer = container.querySelector("[data-testid='disclaimer']");
    expect(disclaimer).toBeInTheDocument();
    expect(disclaimer?.textContent).toBe(
      "Decision-support tool. Not a replacement for certified range safety."
    );
  });
});
