import { test, expect } from "@playwright/test";
import path from "node:path";

test("a shipped crack on the back quadrant remains NO-GO in the saved report", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const fixture = (name: string) =>
    path.resolve("apps/api/tests/fixtures/images", name);
  await page.goto("/inspect");
  await page.getByRole("button", { name: "Register vehicle" }).click();
  const dialog = page.getByRole("dialog");
  await dialog
    .getByLabel("Vehicle name", { exact: true })
    .fill(`Day 5 crack ${Date.now()}`);
  await dialog
    .getByLabel("Vehicle class", { exact: true })
    .fill("Synthetic demo");
  for (const angle of ["Front", "Right", "Back", "Left"]) {
    await dialog
      .getByLabel(`${angle} golden reference`)
      .setInputFiles(fixture("rocket_golden_reference.jpg"));
  }
  await dialog
    .getByRole("button", { name: "Save vehicle and references" })
    .click();
  await expect(dialog).not.toBeVisible();
  for (const angle of ["Front", "Right", "Back", "Left"]) {
    await page
      .getByLabel(`${angle} image`, { exact: true })
      .setInputFiles(
        fixture(
          angle === "Back"
            ? "rocket_current_cracked.jpg"
            : "rocket_current_intact.jpg",
        ),
      );
  }
  await page.getByRole("button", { name: "Run four-angle inspection" }).click();
  await expect(page.getByTestId("verdict-badge")).toHaveText("NO-GO", {
    timeout: 60_000,
  });
  await page.getByRole("link", { name: "View inspection report" }).click();
  await expect(page.getByTestId("verdict-badge")).toHaveText("NO-GO");
  const evidence = page.getByRole("region", {
    name: "Quadrant inspection evidence",
  });
  await evidence.getByRole("tab", { name: /Back 180/ }).click();
  const slider = evidence.getByRole("slider", {
    name: "Comparison reveal position",
  });
  await slider.focus();
  await slider.press("Home");
  await expect(slider).toHaveValue("0");
  await slider.press("End");
  await expect(slider).toHaveValue("100");
  await slider.press("Home");
  await slider.press("ArrowRight");
  await expect(slider).toHaveValue("1");
  await expect(
    evidence.getByText("reference.structural_deviation", { exact: true }),
  ).toBeVisible();
  await evidence
    .getByRole("button", { name: "Show difference contours" })
    .click();
  await expect(
    evidence.locator(
      'svg[aria-label="Reference difference contours"] rect, svg[aria-label="Reference difference contours"] polygon',
    ),
  ).not.toHaveCount(0);
  await expect(page.getByTestId("disclaimer")).toBeVisible();
  await page.screenshot({
    path: "test-results/day5-cracked-reference.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});
