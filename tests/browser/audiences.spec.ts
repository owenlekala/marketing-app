import { test, expect, login } from "./fixtures";

test("Marketing Manager edits, previews and disables a bounded audience segment", async ({ page, accounts }, info) => {
  test.setTimeout(120_000);
  await login(page, accounts.audience_manager, info.project.use.colorScheme === "dark" ? "dark" : "light");
  const segmentLabel = `Browser Segment ${accounts.run_id} ${info.project.name}`;
  await page.evaluate(async ({ source, phone }) => {
    const ui = (window as any).tag_marketing?.ui;
    if (!ui) throw new Error("Marketing commands are not available in Desk");
    await ui.request("tag_marketing.api.audiences.add_source", {
      source_doctype: "Lead",
      source_name: source,
      selected_phone: phone,
      country_code: "ZA",
      include_unassigned_lead: false,
    }, { command: true });
  }, { source: accounts.source, phone: accounts.phone });
  await page.evaluate(() => (window as any).frappe.set_route("List", "WA Audience Segment", "List"));
  let create = page.getByRole("button", { name: "New audience segment", exact: true });
  if (info.project.name === "mobile") {
    await page.getByRole("button", { name: "Menu", exact: true }).click();
    create = page.getByRole("menuitem", { name: "New audience segment", exact: true });
  }
  await expect(create).toBeVisible({ timeout: 30_000 });
  await create.click();
  const createDialog = page.locator(".modal.show").filter({ has: page.getByRole("heading", { name: "New audience segment" }) });
  await createDialog.locator('.frappe-control[data-fieldname="segment_name"] input').fill(segmentLabel);
  const saveResponsePromise = page.waitForResponse(response => response.url().includes("save_audience_segment"));
  await createDialog.getByRole("button", { name: "Create", exact: true }).click();
  const saveResponse = await saveResponsePromise;
  const savedSegment = await saveResponse.json();
  expect(saveResponse.ok(), JSON.stringify(savedSegment)).toBeTruthy();
  expect(savedSegment.message?.ok, JSON.stringify(savedSegment)).toBe(true);
  const segmentName = savedSegment.message.data.name as string;
  await expect.poll(() => page.evaluate(() => (window as any).frappe.get_route())).toEqual(["Form", "WA Audience Segment", segmentName]);
  await expect(page.locator('.form-layout .frappe-control[data-fieldname="segment_name"] input')).toHaveValue(segmentLabel, { timeout: 30_000 });

  const formAction = async (label: string) => {
    let action = page.getByRole("button", { name: label, exact: true });
    if (info.project.name === "mobile") {
      await page.locator(".menu-more-button:visible").last().click();
      action = page.getByRole("menuitem", { name: label, exact: true });
    }
    await action.click();
  };
  await formAction("Edit audience");
  const editDialog = page.locator(".modal.show").filter({ has: page.getByRole("heading", { name: "Edit audience filters" }) });
  await expect(editDialog.locator('.frappe-control[data-fieldname="filters_json"]')).toBeVisible();
  const definition = JSON.stringify({
    version: 1,
    logic: "and",
    rules: [{ field: "source_type", operator: "equals", value: "Lead" }],
    groups: [],
  }, null, 2);
  const editor = editDialog.locator('.frappe-control[data-fieldname="filters_json"] .ace_content');
  await editor.click();
  await page.keyboard.press("Control+A");
  await page.keyboard.insertText(definition);
  await page.keyboard.press("Tab");
  await editDialog.getByRole("button", { name: "Save filters", exact: true }).click();
  await expect(page.locator('.frappe-control[data-fieldname="filters_json"]').first()).toContainText('"source_type"', { timeout: 30_000 });

  await formAction("Preview audience");
  const preview = page.locator(".modal.show").filter({ has: page.getByRole("heading", { name: "Audience preview" }) });
  await expect(preview.locator('[data-fieldname="result"]')).toContainText("Live advisory preview", { timeout: 30_000 });
  await expect(preview.locator('[data-fieldname="result"]')).toContainText("Eligible");
  await expect(preview.locator('[data-fieldname="result"]')).toContainText("Unknown consent: 1");
  await expect(preview.locator('[data-fieldname="result"]')).toContainText("No eligible contacts match these filters.");
  await page.screenshot({ path: info.outputPath("audience-segment-preview.png"), fullPage: true });
  await preview.getByRole("button", { name: "Close", exact: true }).last().click();

  await formAction("Disable");
  await expect(page.locator('.frappe-control[data-fieldname="disabled"] input')).toHaveClass(/disabled-selected/, { timeout: 30_000 });
  await expect(page.getByRole("button", { name: "Preview audience", exact: true })).toHaveCount(0);
});

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
