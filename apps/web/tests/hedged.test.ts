import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";
import {
  BANNED_CERTAINTY_WORDS,
  PERMITTED_HEDGES,
  containsBannedCertaintyClaims,
} from "../lib/hedged";

describe("Hedged Copy & Disclaimer Audit (T137, FR-037, FR-038, SH-004, SH-005)", () => {
  it("detects banned certainty words in text", () => {
    for (const word of BANNED_CERTAINTY_WORDS) {
      const sample = `The system has ${word} the launch vehicle.`;
      expect(
        containsBannedCertaintyClaims(sample),
        `Expected containsBannedCertaintyClaims to flag "${word}"`
      ).toBe(true);
    }
  });

  it("passes compliant hedged phrasing", () => {
    for (const hedge of PERMITTED_HEDGES) {
      const sample = `Fin alignment ${hedge} nominal within camera limits.`;
      expect(
        containsBannedCertaintyClaims(sample),
        `Expected permitted hedge "${hedge}" to not trigger false positive`
      ).toBe(false);
    }
  });

  it("confirms Disclaimer is rendered on all five UX-004 core screens", () => {
    const fiveScreens = [
      "app/page.tsx",
      "app/inspect/page.tsx",
      "app/monitor/page.tsx",
      "app/report/[runId]/page.tsx",
      "app/history/page.tsx",
    ];

    for (const screenPath of fiveScreens) {
      const fullPath = path.resolve(__dirname, "..", screenPath);
      expect(fs.existsSync(fullPath), `Screen file missing: ${screenPath}`).toBe(true);

      const content = fs.readFileSync(fullPath, "utf-8");
      expect(
        content.includes("<Disclaimer"),
        `Screen ${screenPath} must render <Disclaimer />`
      ).toBe(true);
      expect(
        content.includes("Disclaimer"),
        `Screen ${screenPath} must import Disclaimer component`
      ).toBe(true);
    }
  });

  it("scans application copy for prohibited autonomous certification strings", () => {
    const prohibitedPhrases = [
      "certified for flight",
      "guaranteed safe",
      "zero risk",
      "autonomous certification",
      "100% safe",
    ];

    const appDir = path.resolve(__dirname, "../app");
    const scanDir = (dir: string): string[] => {
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      const files: string[] = [];
      for (const entry of entries) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          files.push(...scanDir(full));
        } else if (entry.name.endsWith(".tsx") || entry.name.endsWith(".ts")) {
          files.push(full);
        }
      }
      return files;
    };

    const sourceFiles = scanDir(appDir);
    for (const file of sourceFiles) {
      const content = fs.readFileSync(file, "utf-8").toLowerCase();
      for (const phrase of prohibitedPhrases) {
        expect(
          content.includes(phrase),
          `File ${path.relative(__dirname, file)} must not contain prohibited phrase: "${phrase}"`
        ).toBe(false);
      }
    }
  });
});
