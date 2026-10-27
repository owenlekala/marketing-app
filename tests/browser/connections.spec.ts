import { test, expect, login } from "./fixtures";

test("Marketing Manager sees safe connection health without credential record access", async ({ page, accounts }, info) => {
  test.setTimeout(120_000);
  test.skip(info.project.name !== "desktop-light", "Connection summary layout is evidenced once; other views are covered by parity checks");
  await login(page, accounts.marketing_manager, "light");
  await page.evaluate(() => (window as any).frappe.set_route("wa-connections"));
  await expect(page.getByRole("navigation", { name: "Breadcrumb" }).getByText("Connections", { exact: true })).toBeVisible();
  await expect(page.getByRole("cell", { name: /WA Harness/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "Sync Templates" })).toBeVisible();
  const summary = await page.evaluate(async () => {
    const response = await fetch("/api/method/tag_marketing.api.connections.health", { credentials: "same-origin" });
    return response.json();
  });
  expect(summary.message.ok).toBe(true);
  const row = summary.message.data.items[0];
  expect(Object.keys(row).sort()).toEqual([
    "connection_name", "last_error_code", "last_validated_at", "last_webhook_at", "name", "number_count", "status", "template_count",
  ].sort());
  expect(JSON.stringify(summary)).not.toMatch(/access_token|app_secret|verify_token|waba_id|meta_app_id/i);
  await page.screenshot({ path: info.outputPath("connections-manager-safe-summary.png"), fullPage: true });
});
