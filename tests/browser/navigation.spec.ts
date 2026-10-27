import { test, expect, login } from "./fixtures";

for (const kind of ["marketing", "marketing_manager", "analyst", "inbox"] as const) {
  test(`native marketing Desk icon and grouped navigation for ${kind}`, async ({ page, accounts }, info) => {
    test.setTimeout(120_000);
    test.skip(info.project.name !== "desktop-light" && kind !== "marketing_manager", "Other roles covered at desktop; manager covers themes and responsive layouts");
    await login(page, accounts[kind], info.project.use.colorScheme === "dark" ? "dark" : "light");
    await page.evaluate(() => (window as any).frappe.set_route("desktop"));
    const title = page.locator("a.icon-title").filter({ hasText: /^TAG Marketing$/ });
    await expect(title).toBeVisible();
    const tile = title.locator("../..");
    const logo = tile.locator('img[src="/assets/tag_marketing/images/tag-marketing.svg"]');
    await expect(logo).toBeVisible();
    await expect(logo).toHaveJSProperty("complete", true);
    expect(await logo.evaluate((image: HTMLImageElement) => image.naturalWidth)).toBeGreaterThan(0);
    await page.screenshot({ path: info.outputPath("marketing-desk-icon.png"), fullPage: true });
    await title.click();
    await expect(page).toHaveURL(/\/desk\/whatsapp-marketing/);
    // A shell URL precedes page/widget readiness. Mobile uses the page toggle,
    // which also sets the drawer height; opening only the rail is insufficient.
    if (kind === "inbox") {
      await expect(page.getByRole("heading", { name: "Inbox unavailable" })).toBeVisible();
    } else {
      await expect(page.locator(".number-widget-box")).toHaveCount(5);
      await expect(page.getByText("N/A", { exact: true })).toHaveCount(5, { timeout: 30_000 });
      await expect(page.getByText("Activity reporting is unavailable until campaign and delivery services are verified.", { exact: true })).toHaveCount(2, { timeout: 30_000 });
    }
    if (info.project.name === "mobile") {
      await page.locator(".sidebar-toggle-btn.navbar-brand:visible").click();
    } else {
      await page.evaluate(() => (window as any).frappe.app.sidebar.open());
    }
    const sidebar = page.locator('.body-sidebar[data-title="WhatsApp Marketing"]');
    await expect(sidebar).toBeVisible();
    if (kind === "inbox") {
      await expect(page.getByRole("heading", { name: "Inbox unavailable" })).toBeVisible();
      await expect(sidebar.locator('[item-name="Overview"]')).toHaveCount(0);
      const group = sidebar.locator('[item-name="Conversations"]');
      await expect(group.locator('[item-icon="message-circle"]')).toBeVisible();
      const inbox = group.locator('[item-name="Inbox"]');
      if (await inbox.isVisible()) {
        await group.locator("button.drop-icon").click();
        await expect(inbox).toBeHidden();
      }
      await group.locator("button.drop-icon").click();
      await expect(inbox).toBeVisible();
    } else {
      await expect(page.getByText("Sending is disabled.", { exact: false })).toBeVisible();
      const group = sidebar.locator('[item-name="Reports"]');
      if (kind === "marketing") {
        const audiences = sidebar.locator('[item-name="Audiences"]');
        await expect(audiences.locator('[item-icon="users"]')).toBeVisible();
        await audiences.locator("button.drop-icon").click();
        await expect(audiences.locator('[item-name="Contacts"]')).toBeVisible();
      } else {
        await expect(group.locator('[item-icon="chart-column"]')).toBeVisible();
        const toggle = group.locator("button.drop-icon");
        await toggle.focus();
        await page.keyboard.press("Enter");
        await expect(group.locator('[item-name="Campaign Performance"]')).toBeVisible();
        await page.screenshot({ path: info.outputPath("marketing-sidebar-expanded.png"), fullPage: true });
        await toggle.click();
        await expect(group.locator('[item-name="Campaign Performance"]')).toBeHidden();
      }
      await expect(sidebar.locator('[item-name="Settings"]')).toHaveCount(0);
    }
    await page.screenshot({ path: info.outputPath("marketing-sidebar.png"), fullPage: true });
  });
}
