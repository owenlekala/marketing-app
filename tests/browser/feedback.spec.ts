import { test, expect, login } from "./fixtures";

test("Inbox feedback recovers from a real offline query using native controls", async ({ page, accounts }, info) => {
 await login(page, accounts.marketing_manager, info.project.use.colorScheme === "dark" ? "dark" : "light");
 await page.evaluate(() => (window as any).frappe.set_route("wa-inbox"));
 await expect(page.getByRole("heading", { name: "Inbox unavailable", exact: true })).toBeVisible({ timeout: 30_000 });
 await page.context().setOffline(true);
 await page.getByRole("button", { name: "Refresh", exact: true }).click();
 await expect(page.getByRole("heading", { name: "Unable to load Inbox", exact: true })).toBeVisible({ timeout: 30_000 });
 await expect(page.getByText("Connection lost. Check your connection and retry this query.", { exact: true })).toBeVisible();
 await page.context().setOffline(false);
 const retry = page.getByRole("button", { name: "Retry", exact: true });
 await retry.focus(); await retry.press("Enter");
 await expect(page.getByRole("heading", { name: "Inbox unavailable", exact: true })).toBeVisible({ timeout: 30_000 });
 await expect(page.getByRole("button", { name: "Refresh", exact: true })).toBeFocused();
 await page.screenshot({ path: info.outputPath("native-feedback-recovered.png"), fullPage: true });
});

test("native progress dialogs read every persisted state and stop polling on close", async ({ page, accounts }, info) => {
 await login(page, accounts.manager, info.project.use.colorScheme === "dark" ? "dark" : "light");
 const trigger = page.getByRole("button", { name: /^Search/ }).first();
 let reads = 0;
 page.on("request", request => { if (request.url().includes("tag_marketing.api.operations.get")) reads++; });
 for (const state of ["Pending", "Running", "Succeeded", "Failed", "Cancelled"] as const) {
  await trigger.focus();
  await page.evaluate(id => { (window as any).tag_marketing.ui.show_operation(id); }, accounts.operations[state]);
  const dialog = page.getByRole("dialog");
  await expect(dialog).toHaveCSS("opacity", "1");
  await expect(dialog.getByRole("heading", { name: state, exact: true })).toBeVisible({ timeout: 30_000 });
  await expect(dialog.getByRole("progressbar", { name: "Operation progress", exact: true })).toHaveAttribute("aria-valuenow", state === "Succeeded" ? "100" : state === "Pending" ? "0" : "35");
  if (state === "Succeeded") await page.screenshot({ path: info.outputPath("native-operation-progress.png"), fullPage: true });
  await dialog.locator(".modal-footer").getByRole("button", { name: "Close", exact: true }).click();
  await expect(trigger).toBeFocused();
 }
 const closedReads = reads;
 await page.waitForTimeout(3500); // Beyond the documented polling interval: closing must stop future reads.
 expect(reads).toBe(closedReads);
});

test("native permission errors and stale renderer content are safe and require explicit review", async ({ page, accounts }, info) => {
 test.skip(info.project.name !== "desktop-light", "Permission/escaping semantics covered once; stateful dialogs cover the visual matrix");
 await login(page, accounts.agent, "light");
 await page.context().setOffline(true);
 const uncertain = await page.evaluate(async () => {
  const ui = (window as any).tag_marketing.ui;
  const button = document.createElement("button");
  const first = ui.request("tag_marketing.api.operations.get", {}, { command: true, button });
  const duplicate = ui.request("tag_marketing.api.operations.get", {}, { command: true, button });
  const suppressed = first === duplicate && button.disabled;
  try { await first; return null; }
  catch (error: any) { return { code: error.code, retryable: error.retryable, suppressed, restored: !button.disabled }; }
 });
 expect(uncertain).toEqual({ code: "UNCONFIRMED", retryable: false, suppressed: true, restored: true });
 await page.context().setOffline(false);
 await page.evaluate(async () => {
  const ui = (window as any).tag_marketing.ui;
  try { await ui.request("tag_marketing.api.navigation.summary"); }
  catch (error) { ui.show_error(error); }
 });
 let dialog = page.getByRole("dialog");
 await expect(dialog.getByText("You do not have permission to perform this action.", { exact: true })).toBeVisible();
 await expect(dialog.locator("pre")).toHaveCount(0);
 await dialog.locator(".modal-footer").getByRole("button", { name: "Close", exact: true }).click();
 await page.evaluate(() => {
  const ui = (window as any).tag_marketing.ui;
  (window as any).wa_review_count = 0;
  ui.show_error(new ui.RequestError("STALE_DOCUMENT", '<img src=x onerror="window.wa_executed=1">', { field: "expected_modified" }), { on_reload: () => { (window as any).wa_review_count++; } });
 });
 dialog = page.getByRole("dialog");
 await expect(dialog.getByText('<img src=x onerror="window.wa_executed=1">', { exact: true })).toBeVisible();
 await expect(dialog.locator("img")).toHaveCount(0);
 expect(await page.evaluate(() => (window as any).wa_executed)).toBeUndefined();
 expect(await page.evaluate(() => (window as any).wa_review_count)).toBe(0);
 await dialog.getByRole("button", { name: "Reload and review", exact: true }).click();
 expect(await page.evaluate(() => (window as any).wa_review_count)).toBe(1);
});
