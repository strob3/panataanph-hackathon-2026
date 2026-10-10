import { expect, test } from "@playwright/test";

test("terms of service page is accessible and displays key disclosures", async ({ page }) => {
  await page.goto("/");
  const footerTerms = page.getByRole("button", { name: "Terms", exact: true });
  await expect(footerTerms).toBeVisible();
  await footerTerms.click();

  await expect(page).toHaveURL(/\/terms$/);
  await expect(page.getByRole("heading", { level: 1, name: "Terms of Service" })).toBeVisible();
  await expect(page.getByText("Directory Only")).toBeVisible();
  await expect(page.getByText("Verification & Scoring Disclaimer")).toBeVisible();
  await expect(page.getByText("Organizer Responsibilities")).toBeVisible();
});

test("organizer registration requires agreeing to terms of service", async ({ page }) => {
  await page.goto("/register");
  await page.getByLabel("Full name", { exact: true }).fill("Terms Test User");
  await page.getByLabel("Email", { exact: true }).fill(`terms-test-${Date.now()}@example.test`);
  await page.getByLabel("Password", { exact: true }).fill("valid-password-123");

  const termsCheckbox = page.getByRole("checkbox", {
    name: /Terms of Service/i,
  });
  await expect(termsCheckbox).toBeVisible();
  expect(await termsCheckbox.isChecked()).toBeFalsy();

  // Clicking without check should not create account
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await expect(page.getByText("You must agree to the Terms of Service.")).toBeVisible();

  // Checking terms allows registration to proceed
  await termsCheckbox.check();
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await expect(
    page.getByText("Account created. Sign in with your email and password."),
  ).toBeVisible();
});
