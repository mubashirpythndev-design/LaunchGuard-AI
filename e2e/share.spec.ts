import { test, expect } from "@playwright/test";

test.describe("Public Report Sharing Flow (US5, T120, FR-033, FR-040)", () => {
  test("generates share token, opens in fresh context, asserts read-only report with no controls and no run listings", async ({
    browser,
    request,
    baseURL,
  }) => {
    // 1. Create completed inspection run entity with report via API
    const createRes = await request.post("/api/runs", {
      data: {
        mode: "inspection",
        source_type: "image_upload",
      },
    });
    expect(createRes.status()).toBe(201);
    const runData = await createRes.json();
    const runId = runData.run_id;

    // Submit complete manual inputs to trigger report assembly and completion
    const manualRes = await request.post(`/api/runs/${runId}/manual-inputs`, {
      data: {
        wind_speed_ms: 4.8,
        visibility: "good",
        precipitation: "none",
        area_cleared: true,
        notes: "Nominal launchpad conditions.",
      },
    });
    expect(manualRes.status()).toBe(200);

    // 2. Generate capability share token
    const shareRes = await request.post(`/api/runs/${runId}/share`);
    expect(shareRes.status()).toBe(200);
    const shareData = await shareRes.json();
    const token = shareData.token;
    expect(token).toBeDefined();

    // 3. Open share URL in a fresh, isolated browser context
    const freshContext = await browser.newContext({ baseURL });
    const sharedPage = await freshContext.newPage();

    await sharedPage.goto(`/share/${token}`);

    // Verify mandatory compliance disclaimer is visible (Constitution 1.II, FR-037)
    const disclaimer = sharedPage.getByTestId("disclaimer");
    await expect(disclaimer).toBeVisible();
    await expect(disclaimer).toHaveText(
      /Decision-support tool\. Not a replacement for certified range safety\./
    );

    // Verify static verdict badge renders
    const verdict = sharedPage.getByTestId("verdict-badge");
    await expect(verdict).toBeVisible({ timeout: 10000 });

    // Verify risk gauge is present
    await expect(sharedPage.getByTestId("risk-gauge")).toBeVisible();

    // Verify attribution text
    await expect(
      sharedPage.getByText(/Verdict computed by rules; explanation by AI/i)
    ).toBeVisible();

    // Assert NO run controls are present on shared view
    await expect(sharedPage.locator('input[type="file"]')).toHaveCount(0);
    await expect(sharedPage.getByTestId("toggle-edit-btn")).toHaveCount(0);
    await expect(sharedPage.locator("#wind_speed_ms")).toHaveCount(0);
    await expect(sharedPage.getByRole("button", { name: /Resume Inspection/i })).toHaveCount(0);

    // Assert NO listing of other runs
    await expect(sharedPage.getByTestId("history-table")).toHaveCount(0);

    // 4. Assert 410 SHARE_NOT_AVAILABLE state on non-existent token
    await sharedPage.goto("/share/non-existent-token-xyz-12345");
    await expect(sharedPage.getByTestId("status-410")).toBeVisible();
    await expect(sharedPage.getByText(/Report No Longer Available/i)).toBeVisible();
    await expect(sharedPage.getByTestId("disclaimer")).toBeVisible();

    // 5. Verify strict no-emoji rule across page body
    const bodyText = await sharedPage.locator("body").innerText();
    const emojiRegex = /[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/u;
    expect(bodyText).not.toMatch(emojiRegex);

    await freshContext.close();
  });
});
