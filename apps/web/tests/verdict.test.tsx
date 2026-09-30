import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { VerdictBadge } from "@/components/verdict/VerdictBadge";
import { Disclaimer, MANDATED_DISCLAIMER_TEXT } from "@/components/verdict/Disclaimer";
import { SeverityIndicator } from "@/components/verdict/SeverityIndicator";

describe("Decision-critical components (Constitution 2.I, 4.III, 4.VI, T050)", () => {
  describe("VerdictBadge", () => {
    it("renders text and an icon for each of GO / HOLD / NO-GO", () => {
      const verdicts = ["GO", "HOLD", "NO-GO"] as const;

      for (const verdict of verdicts) {
        const { unmount } = render(<VerdictBadge verdict={verdict} />);

        const badge = screen.getByTestId(`verdict-badge-${verdict.toLowerCase()}`);
        expect(badge).toBeDefined();

        // 1. Text is present
        expect(badge.textContent).toContain(verdict);

        // 2. Icon (SVG) is present inside the badge
        const svg = badge.querySelector("svg");
        expect(svg).toBeDefined();
        expect(svg).not.toBeNull();

        unmount();
      }
    });

    it("does not render any emoji or pictograph characters", () => {
      const { container } = render(
        <>
          <VerdictBadge verdict="GO" />
          <VerdictBadge verdict="HOLD" />
          <VerdictBadge verdict="NO-GO" />
        </>,
      );

      const emojiRegex = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/u;
      expect(emojiRegex.test(container.textContent || "")).toBe(false);
    });
  });

  describe("Disclaimer", () => {
    it("renders the exact mandated string required on all 5 screens", () => {
      render(<Disclaimer />);
      const disclaimer = screen.getByTestId("disclaimer");

      expect(disclaimer.textContent).toContain(MANDATED_DISCLAIMER_TEXT);
      expect(disclaimer.textContent).toBe(
        "Decision-support tool. Not a replacement for certified range safety.",
      );
    });
  });

  describe("SeverityIndicator", () => {
    it("never conveys state by colour alone — always renders explicit text and icon", () => {
      const severities = ["ok", "warning", "critical"] as const;

      for (const sev of severities) {
        const { unmount } = render(<SeverityIndicator severity={sev} />);

        const indicator = screen.getByTestId(`severity-indicator-${sev}`);
        expect(indicator).toBeDefined();

        // Must display text label so it remains legible in black & white
        expect(indicator.textContent?.toUpperCase()).toContain(sev.toUpperCase());

        // Must contain an icon
        const icon = indicator.querySelector("svg");
        expect(icon).toBeDefined();
        expect(icon).not.toBeNull();

        unmount();
      }
    });
  });
});
