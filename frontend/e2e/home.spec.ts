import { expect, test } from "@playwright/test";

test("home page shows the app name and the API status", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { level: 1, name: "ACME Pay" }),
  ).toBeVisible();
  // "API: ok" with the backend running, "API unreachable" without it.
  await expect(page.getByRole("status")).toHaveText(
    /^(API: ok|API unreachable)$/,
  );
});
