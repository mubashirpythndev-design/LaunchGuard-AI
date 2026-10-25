import React from "react";
import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import fs from "fs";
import path from "path";

import { VerdictBadge } from "../components/verdict/VerdictBadge";
import { SeverityIndicator } from "../components/verdict/SeverityIndicator";
import { Disclaimer } from "../components/verdict/Disclaimer";
import { FindingList } from "../components/inspection/FindingList";
import type { FindingSchema } from "../lib/schemas";

const CRITICAL_SAFETY_COMPONENTS = [
  "components/verdict/VerdictBadge.tsx",
  "components/verdict/SeverityIndicator.tsx",
  "components/verdict/Disclaimer.tsx",
  "components/inspection/FindingList.tsx",
];

const KNOWN_REACT_BITS = [
  "AnimatedList",
  "CountUp",
  "SpotlightCard",
  "Aurora",
  "Particles",
  "Silk",
  "Iridescence",
  "Galaxy",
  "LiquidChrome",
  "Beams",
  "Lightning",
  "ClickSpark",
  "GradientText",
  "ShinyText",
  "DecryptedText",
  "Dock",
  "PillNav",
];

describe("React Bits Boundary Audit (T139, Constitution 4.III)", () => {
  it("statically verifies no critical safety component imports from components/react-bits", () => {
    for (const compPath of CRITICAL_SAFETY_COMPONENTS) {
      const fullPath = path.resolve(__dirname, "..", compPath);
      expect(fs.existsSync(fullPath), `Safety component file missing: ${compPath}`).toBe(true);

      const content = fs.readFileSync(fullPath, "utf-8");

      // Assert no import from react-bits
      expect(
        content.includes("react-bits"),
        `${compPath} must NOT import from components/react-bits`
      ).toBe(false);

      // Assert none of the known React Bits names appear in the source code
      for (const bit of KNOWN_REACT_BITS) {
        const regex = new RegExp(`\\b${bit}\\b`);
        expect(
          regex.test(content),
          `${compPath} must NOT reference React Bit component: ${bit}`
        ).toBe(false);
      }
    }
  });

  it("renders VerdictBadge statically with zero decorative motion or React Bits", () => {
    const { container: goContainer } = render(<VerdictBadge verdict="GO" />);
    expect(goContainer.querySelector("[data-testid='verdict-badge']")).toBeInTheDocument();
    expect(goContainer.innerHTML).not.toContain("react-bits");

    const { container: holdContainer } = render(<VerdictBadge verdict="HOLD" />);
    expect(holdContainer.querySelector("[data-testid='verdict-badge']")).toBeInTheDocument();
    expect(holdContainer.innerHTML).not.toContain("react-bits");

    const { container: nogoContainer } = render(<VerdictBadge verdict="NO-GO" />);
    expect(nogoContainer.querySelector("[data-testid='verdict-badge']")).toBeInTheDocument();
    expect(nogoContainer.innerHTML).not.toContain("react-bits");
  });

  it("renders SeverityIndicator statically without React Bits", () => {
    const { container } = render(<SeverityIndicator severity="critical" />);
    expect(container.querySelector("[data-testid='severity-indicator-critical']")).toBeInTheDocument();
    expect(container.innerHTML).not.toContain("react-bits");
  });

  it("renders Disclaimer statically with mandated text and no React Bits", () => {
    const { container } = render(<Disclaimer />);
    expect(container.querySelector("[data-testid='disclaimer']")).toBeInTheDocument();
    expect(container.textContent).toContain("Decision-support tool. Not a replacement for certified range safety.");
    expect(container.innerHTML).not.toContain("react-bits");
  });

  it("renders FindingList with findings statically and without React Bits", () => {
    const sampleFindings: FindingSchema[] = [
      {
        module: "cv.fins",
        check_id: "fin.alignment",
        severity: "warning",
        message: "Fin deviation 4.2 deg exceeds warning threshold.",
        confidence: 0.9,
        metrics: [{ name: "fin_angle_deviation", value: 4.2, unit: "deg" }],
        step_position: 2,
        degraded: false,
      },
    ];

    const { container } = render(<FindingList findings={sampleFindings} />);
    expect(container.textContent).toContain("Fin deviation 4.2 deg");
    expect(container.innerHTML).not.toContain("react-bits");
  });
});
