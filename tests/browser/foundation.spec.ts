import { test, expect, login } from "./fixtures";

test("system manager opens native settings without exposing suppression credentials", async ({ page, accounts }, info) => {
  await login(page, accounts.manager, info.project.use.colorScheme === "dark" ? "dark" : "light");
  await page.evaluate(() => (window as any).frappe.set_route("Form", "WA Settings"));
  const company = page.locator('.frappe-control[data-fieldname="marketing_company"] input');
  await expect(company).toBeVisible();
  await company.focus();
  await expect(company).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(page.getByText("Retention and Privacy", { exact: true })).toBeVisible();
  await expect(page.locator('.frappe-control[data-fieldname="suppression_hmac_key"]')).toBeHidden();
  await expect(page.locator('input[data-fieldname="sending_enabled"]')).not.toBeChecked();
  expect(await page.evaluate(() => Boolean((window as any).frappe.get_doc("WA Settings").suppression_hmac_key))).toBe(false);
  await page.screenshot({ path: info.outputPath("native-settings.png"), fullPage: true });
  await page.getByText("Retention and Privacy", { exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath("native-settings-privacy.png"), fullPage: true });
});

test("ordinary agent cannot retrieve marketing settings through the generic API", async ({ page, accounts }, info) => {
  await login(page, accounts.agent, info.project.use.colorScheme === "dark" ? "dark" : "light");
  const response = await page.request.get("/api/method/frappe.client.get", { params: { doctype: "WA Settings" } });
  expect(response.status()).toBe(403);
});
