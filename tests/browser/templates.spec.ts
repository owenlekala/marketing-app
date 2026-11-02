import { test, expect, login } from "./fixtures";

test("Marketing Manager creates, validates and safely previews a template draft", async ({ page, accounts }, info) => {
  test.setTimeout(120_000);
  await login(page, accounts.audience_manager, info.project.use.colorScheme === "dark" ? "dark" : "light");
  await page.evaluate(() => (window as any).frappe.set_route("List", "WA Template", "List"));
  let create = page.getByRole("button", { name: "Create Draft", exact: true });
  if (info.project.name === "mobile") {
    await page.getByRole("button", { name: "Menu", exact: true }).click();
    create = page.getByRole("menuitem", { name: "Create Draft", exact: true });
  }
  await expect(create).toBeVisible({ timeout: 30_000 });
  await create.click();
  const createDialog = page.locator(".modal.show").filter({ has: page.getByRole("heading", { name: "Create WhatsApp template draft" }) });
  await expect(createDialog).toBeVisible();
  const name = `wa_browser_template_${accounts.run_id}_${info.project.name.replaceAll("-", "_")}`;
  await createDialog.locator('.frappe-control[data-fieldname="connection"] select').selectOption(accounts.connection);
  await createDialog.locator('.frappe-control[data-fieldname="template_name"] input').fill(name);
  await createDialog.locator('.frappe-control[data-fieldname="language_code"] input').fill("en_US");
  const components = JSON.stringify([{ type: "BODY", text: "Hello {{1}}" }]);
  const editor = createDialog.locator('.frappe-control[data-fieldname="components"] .ace_content');
  await editor.click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText(components);
  await page.keyboard.press("Tab");
  const saveResponsePromise = page.waitForResponse(response => response.url().includes("tag_marketing.api.templates.save"));
  await createDialog.getByRole("button", { name: "Save draft", exact: true }).click();
  const saveResponse = await saveResponsePromise;
  const savePayload = await saveResponse.json();
  expect(saveResponse.ok(), JSON.stringify(savePayload)).toBeTruthy();
  expect(savePayload.message?.ok, JSON.stringify(savePayload)).toBe(true);
  const template = savePayload.message.data.template as string;
  await expect.poll(() => page.evaluate(() => (window as any).frappe.get_route())).toEqual(["Form", "WA Template", template]);
  await expect(page.locator('.form-layout .frappe-control[data-fieldname="template_name"] input')).toHaveValue(name, { timeout: 30_000 });
  await expect(page.locator('.frappe-control[data-fieldname="status"]')).toContainText("Draft");
  await expect(page.locator('.frappe-control[data-fieldname="revision_number"]')).toContainText("1");

  const validateResponsePromise = page.waitForResponse(response => response.url().includes("tag_marketing.api.templates.validate"));
  const formAction = async (label: string) => {
    if (info.project.name === "mobile") {
      await page.locator(".menu-more-button:visible").last().click();
      await page.getByRole("menuitem", { name: label, exact: true }).click();
    } else {
      await page.getByRole("button", { name: label, exact: true }).click();
    }
  };
  await formAction("Validate Draft");
  const validateResponse = await validateResponsePromise;
  const validatePayload = await validateResponse.json();
  expect(validateResponse.ok(), JSON.stringify(validatePayload)).toBeTruthy();
  expect(validatePayload.message?.data?.valid).toBe(true);

  await formAction("Preview");
  const preview = page.locator(".modal.show").filter({ has: page.getByRole("heading", { name: "Template preview" }) });
  const sampleEditor = preview.locator('.frappe-control[data-fieldname="samples"] .ace_content');
  await sampleEditor.click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText(JSON.stringify(["<script>alert(1)</script>"]));
  await page.keyboard.press("Tab");
  await preview.getByRole("button", { name: "Render preview", exact: true }).click();
  const rendered = preview.locator(".wa-template-preview");
  await expect(rendered).toHaveText("Hello <script>alert(1)</script>");
  expect(await rendered.evaluate(element => element.innerHTML)).not.toContain("<script>");
  await page.screenshot({ path: info.outputPath("template-draft-safe-preview.png"), fullPage: true });
});
