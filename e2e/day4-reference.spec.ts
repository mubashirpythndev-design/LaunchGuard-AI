import { test, expect } from "@playwright/test";
import path from "node:path";

test.use({
  launchOptions: {
    args: [
      "--use-fake-ui-for-media-stream",
      "--use-fake-device-for-media-stream",
    ],
  },
});

test("profile dialog, webcam HUD, and reference comparison work on inspection and report", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/inspect");
  await page.getByRole("button", { name: "Register vehicle" }).click();
  const dialog = page.getByRole("dialog");
  await expect(
    dialog.getByText(
      "Decision-support tool. Not a replacement for certified range safety.",
    ),
  ).toBeVisible();
  await dialog
    .getByLabel("Vehicle name", { exact: true })
    .fill(`Day 4 vehicle ${Date.now()}`);
  await dialog.getByLabel("Vehicle class", { exact: true }).fill("Research");
  await dialog.getByLabel("Vehicle notes").fill("Standard baseline setup");
  const reference = path.resolve(
    "apps/api/tests/fixtures/images/rocket_reference_front.jpg",
  );
  for (const angle of ["Front", "Right", "Back", "Left"])
    await dialog
      .getByLabel(`${angle} golden reference`)
      .setInputFiles(reference);
  await dialog
    .getByRole("button", { name: "Save vehicle and references" })
    .click();
  await expect(dialog).not.toBeVisible();
  await expect(page.getByAltText("Front enrolled baseline")).toBeVisible();

  await page.getByRole("button", { name: "Start camera" }).click();
  await expect(
    page.getByRole("button", { name: "Capture front image" }),
  ).toBeEnabled();
  await page.getByLabel("Alignment guide", { exact: true }).uncheck();
  await page.getByRole("button", { name: "Capture front image" }).click();
  await expect(page.getByAltText("Front capture preview")).toBeVisible();
  await page.getByRole("button", { name: "Stop camera" }).click();

  for (const angle of ["Front", "Right", "Back", "Left"])
    await page
      .getByLabel(`${angle} image`, { exact: true })
      .setInputFiles(reference);
  await page.getByRole("button", { name: "Run four-angle inspection" }).click();
  await expect(page.getByTestId("verdict-badge")).toBeVisible({
    timeout: 60_000,
  });
  await expect(
    page.getByRole("slider", { name: "Comparison reveal position" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Difference map" }).click();
  await expect(
    page.getByAltText("Reference comparison difference map"),
  ).toBeVisible();
  await page.getByRole("link", { name: "View inspection report" }).click();
  await expect(
    page.getByRole("slider", { name: "Comparison reveal position" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Show difference contours" }).click();
  await expect(
    page.getByRole("button", { name: "Hide difference contours" }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.screenshot({
    path: "test-results/day4-reference-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/inspect");
  await expect(page.getByTestId("disclaimer")).toBeInViewport();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/day4-capture-mobile.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});
