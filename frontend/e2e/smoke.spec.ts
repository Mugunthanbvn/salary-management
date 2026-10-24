import { expect, test, type Page } from "@playwright/test";

// The smoke flow (docs/14-testing-strategy.md §5.8) against the real local stack started by
// playwright.config.ts: FastAPI on a fresh `--seed 42 --employees 300` SQLite file and the
// production build of the web app. Each test runs at 1440 × 900 and at 390 × 844.

const HR = { email: "hr@acme.example", password: "change-me-hr" };
const VIEWER = { email: "viewer@acme.example", password: "change-me-viewer" };

// Each viewport raises a different seeded employee with an accented name, so the two
// projects can run in parallel on the same database without seeing each other's raise.
const RAISES = {
  desktop: {
    search: "gonçalves",
    name: "Thomas Gonçalves",
    newBase: "152000",
    from: "R$141,000",
    shown: "R$152,000",
  },
  phone: {
    search: "jähn",
    name: "Darius Jähn",
    newBase: "121500",
    from: "€115,000",
    shown: "€121,500",
  },
} as const;

async function signIn(page: Page, user: { email: string; password: string }) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(user.email);
  await page.getByLabel("Password").fill(user.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/insights/);
}

async function openEmployee(page: Page, search: string, name: string) {
  await page.goto("/employees");
  await page.getByLabel("Search by name, employee code or email").fill(search);
  await expect(page).toHaveURL(/q=/);
  await page.getByRole("link", { name }).click();
  await expect(
    page.getByRole("heading", { level: 1, name: new RegExp(name) }),
  ).toBeVisible();
}

test("an HR manager finds an employee by an accented name and records a merit raise", async ({
  page,
}, testInfo) => {
  const raise = RAISES[testInfo.project.name as keyof typeof RAISES];
  await signIn(page, HR);
  await openEmployee(page, raise.search, raise.name);

  await page.getByRole("button", { name: "Record salary change" }).click();
  const dialog = page.getByRole("dialog", { name: "Record a salary change" });
  await dialog.getByLabel("Reason").selectOption({ label: "Merit raise" });
  await dialog.getByLabel(/New base pay/).fill(raise.newBase);
  await dialog.getByRole("button", { name: "Record salary change" }).click();

  await expect(dialog).toBeHidden();
  // The timeline lists the newest record first: the raise, recorded by the HR manager.
  const newest = page
    .getByRole("list")
    .filter({ hasText: "Hired" })
    .getByRole("listitem")
    .first();
  await expect(newest).toContainText("Merit raise by Hema");
  await expect(newest).toContainText(`${raise.from} to ${raise.shown}`);
  // Current pay: the first figure under "Base pay" is the new amount.
  const basePay = page.getByRole("term").filter({ hasText: "Base pay" });
  await expect(basePay.locator("+ dd")).toHaveText(raise.shown);
});

test("a viewer sees an employee without salary or salary actions", async ({
  page,
}) => {
  await signIn(page, VIEWER);
  await openEmployee(page, "cécile", "Cécile Masse");

  await expect(
    page.getByText("Compensation details are restricted for your role."),
  ).toBeVisible();
  await expect(page.getByText(/€\d/)).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Record salary change" }),
  ).toHaveCount(0);
});
