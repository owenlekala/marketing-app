import { test, expect, login } from "./fixtures";

test("Marketing Manager imports an authorised ERPNext source through native Desk controls", async ({ page, accounts }, info) => {
  test.setTimeout(120_000);
  await login(page, accounts.audience_manager, info.project.use.colorScheme === "dark" ? "dark" : "light");
  await page.evaluate(() => (window as any).frappe.set_route("List", "WA Contact", "List"));
  let addSource = page.getByRole("button", { name: "Add ERPNext Source", exact: true });
  if (info.project.name === "mobile") {
    await page.getByRole("button", { name: "Menu", exact: true }).click();
    addSource = page.getByRole("menuitem", { name: "Add ERPNext Source", exact: true });
    await expect(addSource).toBeVisible({ timeout: 30_000 });
    await addSource.click();
  } else {
    await expect(addSource).toBeVisible({ timeout: 30_000 });
    await addSource.click();
  }
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
  const consentStatus = page.locator('.frappe-control[data-fieldname="consent_status"]');
  const statusBefore = await consentStatus.innerText();
  await page.screenshot({ path: info.outputPath("contacts-source-linked-native-form.png"), fullPage: true });
  const consentHistory = page.locator('.frappe-control[data-fieldname="consent_history"]');
  if (statusBefore.includes("Unknown")) {
    await expect(consentHistory).toContainText("No consent evidence has been recorded.");
  } else {
    await expect(consentStatus).toContainText("Granted");
    await expect(consentHistory).toContainText("synthetic-browser-evidence");
  }
  await page.screenshot({ path: info.outputPath("contacts-consent-evidence-panel.png"), fullPage: true });
  if (statusBefore.includes("Unknown")) {
    await page.getByRole("button", { name: "Consent", exact: true }).click();
    await page.getByRole("menuitem", { name: "Record Consent", exact: true }).click();
    const consentDialog = page.locator(".modal.show").filter({ has: page.getByRole("heading", { name: "Record Marketing Consent" }) });
    await expect(consentDialog).toBeVisible();
    await consentDialog.locator('.frappe-control[data-fieldname="notice_version"] input').fill("browser-consent-v1");
    await consentDialog.locator('.frappe-control[data-fieldname="evidence_reference"] textarea').fill("synthetic-browser-evidence");
    await consentDialog.getByRole("button", { name: "Record Consent", exact: true }).click();
    await expect(consentStatus).toContainText("Granted", { timeout: 30_000 });
    await expect(consentHistory).toContainText("synthetic-browser-evidence");
  }
  await page.screenshot({ path: info.outputPath("contacts-consent-history-recorded.png"), fullPage: true });
});

test("Marketing Manager completes a private CSV preview and confirmation in native Desk", async ({ page, accounts }, info) => {
  test.setTimeout(120_000);
  await login(page, accounts.audience_manager, info.project.use.colorScheme === "dark" ? "dark" : "light");
  await page.evaluate(() => (window as any).frappe.set_route("List", "WA Contact", "List"));
  let importAction = page.getByRole("button", { name: "Import CSV", exact: true });
  if (info.project.name === "mobile") {
    await page.getByRole("button", { name: "Menu", exact: true }).click();
    importAction = page.getByRole("menuitem", { name: "Import CSV", exact: true });
  }
  await expect(importAction).toBeVisible({ timeout: 30_000 });
  await importAction.click();
  const filename = `wa-browser-import-${accounts.run_id}-${info.project.name}.csv`;
  await page.locator('input[type="file"]').last().setInputFiles({
    name: filename,
    mimeType: "text/csv",
    buffer: Buffer.from(`Name,Mobile\nBrowser Synthetic,${accounts.phone}\n`),
  });
  await page.getByRole("button", { name: "Upload", exact: true }).click();
  const mapping = page.locator(".modal.show").filter({ has: page.getByRole("heading", { name: "Map CSV columns" }) });
  await expect(mapping).toBeVisible({ timeout: 30_000 });
  await mapping.locator('.frappe-control[data-fieldname="phone"] select').selectOption("Mobile");
  await mapping.locator('.frappe-control[data-fieldname="display_name"] select').selectOption("Name");
  await mapping.locator('.frappe-control[data-fieldname="default_country_code"] input').fill("ZA");
  const createResponsePromise = page.waitForResponse(response => response.url().includes("create_import_batch"));
  await mapping.getByRole("button", { name: "Validate preview", exact: true }).click();
  const createResponse = await createResponsePromise;
  const createPayload = await createResponse.json();
  const safeFailure = {
    status: createResponse.status(),
    response_keys: Object.keys(createPayload || {}),
    error_code: createPayload?.message?.error?.code,
    exception_class: typeof createPayload?.exc_type === "string" ? createPayload.exc_type : undefined,
    exception_summary: typeof createPayload?.exception === "string" ? createPayload.exception.split("\n")[0] : undefined,
  };
  expect(createResponse.ok(), JSON.stringify(safeFailure)).toBeTruthy();
  expect(createPayload.message?.ok, JSON.stringify(safeFailure)).toBe(true);
  await expect(page.locator('.frappe-control[data-fieldname="status"]')).toContainText("Preview Ready", { timeout: 30_000 });
  await expect(page.locator('.frappe-control[data-fieldname="valid_count"]')).toContainText("1");
  await expect(page.locator('.frappe-control[data-fieldname="evidence_missing_count"]')).toContainText("1");
  await page.screenshot({ path: info.outputPath("contacts-private-csv-preview.png"), fullPage: true });
  const confirm = page.getByRole("button", { name: "Confirm Import", exact: true });
  if (info.project.name === "mobile") {
    await page.getByRole("button", { name: "Menu", exact: true }).click();
    await page.getByRole("menuitem", { name: "Import", exact: true }).click();
    await page.getByRole("menuitem", { name: "Confirm Import", exact: true }).click();
  } else {
    const importMenu = page.getByRole("button", { name: "Import", exact: true });
    if (await importMenu.isVisible().catch(() => false)) await importMenu.click();
    if (!(await confirm.isVisible().catch(() => false))) await page.getByRole("menuitem", { name: "Confirm Import", exact: true }).click();
    else await confirm.click();
  }
  const confirmDialog = page.locator(".modal.show").filter({ has: page.getByRole("heading", { name: "Confirm contact import" }) });
  await expect(confirmDialog).toBeVisible();
  await confirmDialog.getByRole("button", { name: "Confirm Import", exact: true }).click();
  const progress = page.locator(".modal.show").filter({ has: page.getByRole("heading", { name: "Operation progress" }) });
  await expect(progress.getByRole("heading", { name: "Succeeded" })).toBeVisible({ timeout: 30_000 });
  await progress.getByRole("button", { name: "Close", exact: true }).last().click();
  await page.evaluate(async () => await (window as any).cur_frm.reload_doc());
  await expect(page.locator('.frappe-control[data-fieldname="status"]')).toContainText("Completed", { timeout: 30_000 });
  await page.screenshot({ path: info.outputPath("contacts-private-csv-complete.png"), fullPage: true });
});
