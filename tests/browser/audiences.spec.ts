import { test, expect, login } from "./fixtures";

test("Marketing Manager imports an authorised ERPNext source through native Desk controls", async ({ page, accounts }, info) => {
  test.setTimeout(120_000);
  await login(page, accounts.audience_manager, info.project.use.colorScheme === "dark" ? "dark" : "light");
  await page.evaluate(() => (window as any).frappe.set_route("List", "WA Contact", "List"));
  let addSource = page.getByRole("button", { name: "Add ERPNext Source", exact: true });
  if (!(await addSource.isVisible().catch(() => false))) {
    await page.getByRole("button", { name: "Menu", exact: true }).click();
    addSource = page.getByRole("menuitem", { name: "Add ERPNext Source", exact: true });
  }
  await expect(addSource).toBeVisible({ timeout: 30_000 });
  await addSource.click();
  const dialog = page.locator(".modal.show").filter({ has: page.getByRole("heading", { name: "Add ERPNext Source" }) });
  await expect(dialog).toBeVisible();
  await expect(dialog.locator('.frappe-control[data-fieldname="source_doctype"] select')).toHaveValue("Lead");
  await dialog.locator('.frappe-control[data-fieldname="search"] input').fill(accounts.source_label);
  await dialog.locator('.frappe-control[data-fieldname="country_code"] input').fill("ZA");
  await dialog.getByRole("button", { name: "Search", exact: true }).click();
  const selection = dialog.getByRole("button", { name: /\+2782.*Lead mobile/ });
  await expect(selection).toBeVisible();
  await page.screenshot({ path: info.outputPath("contacts-authorised-source-selection.png"), fullPage: true });
  await selection.click();
  await expect(page.locator('.frappe-control[data-fieldname="phone_e164"]')).toContainText(/\+2782/);
  await expect(page.locator('input[data-doctype="WA Contact"][data-fieldname="display_name"]')).toHaveValue(accounts.source_label);
  await expect(page.locator('.frappe-control[data-fieldname="consent_status"]')).toContainText("Unknown");
  await page.screenshot({ path: info.outputPath("contacts-source-linked-native-form.png"), fullPage: true });
});
