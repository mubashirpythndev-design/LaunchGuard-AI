import { test, expect } from "@playwright/test";

test.describe("Demo Mode Scenarios E2E (US6, T131, FR-034, SC-001)", () => {
  test("dashboard displays demo scenarios menu with expected verdicts", async ({ page }) => {
    await page.goto("/");

    // 1. Assert demo scenarios menu is visible
    const menu = page.getByTestId("demo-scenario-menu");
    await expect(menu).toBeVisible();

    // 2. Assert all three canonical scenarios are presented
    await expect(page.getByTestId("demo-scenario-normal")).toBeVisible();
    await expect(page.getByTestId("demo-scenario-misaligned_fin")).toBeVisible();
    await expect(page.getByTestId("demo-scenario-person_near_pad")).toBeVisible();

    // 3. Assert mandatory range safety disclaimer is visible
    const disclaimer = page.getByTestId("disclaimer");
    await expect(disclaimer).toBeVisible();

    // 4. Assert zero emoji compliance across body
    const bodyText = await page.locator("body").innerText();
    const emojiRegex = /[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/u;
    expect(bodyText).not.toMatch(emojiRegex);
  });

  test("demo scenario runs produce GO, HOLD, and NO-GO deterministically in 10 consecutive passes (SC-001)", async ({
    request,
  }) => {
    // This exercises 30 complete runs, not a single interactive request.
    test.setTimeout(180_000);
    const expectedVerdicts: Record<string, string> = {
      normal: "GO",
      misaligned_fin: "HOLD",
      person_near_pad: "NO-GO",
    };

    // 10 consecutive passes across all 3 scenarios per SC-001
    for (let iteration = 1; iteration <= 10; iteration++) {
      for (const [key, expectedVerdict] of Object.entries(expectedVerdicts)) {
        const triggerRes = await request.post(`/api/demo/scenarios/${key}/run`);
        expect(triggerRes.status(), `Iteration ${iteration} ${key} trigger status`).toBe(201);

        const data = await triggerRes.json();
        const runId = data.run_id;
        expect(runId).toBeTruthy();

        const reportRes = await request.get(`/api/runs/${runId}/report`);
        expect(reportRes.status(), `Iteration ${iteration} ${key} report status`).toBe(200);

        const report = await reportRes.json();
        expect(
          report.verdict,
          `Iteration ${iteration} ${key} must yield ${expectedVerdict}`
        ).toBe(expectedVerdict);
        expect(report.disclaimer).toContain(
          "Decision-support tool. Not a replacement for certified range safety."
        );
      }
    }
  });

  test("clicking demo scenario on inspect page navigates to completed report", async ({ page }) => {
    await page.goto("/inspect");
    await page.getByRole("tab", { name: "Single image / Demo" }).click();

    const menu = page.getByTestId("demo-scenario-menu");
    await expect(menu).toBeVisible();

    // Click the normal scenario run button
    const runNormalBtn = page
      .getByTestId("demo-scenario-normal")
      .getByRole("button", { name: /run/i });
    await expect(runNormalBtn).toBeVisible();
    await runNormalBtn.click();

    // Verify navigation to report page
    await expect(page).toHaveURL(/\/report\/[a-f0-9-]+/, { timeout: 15000 });

    // Verify verdict badge shows GO
    const verdict = page.getByTestId("verdict-badge");
    await expect(verdict).toBeVisible();
    await expect(verdict).toHaveText(/GO/);

    // Verify disclaimer on report page
    const disclaimer = page.getByTestId("disclaimer");
    await expect(disclaimer).toBeVisible();
  });
});
