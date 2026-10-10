import { expect, test } from "@playwright/test";

for (const width of [320, 375, 768, 1280]) {
  test(`public pages and guest gates fit ${width}px viewport`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const routes = [
      ["/", "Verify before you give."],
      ["/about", "Clear evidence. Human review. Informed giving."],
      ["/terms", "Terms of Service"],
      ["/campaigns", "Relief Campaign Directory"],
      ["/login", "Sign in to PanataanPH"],
      ["/register", "Create your account"],
      ["/verify", "Log in to continue"],
      ["/my-campaigns", "Log in to continue"],
      ["/admin", "Admin and LGU access"],
    ];
    for (const [path, heading] of routes) {
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1, name: heading })).toBeVisible();
      if (path === "/campaigns") {
        await expect(page.getByText(/^\d+ verified campaigns?$/)).toBeVisible();
      }
      if (path === "/login" || path === "/register") {
        await expect(page.getByLabel("Email", { exact: true })).toBeVisible();
        await expect(page.getByLabel("Password", { exact: true })).toBeVisible();
      }
      if (path === "/register") {
        await expect(page.getByLabel("Full name", { exact: true })).toBeVisible();
      }
      await expect
        .poll(() => page.evaluate(() => document.documentElement.scrollWidth), {
          message: `${path} has horizontal overflow at ${width}px`,
        })
        .toBeLessThanOrEqual(width);
      if (path === "/" && width < 1280) {
        await page.getByRole("button", { name: "Open menu", exact: true }).click();
        await expect(page.getByRole("navigation", { name: "Mobile navigation" })).toBeVisible();
        expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
          width,
        );
        await page
          .getByRole("navigation", { name: "Mobile navigation" })
          .getByRole("button", { name: "About", exact: true })
          .click();
        await expect(page).toHaveURL(/\/about$/);
        await expect(page.getByRole("navigation", { name: "Mobile navigation" })).not.toBeVisible();
      }
    }
    expect(errors).toEqual([]);
  });
}
