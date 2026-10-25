import { test, expect } from "@playwright/test";

test("an unrelated document does not get rocket boxes, angles or a clean inspection", async ({
  page,
}) => {
  await page.goto("/inspect");
  await page.getByRole("tab", { name: "Single image / Demo" }).click();
  // Generate an unrelated document locally; no user screenshot is committed.
  const encoded = await page.evaluate(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 800;
    canvas.height = 600;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Canvas unavailable");
    context.fillStyle = "white";
    context.fillRect(0, 0, 800, 600);
    context.strokeStyle = "black";
    context.fillStyle = "blue";
    context.font = "20px monospace";
    for (let y = 50; y < 580; y += 35) {
      context.beginPath();
      context.moveTo(20, y);
      context.lineTo(780, y);
      context.stroke();
      context.fillText("Notebook: array values 75, 45, 90", 60, y - 8);
    }
    return canvas.toDataURL("image/png").split(",")[1];
  });
  await page.locator("#file-input").setInputFiles({
    name: "rocket.png",
    mimeType: "image/png",
    buffer: Buffer.from(encoded, "base64"),
  });
  await expect(page.getByTestId("verdict-badge")).toHaveText("HOLD");
  await expect(page.getByText("Not evaluated", { exact: true })).toBeVisible();
  await expect(
    page.getByTestId("finding-card-body.subject_unverified"),
  ).toContainText("No defect");
  await expect(
    page.getByTestId("finding-card-fin.subject_unverified"),
  ).toContainText("No defect");
  await expect(page.getByTestId("finding-card-fin.alignment")).toHaveCount(0);
  await expect(
    page.locator('[data-testid^="overlay-bbox"], [data-testid^="overlay-arc"]'),
  ).toHaveCount(0);
  await expect(page.getByTestId("disclaimer")).toBeVisible();
  await page.screenshot({
    path: "test-results/unsupported-document.png",
    fullPage: true,
  });
});
