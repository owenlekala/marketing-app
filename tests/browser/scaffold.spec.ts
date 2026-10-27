import { test, expect } from "./fixtures";

for (const kind of ["agent", "manager"] as const) {
  test(`${kind} logs in through native Desk and retains its own session`, async ({ page, accounts }, info) => {
    const account = accounts[kind];
    await page.goto("/login");
    await page.locator("#login_email").fill(account.username);
    await page.locator("#login_password").fill(account.password);
    await page.locator("#login_password").press("Enter");
    await expect(page).toHaveURL(/\/(app|desk)(\/|$)/, { timeout: 30_000 });
    // Server-injected boot data exists before Desk bundles/startup have finished.
    await page.waitForFunction(() => Boolean(
      (window as any).frappe?.app?.sidebar &&
      typeof (window as any).frappe?.ui?.set_theme === "function"
    ));
    const theme = info.project.use.colorScheme === "dark" ? "dark" : "light";
    await page.evaluate(theme => {
      document.documentElement.setAttribute("data-theme-mode", theme);
      (window as any).frappe.ui.set_theme(theme);
    }, theme);
    await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
    const search = page.getByRole("button", { name: /^Search/ }).first();
    await expect(search).toBeVisible({ timeout: 30_000 });
    await search.focus();
    await expect(search).toBeFocused();
    await search.press("Enter");
    await expect(page.locator("#navbar-search")).toBeFocused();
    await page.keyboard.press("Escape");
    const response = await page.request.get("/api/method/frappe.auth.get_logged_user");
    expect(response.ok()).toBeTruthy();
    expect((await response.json()).message).toBe(account.username);
    const permission = await page.request.get("/api/method/frappe.client.has_permission", {
      params: { doctype: "System Settings", docname: "System Settings", perm_type: "write" }
    });
    expect(permission.ok()).toBeTruthy();
    expect((await permission.json()).message.has_permission).toBe(kind === "manager");
    await page.screenshot({ path: info.outputPath("native-desk.png"), fullPage: true });
  });
}
