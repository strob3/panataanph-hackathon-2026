import { expect, test } from "@playwright/test";

test("reviewers verify accounts and campaigns before QR and reviewed funds become public", async ({
  page,
  browser,
}) => {
  const email = `review-flow-${Date.now()}@example.test`;
  const title = `Review flow ${Date.now()}`;
  await page.goto("/register?next=/verify");
  await page.getByLabel("Full name", { exact: true }).fill("Review Flow Organizer");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill("browser-organizer-password-123");
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Submit a Fundraiser" })).toBeVisible();
  await page.getByLabel("Organizer name", { exact: false }).fill("Review Flow Organizer");
  await page.getByLabel("Campaign title", { exact: false }).fill(title);
  await page.getByLabel("Location", { exact: false }).fill("Marikina");
  await page.getByLabel("Purpose", { exact: false }).fill("Food packs");
  await page.getByLabel("Target amount", { exact: false }).fill("5000");
  await page
    .getByLabel("Description", { exact: false })
    .fill("Fictional campaign for browser testing");
  await page.getByLabel("Beneficiaries", { exact: false }).fill("Ten test households");
  await page.getByLabel("Payment method", { exact: false }).fill("Test wallet");
  await page
    .getByLabel("Donation payment details", { exact: false })
    .fill("Fictional test recipient");
  await page.getByLabel("Fundraiser Screenshot", { exact: true }).setInputFiles({
    name: "test-permit.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.7\nFictional evidence"),
  });
  const qrInput = page.getByLabel("Donation QR image", { exact: false });
  const qrDropzone = qrInput.locator("../..");
  await expect(qrDropzone.getByText("Browse files or drag and drop")).toBeVisible();
  const transfer = await page.evaluateHandle(() => {
    const data = new DataTransfer();
    data.items.add(new File(["%PDF-1.7"], "invalid-qr.pdf", { type: "application/pdf" }));
    return data;
  });
  await qrDropzone.dispatchEvent("drop", { dataTransfer: transfer });
  await transfer.dispose();
  await expect(page.getByRole("alert")).toContainText("PNG or JPG donation QR");
  await qrInput.setInputFiles({
    name: "test-qr.png",
    mimeType: "image/png",
    buffer: Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j5ioAAAAASUVORK5CYII=",
      "base64",
    ),
  });
  await page.getByRole("button", { name: "Remove donation QR", exact: true }).click();
  const imageTransfer = await page.evaluateHandle(() => {
    const data = new DataTransfer();
    const bytes = Uint8Array.from(
      atob(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j5ioAAAAASUVORK5CYII=",
      ),
      (character) => character.charCodeAt(0),
    );
    data.items.add(new File([bytes], "dropped-qr.png", { type: "image/png" }));
    return data;
  });
  await qrDropzone.dispatchEvent("drop", { dataTransfer: imageTransfer });
  await imageTransfer.dispose();
  await expect(page.getByText("dropped-qr.png", { exact: true })).toBeVisible();
  await page
    .getByLabel("QR label / provider and account name", { exact: false })
    .fill("Test wallet QR");
  await page.getByRole("checkbox").check();
  const submitted = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/submissions") && response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Submit for Review" }).click();
  const response = await submitted;
  expect(response.status()).toBe(201);
  const { public_id: id } = await response.json();
  expect((await page.context().request.get(`/api/campaigns/${id}`)).status()).toBe(404);

  const reviewer = await browser.newContext({
    baseURL: "http://127.0.0.1:5174",
    viewport: page.viewportSize()!,
  });
  try {
    const admin = await reviewer.newPage();
    await admin.goto("/login");
    await admin.getByLabel("Email", { exact: true }).fill("reviewer@example.test");
    await admin.getByLabel("Password", { exact: true }).fill("browser-reviewer-password-123");
    await admin.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(admin).toHaveURL(/\/admin$/);
    await admin.getByRole("button", { name: "Account verification", exact: true }).click();
    await admin.getByRole("button").filter({ hasText: email }).click();
    await admin
      .getByLabel("Account verification reason", { exact: true })
      .fill("Fictional identity evidence checked");
    await admin.getByRole("button", { name: "Verify organizer account", exact: true }).click();
    await expect(admin.getByText("Organizer account verified.", { exact: true })).toBeVisible();
    await admin.getByRole("button", { name: "Campaign review", exact: true }).click();
    await admin.getByRole("button").filter({ hasText: title }).click();
    await admin
      .getByLabel("Review reason", { exact: true })
      .fill("Start fictional evidence review");
    await admin.getByRole("button", { name: "Start review", exact: true }).click();
    await expect(
      admin.getByText("Review saved. Campaign is under review.", { exact: true }),
    ).toBeVisible();
    await admin.getByLabel("Review reason", { exact: true }).fill("Provide a clearer authorization document");
    await admin.getByRole("button", { name: "Save campaign review", exact: true }).click();
    await expect(admin.getByText("Review saved. Campaign is needs information.", { exact: true })).toBeVisible();
    await page.goto("/my-campaigns");
    await page.getByRole("button", { name: "View Review Details", exact: true }).click();
    await expect(page.getByText("Provide a clearer authorization document", { exact: true })).toBeVisible();
    await page.getByLabel("Additional supporting documents", { exact: true }).setInputFiles({
      name: "clearer-authorization.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.7\nFictional additional evidence"),
    });
    const additional = page.waitForResponse((res) => res.url().endsWith(`/my/campaigns/${id}/documents`) && res.request().method() === "POST");
    await page.getByRole("button", { name: "Send Additional Evidence", exact: true }).click();
    expect((await additional).status()).toBe(201);
    expect((await page.context().request.get(`/api/campaigns/${id}`)).status()).toBe(404);
    await admin.getByRole("button", { name: "Refresh queue", exact: true }).click();
    await expect(admin.getByRole("link", { name: "clearer-authorization.pdf", exact: false })).toBeVisible();
    await admin.getByRole("checkbox", { name: /Applicable permits/ }).check();
    await admin.getByRole("checkbox", { name: /Organizer identity/ }).check();
    await admin.getByRole("checkbox", { name: /donation details|Payment|payment/ }).check();
    await admin.getByLabel("Campaign decision", { exact: true }).selectOption("verified");
    await admin.getByRole("checkbox", { name: "Warnings and major inconsistencies reviewed and resolved", exact: true }).check();
    await admin
      .getByLabel("Review reason", { exact: true })
      .fill("Fictional documents and donation destination checked");
    await admin.getByRole("button", { name: "Verify and publish", exact: true }).click();
    await expect(
      admin.getByText("Review saved. Campaign is verified.", { exact: true }),
    ).toBeVisible();
    await page.goto(`/campaigns/${id}`);
    await expect(page.getByRole("heading", { level: 1, name: title })).toBeVisible();
    const qr = page.getByRole("img", { name: /Test wallet QR/ });
    await expect(qr).toBeVisible();
    await expect
      .poll(() => qr.evaluate((element) => (element as HTMLImageElement).naturalWidth))
      .toBeGreaterThan(0);
    await page.goto("/my-campaigns");
    await page.getByRole("button", { name: "Report Funds", exact: true }).click();
    await page.getByLabel("Amount (PHP)", { exact: false }).fill("1200.50");
    await page
      .getByLabel("Transaction date", { exact: false })
      .fill(new Date().toISOString().slice(0, 10));
    await page
      .getByLabel("Public description", { exact: false })
      .fill("Fictional donations received");
    const reported = page.waitForResponse(
      (res) => res.url().endsWith(`/my/campaigns/${id}/funds`) && res.request().method() === "POST",
    );
    await page.getByRole("button", { name: "Submit Fund Report", exact: true }).click();
    expect((await reported).status()).toBe(201);
    const beforeReview = await (await page.context().request.get(`/api/campaigns/${id}`)).json();
    expect(beforeReview.transparency.received_centavos).toBe(0);
    await admin.getByRole("button", { name: "Refresh queue", exact: true }).click();
    await admin
      .getByLabel("Fund update review reason", { exact: true })
      .fill("Fictional receipt checked");
    await admin.getByRole("button", { name: "Save fund review", exact: true }).click();
    await expect
      .poll(async () => {
        const campaign = await (await page.context().request.get(`/api/campaigns/${id}`)).json();
        return campaign.transparency.received_centavos;
      })
      .toBe(120050);
    await page.goto(`/campaigns/${id}`);
    await expect(page.getByText("Fictional donations received", { exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
      page.viewportSize()!.width,
    );
    expect(await admin.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
      admin.viewportSize()!.width,
    );
  } finally {
    await reviewer.close();
  }
});
