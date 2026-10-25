import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";

describe("Secrets Audit (T138, Constitution 5.III)", () => {
  it("confirms OPENAI_API_KEY does not appear in any apps/web source file", () => {
    const webRoot = path.resolve(__dirname, "..");

    const scanDir = (dir: string): string[] => {
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      const files: string[] = [];
      for (const entry of entries) {
        if (
          entry.name === "node_modules" ||
          entry.name === ".next" ||
          entry.name === "tests" ||
          entry.name === ".turbo"
        ) {
          continue;
        }
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          files.push(...scanDir(full));
        } else if (/\.(tsx?|jsx?|json|css|mjs)$/.test(entry.name)) {
          files.push(full);
        }
      }
      return files;
    };

    const files = scanDir(webRoot);
    for (const file of files) {
      const content = fs.readFileSync(file, "utf-8");
      expect(
        content.includes("OPENAI_API_KEY"),
        `File ${path.relative(webRoot, file)} must not contain OPENAI_API_KEY`
      ).toBe(false);

      expect(
        /NEXT_PUBLIC_.*(?:API_KEY|SECRET|TOKEN)/i.test(content),
        `File ${path.relative(webRoot, file)} must not expose sensitive keys via NEXT_PUBLIC_*`
      ).toBe(false);
    }
  });

  it("verifies OPENAI_API_KEY is documented safely in env examples", () => {
    const rootEnvExample = path.resolve(__dirname, "../../../.env.example");
    const apiEnvExample = path.resolve(__dirname, "../../api/.env.example");

    if (fs.existsSync(rootEnvExample)) {
      const rootContent = fs.readFileSync(rootEnvExample, "utf-8");
      expect(rootContent).toContain("OPENAI_API_KEY");
      expect(rootContent).not.toMatch(/OPENAI_API_KEY=sk-[a-zA-Z0-9]{20,}/);
    }

    if (fs.existsSync(apiEnvExample)) {
      const apiContent = fs.readFileSync(apiEnvExample, "utf-8");
      expect(apiContent).toContain("OPENAI_API_KEY");
      expect(apiContent).not.toMatch(/OPENAI_API_KEY=sk-[a-zA-Z0-9]{20,}/);
    }
  });
});
