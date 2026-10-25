import { test, expect } from "@playwright/test";
import path from "node:path";

test("four-angle upload, aggregated evidence, report, and responsive layout", async ({ page, request }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const profile = await request.post("/api/rockets", { data: {
    name: `Flight test ${Date.now()}`, vehicle_class: "Research",
  } });
  expect(profile.status()).toBe(201);
  const rocket = await profile.json();
  await page.goto("/inspect");
  await expect(page.getByText("A clearer view of flight readiness.")).toBeVisible();
  await page.getByLabel("01 / Vehicle profile").selectOption(rocket.id);
  const submit = page.getByRole("button", { name: "Run four-angle inspection" });
  await expect(submit).toBeDisabled();
  for (const angle of ["Front", "Right", "Back", "Left"]) {
    const fixture = angle === "Back" ? "fin_misaligned.jpg" : "normal.jpg";
    await page.getByLabel(`${angle} image`, { exact: true }).setInputFiles(
      path.resolve("apps/api/tests/fixtures/images", fixture),
    );
    await expect(page.getByAltText(`${angle} capture preview`)).toBeVisible();
  }
  await expect(submit).toBeEnabled();
  await page.screenshot({ path: "test-results/day2-captures-desktop.png", fullPage: true });
  await submit.click();
  await expect(page.getByTestId("verdict-badge")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId("verdict-badge")).toContainText(/HOLD|NO-GO/);
  await page.getByRole("tab", { name: /Back 180/ }).click();
  await expect(page.getByText(/Back:.*fin/i).first()).toBeVisible();
  await expect(page.getByTestId("disclaimer")).toBeInViewport();
  await page.getByRole("link", { name: "View inspection report" }).click();
  await expect(page).toHaveURL(/\/report\//);
  await expect(page.getByRole("tab", { name: /Left 270/ })).toBeVisible();
  await page.screenshot({ path: "test-results/day2-report-desktop.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/inspect");
  await expect(page.getByText("A clearer view of flight readiness.")).toBeVisible();
  await expect(page.getByTestId("disclaimer")).toBeInViewport();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "test-results/day2-captures-mobile.png", fullPage: true });
  expect(errors).toEqual([]);
});
