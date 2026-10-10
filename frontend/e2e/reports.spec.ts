import { expect, test } from "@playwright/test";

test("password visibility toggle reveals and hides password", async ({ page }) => {
  await page.goto("/login");
  const passwordInput = page.getByLabel("Password", { exact: true });
  await passwordInput.fill("super-secret-123");
  await expect(passwordInput).toHaveAttribute("type", "password");

  const toggleBtn = page.getByRole("button", { name: "Show password" });
  await expect(toggleBtn).toBeVisible();
  await toggleBtn.click();

  await expect(passwordInput).toHaveAttribute("type", "text");
  const hideBtn = page.getByRole("button", { name: "Hide password" });
  await expect(hideBtn).toBeVisible();
  await hideBtn.click();

  await expect(passwordInput).toHaveAttribute("type", "password");
});

test("citizens can report a public campaign for review", async ({ page, request }) => {
  const directoryRes = await request.get("/api/campaigns");
  expect(directoryRes.ok()).toBeTruthy();
  const directory = await directoryRes.json();
  expect(directory.items.length).toBeGreaterThan(0);
  const campaign = directory.items[0];

  await page.goto(`/campaigns/${campaign.public_id}`);
  const reportBtn = page.getByRole("button", { name: "Report Fundraiser" });
  await expect(reportBtn).toBeVisible();
  await reportBtn.click();

  await expect(page.getByRole("heading", { name: "Report this Campaign" })).toBeVisible();
  await page.getByLabel("Reason for report").fill("Suspicious payment QR discrepancy");
  await page.getByLabel("Your email (optional)").fill("concerned-citizen@example.test");
  await page.getByRole("button", { name: "Submit Report" }).click();

  await expect(
    page.getByText("Report received. Our review team will independently verify this campaign."),
  ).toBeVisible();
});
