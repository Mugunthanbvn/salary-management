import { expect, test } from "@playwright/test";

// No backend needed: these pages make no API call until someone signs in.
// Each test runs at 1440 × 900 and at 390 × 844 (playwright.config.ts).

test("a visitor without a session is sent to sign in, keeping the page", async ({
  page,
}) => {
  await page.goto("/insights");

  await expect(page).toHaveURL("/login?next=%2Finsights");
  await expect(
    page.getByRole("heading", { level: 1, name: "Sign in to ACME Pay" }),
  ).toBeVisible();
});

test("the home page leads to Insights, so to sign in first", async ({
  page,
}) => {
  await page.goto("/");

  await expect(page).toHaveURL("/login?next=%2Finsights");
});

test("the login page fits the screen, with labelled fields and a 44 px button", async ({
  page,
}) => {
  await page.goto("/login");

  await expect(page.getByLabel("Email")).toBeVisible();
  await expect(page.getByLabel("Password")).toBeVisible();
  const signIn = page.getByRole("button", { name: "Sign in" });
  await expect(signIn).toBeVisible();
  const box = await signIn.boundingBox();
  expect(box?.height).toBeGreaterThanOrEqual(44);
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
});
