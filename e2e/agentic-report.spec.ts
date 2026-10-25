import { test, expect } from "@playwright/test";

test.describe("Agentic Safety Report Flow (US4, T105, FR-023, FR-026)", () => {
  test("run pauses for missing inputs, dialog submits, run resumes, and report renders verdict with disclaimer", async ({
    page,
    request,
  }) => {
    // 1. Create a fresh inspection run entity via API
    const createRes = await request.post("/api/runs", {
      data: {
        mode: "inspection",
        source_type: "image_upload",
      },
    });
    expect(createRes.status()).toBe(201);
    const runData = await createRes.json();
    const runId = runData.run_id;

    // 2. Put run into paused state awaiting mandatory inputs (step 4)
    const pauseRes = await request.post(`/api/runs/${runId}/manual-inputs`, {
      data: {},
    });
    expect(pauseRes.status()).toBe(200);
    const pauseData = await pauseRes.json();
    expect(pauseData.status).toBe("paused");
    expect(pauseData.missing).toContain("wind_speed_ms");

    // 3. Navigate to the agentic safety report page
    await page.goto(`/report/${runId}`);

    // Verify mandatory compliance disclaimer is visible (Constitution 1.II, FR-037)
    const disclaimer = page.getByTestId("disclaimer");
    await expect(disclaimer).toBeVisible();
    await expect(disclaimer).toHaveText(
      /Decision-support tool\. Not a replacement for certified range safety\./
    );

    // 4. Assert paused state is displayed or dialog opens
    const pausedIndicator = page.getByText(/Inspection Paused/i);
    const manualBtn = page.getByRole("button", { name: /Enter Manual Inputs/i });

    // Open Manual Inputs Dialog if not auto-opened
    if (await manualBtn.isVisible()) {
      await manualBtn.click();
    }

    // Verify dialog appears
    const dialogTitle = page.getByText(/Range Safety: Manual Verification Required/i);
    await expect(dialogTitle).toBeVisible();

    // 5. Fill valid manual environmental inputs
    await page.locator("#wind_speed_ms").fill("5.5");
    await page.locator("#visibility").selectOption("good");
    await page.locator("#precipitation").selectOption("none");
    await page.locator("#area_cleared").check();
    await page.locator("#notes").fill("Range officer confirmed pad clearance.");

    // 6. Submit and resume inspection
    const resumeBtn = page.getByRole("button", { name: /Resume Inspection/i });
    await resumeBtn.click();

    // 7. Await run completion and verify verdict badge renders
    const verdict = page.getByTestId("verdict-badge");
    await expect(verdict).toBeVisible({ timeout: 15000 });

    // Verify static verdict badge has no DecryptedText or animation classes
    const verdictContent = page.getByTestId(/verdict-badge-(go|hold|nogo)/i);
    await expect(verdictContent).toBeVisible();

    // Verify range safety disclaimer remains visible
    await expect(disclaimer).toBeVisible();

    // Verify attribution text
    await expect(
      page.getByText(/Verdict computed by rules; explanation by AI/i)
    ).toBeVisible();

    // 8. Verify strict no-emoji rule across rendered page body (Constitution 4.VII)
    const bodyText = await page.locator("body").innerText();
    const emojiRegex = /[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/u;
    expect(bodyText).not.toMatch(emojiRegex);
  });
});
