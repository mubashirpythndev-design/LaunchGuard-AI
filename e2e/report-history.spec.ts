import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import type { CreateRunResponse } from "../packages/contract/src/types.gen";

test("recent operations opens the saved single-image report instead of loading forever", async ({
  page,
  request,
}) => {
  const result = await request.post("/api/inspections", {
    multipart: {
      file: {
        name: "normal.jpg",
        mimeType: "image/jpeg",
        buffer: fs.readFileSync(
          path.resolve("apps/api/tests/fixtures/images/normal.jpg"),
        ),
      },
    },
  });
  expect(result.status()).toBe(201);
  const run: CreateRunResponse = await result.json();
  await page.goto("/");
  await page.locator(`a[href="/report/${run.run_id}"]`).last().click();
  await expect(page).toHaveURL(new RegExp(`/report/${run.run_id}$`));
  await expect(page.getByTestId("verdict-badge")).toBeVisible();
  await expect(page.getByText("Synthesizing safety narrative...")).toHaveCount(
    0,
  );
  await expect(
    page.getByText("Automated Inspection in Progress..."),
  ).toHaveCount(0);
  await expect(page.getByTestId("disclaimer")).toBeVisible();
  await page.reload();
  await expect(page.getByTestId("verdict-badge")).toBeVisible();
});
