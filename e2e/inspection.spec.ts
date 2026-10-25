import { test, expect } from "@playwright/test";
import path from "path";

test.describe("Pre-Launch Inspection Flow (US1, T058)", () => {
  test("uploads misaligned fin fixture, shows deviation warning, disclaimer, and no emojis", async ({ page }) => {
    await page.goto("/inspect");
    await page.getByRole("tab", { name: "Single image / Demo" }).click();

    // Verify initial screen and mandatory range safety disclaimer
    const disclaimer = page.getByText("Decision-support tool. Not a replacement for certified range safety.");
    await expect(disclaimer).toBeVisible();

    // Locate file input and upload fin_misaligned.jpg fixture
    const fileInput = page.locator('#file-input');
    const fixturePath = path.resolve(__dirname, "../apps/web/public/demo/fin_misaligned.jpg");

    await fileInput.setInputFiles(fixturePath);

    // Assert preview image is visible immediately
    await expect(page.getByAltText("Annotated rocket view")).toBeVisible();

    // Await inspection results and verify fin angle warning
    await expect(page.getByTestId("finding-card-fin.alignment")).toContainText(/fin angle deviation/i);
    await expect(page.getByTestId("finding-card-fin.alignment")).toContainText(/deg/i);

    // Verify verdict badge shows HOLD or NO-GO
    const verdict = page.getByTestId("verdict-badge");
    await expect(verdict).toBeVisible();

    // Verify strict no-emoji rule across rendered page body
    const bodyText = await page.locator("body").innerText();
    const emojiRegex = /[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/u;
    expect(bodyText).not.toMatch(emojiRegex);
  });
});
