import { describe, expect, it } from "vitest";
import { decisionReasonMessages } from "../lib/sse";

describe("completion reason compatibility", () => {
  it("accepts historical text and current structured reasons without rendering objects", () => {
    expect(
      decisionReasonMessages([
        "Recorded warning",
        {
          check_id: "manual.missing_inputs",
          message: "Missing clearance",
          severity: "warning",
        },
      ]),
    ).toEqual(["Recorded warning", "Missing clearance"]);
  });
  it("ignores malformed reason payloads", () => {
    expect(decisionReasonMessages([null, 42, {}, { message: false }])).toEqual([]);
    expect(decisionReasonMessages(null)).toEqual([]);
  });
});
