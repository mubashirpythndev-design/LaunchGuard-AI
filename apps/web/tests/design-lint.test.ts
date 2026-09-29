import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = process.cwd();
const DIRS = ["app", "components", "hooks", "lib", "stores"];
const EMOJI = /\p{Extended_Pictographic}|\uFE0F|\u200D/u;
const BANNED_COMPONENTS = /\b(Aurora|Particles|Silk|Iridescence|Galaxy|LiquidChrome|Beams|Lightning|ClickSpark|GradientText|ShinyText|Dock|PillNav)\b/;
const GRADIENT = /gradient|drop-shadow|shadow-\[.*(rgb|#)/i;
const COLOR_LITERAL = /#[0-9a-fA-F]{3,8}\b|\b(hsla?|oklch|oklab|lab|lch)\(|\brgba?\((?!\s*(255\s*,\s*255\s*,\s*255|0\s*,\s*0\s*,\s*0)\b)/;

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) {
      if (name !== "node_modules" && name !== ".next") walk(p, out);
    } else if (/\.(tsx?|css)$/.test(name)) {
      out.push(p);
    }
  }
  return out;
}

const files = DIRS.flatMap((d) => {
  try {
    return walk(join(ROOT, d));
  } catch {
    return [];
  }
});
const own = files.filter(
  (f) => !f.includes(`${join("components", "react-bits")}`)
);

describe("design-lint", () => {
  it("has files to check", () => expect(files.length).toBeGreaterThan(0));

  it("contains no emojis or pictographs", () => {
    const bad = files.filter((f) => EMOJI.test(readFileSync(f, "utf8")));
    expect(bad, `Emoji found in: ${bad.join(", ")}`).toEqual([]);
  });

  it("uses no gradients, glow, or coloured shadows", () => {
    const bad = files.filter((f) => GRADIENT.test(readFileSync(f, "utf8")));
    expect(bad, `Gradient/glow found in: ${bad.join(", ")}`).toEqual([]);
  });

  it("keeps colour literals in globals.css only", () => {
    const bad = own.filter(
      (f) => !f.endsWith("globals.css") && COLOR_LITERAL.test(readFileSync(f, "utf8"))
    );
    expect(bad, `Colour literal found in: ${bad.join(", ")}`).toEqual([]);
  });

  it("does not use banned React Bits components", () => {
    const bad = own.filter(
      (f) => /\.(tsx?)$/.test(f) && BANNED_COMPONENTS.test(readFileSync(f, "utf8"))
    );
    expect(bad, `Banned component referenced in: ${bad.join(", ")}`).toEqual([]);
  });
});
