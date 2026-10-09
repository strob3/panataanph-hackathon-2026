import { expect, test } from "@playwright/test";

test("directory reads the backend and opens a public campaign", async ({ page, request }) => {
  const response = await request.get("/api/campaigns");
  expect(response.ok()).toBeTruthy();
  const directory = await response.json();
  expect(directory.items.length).toBeGreaterThan(0);
  const campaign = directory.items[0];
  await page.goto("/campaigns");
  await expect(page.getByRole("heading", { name: campaign.title })).toBeVisible();
  await page.getByRole("textbox", { name: "Search campaigns" }).fill(campaign.title);
  await expect(page.getByRole("heading", { name: campaign.title })).toBeVisible();
  await page.getByRole("button", { name: "View Campaign" }).first().click();
  await expect(page).toHaveURL(new RegExp(`/campaigns/${campaign.public_id}$`));
  await expect(page.getByRole("heading", { level: 1, name: campaign.title })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Campaign Information" })).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download Public Report" }).click();
  expect((await download).suggestedFilename()).toBe(`panataanph-${campaign.public_id}.json`);
  await page.getByRole("button", { name: "Back to Directory" }).click();
  await page.getByRole("textbox", { name: "Search campaigns" }).fill("no-matching-campaign-123456");
  await expect(page.getByText("No verified campaigns match these filters.")).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBeTruthy();
});

test("submission persists to the backend and stays out of the directory", async ({
  page,
  request,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Verify before you give." })).toBeVisible();
  await page.getByRole("button", { name: "Open Submission Form" }).click();
  await expect(page.getByRole("heading", { name: "Log in to continue" })).toBeVisible();
  await page.getByRole("button", { name: "Create Account", exact: true }).click();
  await page.getByLabel("Full name", { exact: true }).fill("Browser Test Organizer");
  await page.getByLabel("Email", { exact: true }).fill(`organizer-${Date.now()}@example.test`);
  await page.getByLabel("Password", { exact: true }).fill("browser-test-password-123");
  await page.getByRole("checkbox", { name: /Terms of Service/i }).check();
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Submit a Fundraiser" })).toBeVisible();
  await page.getByLabel("Organizer name").fill("Browser Test Organizer");
  await page.getByLabel("Campaign title").fill("Browser Test Relief");
  await page.getByLabel("Location", { exact: false }).fill("Marikina");
  await page.getByLabel("Purpose").fill("Food packs");
  await page.getByLabel("Target amount").fill("5000");
  await page.getByLabel("Description", { exact: false }).fill("Relief for displaced families");
  await page.getByLabel("Fundraiser Screenshot", { exact: true }).setInputFiles({
    name: "evidence.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.7\nBrowser test evidence"),
  });
  await page.getByRole("checkbox").check();
  const submissionResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/submissions") && response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Submit for Review" }).click();
  const response = await submissionResponse;
  expect(response.status()).toBe(201);
  const submission = await response.json();
  expect(submission.status).toBe("pending");
  await expect(page.getByRole("heading", { name: "Submission received" })).toBeVisible();
  await expect(page.getByText(submission.public_id, { exact: true })).toBeVisible();
  const privateCampaign = await request.get(`/api/campaigns/${submission.public_id}`);
  expect(privateCampaign.status()).toBe(404);
  await page.getByRole("button", { name: "Browse Campaigns", exact: true }).click();
  await page.getByRole("textbox", { name: "Search campaigns" }).fill("Browser Test Relief");
  await expect(page.getByText("No verified campaigns match these filters.")).toBeVisible();
  await page.goto("/my-campaigns");
  await expect(page.getByRole("heading", { name: "Browser Test Relief" })).toBeVisible();
  if (page.viewportSize()!.width < 1280) {
    await page.getByRole("button", { name: "Open menu" }).click();
    await page
      .getByRole("navigation", { name: "Mobile navigation" })
      .getByRole("button", { name: "Log Out" })
      .click();
  } else {
    await page.getByRole("button", { name: "Log Out" }).click();
  }
  await page.goto("/my-campaigns");
  await expect(page.getByRole("heading", { name: "Log in to continue" })).toBeVisible();
  expect(errors).toEqual([]);
});
