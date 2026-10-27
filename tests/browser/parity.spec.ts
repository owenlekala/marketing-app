import { test, expect, login } from "./fixtures";

const themeFor = (info: import("@playwright/test").TestInfo) =>
	info.project.use.colorScheme === "dark" ? "dark" : "light";

async function desk(page: import("@playwright/test").Page, ...route: string[]) {
	await page.evaluate((parts) => (window as any).frappe.set_route(...parts), route);
}

async function openWorkspace(page: import("@playwright/test").Page, slug: string, name: string, marker: string, theme: "light" | "dark") {
	await page.goto(`/desk/${slug}`);
	await page.waitForFunction(() => Boolean((window as any).frappe?.ui?.set_theme), undefined, { timeout: 30_000 });
	await page.evaluate((value) => {
		document.documentElement.setAttribute("data-theme-mode", value);
		(window as any).frappe.ui.set_theme(value);
	}, theme);
	await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
	await page.waitForFunction((expected) => {
		const f = (window as any).frappe;
		return f?.router?.current_route?.[0] === "Workspaces" && f.router.current_route[1] === expected && f.workspace?._page?.name === expected;
	}, name, { timeout: 30_000 });
	await expect(page.locator("#editorjs")).toContainText(marker, { timeout: 30_000 });
}

async function capture(page: import("@playwright/test").Page, info: { outputPath: (name: string) => string }, name: string) {
	const viewport = await page.evaluate(() => ({ width: window.innerWidth, height: window.innerHeight }));
	await page.mouse.move(viewport.width - 2, viewport.height - 2);
	await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
	await page.screenshot({ path: info.outputPath(`parity-${name}.png`), fullPage: true });
}

test("same-user native ERPNext and marketing Desk parity evidence", async ({ page, accounts }, info) => {
	await login(page, accounts.parity, themeFor(info));
	await page.setViewportSize(info.project.name === "mobile" ? { width: 390, height: 844 } : info.project.name === "tablet" ? { width: 1024, height: 768 } : { width: 1440, height: 900 });

	// Pair the standard workspace shell and responsive navigation.
	await openWorkspace(page, "crm", "CRM", "Incoming Leads", themeFor(info));
	await capture(page, info, "erpnext-crm-workspace");
	await page.getByRole("button", { name: "Search", exact: true }).click();
	const erpnextSearch = page.getByRole("dialog");
	await expect(erpnextSearch).toBeVisible();
	await capture(page, info, "erpnext-native-dialog");
	await page.keyboard.press("Escape");
	await expect(erpnextSearch).toBeHidden();
	await openWorkspace(page, "whatsapp-marketing", "WhatsApp Marketing", "Sending is disabled", themeFor(info));
	await expect.poll(() => page.locator("#editorjs").getByText("N/A", { exact: true }).count()).toBeGreaterThanOrEqual(5);
	await capture(page, info, "marketing-workspace");
	await page.getByRole("button", { name: "Search", exact: true }).click();
	const marketingSearch = page.getByRole("dialog");
	await expect(marketingSearch).toBeVisible();
	await capture(page, info, "marketing-native-dialog");
	await page.keyboard.press("Escape");
	await expect(marketingSearch).toBeHidden();

	// Pair native CRM and marketing list views; no business records are created.
	await desk(page, "List", "Lead");
	const addLeadLabel = info.project.name === "mobile" ? "Add" : "Add Lead";
	await expect(page.getByRole("button", { name: addLeadLabel, exact: true })).toBeVisible({ timeout: 30_000 });
	await capture(page, info, "erpnext-lead-list");
	await desk(page, "List", "WA Connection");
	await expect(page.getByRole("link", { name: /WA Harness/ })).toBeVisible({ timeout: 30_000 });
	await capture(page, info, "marketing-connection-list");

	// Compare a native unsaved CRM form with the owned read-only settings form.
	await page.evaluate(() => (window as any).frappe.new_doc("Lead"));
	await expect(page.locator('.frappe-control[data-fieldname="first_name"] input')).toBeVisible({ timeout: 30_000 });
	const leadName = page.locator('.frappe-control[data-fieldname="first_name"] input');
	await leadName.focus();
	await expect(leadName).toBeFocused();
	await page.keyboard.press("Tab");
	expect(await page.evaluate(() => document.activeElement?.matches(":focus-visible"))).toBe(true);
	await capture(page, info, "erpnext-lead-form");
	await desk(page, "Form", "WA Settings");
	const marketingCompany = page.locator('.frappe-control[data-fieldname="marketing_company"] input');
	await expect(marketingCompany).toBeVisible();
	await marketingCompany.focus();
	await expect(marketingCompany).toBeFocused();
	await page.keyboard.press("Tab");
	expect(await page.evaluate(() => document.activeElement?.matches(":focus-visible"))).toBe(true);
	await capture(page, info, "marketing-settings-form");

	// A CRM report is available to this role; the unimplemented marketing report
	// must present its safe unavailable state rather than fabricated metrics.
	await desk(page, "query-report", "Lead Details");
	await expect(page.locator(".report-wrapper, .report-container").first()).toBeVisible({ timeout: 30_000 });
	await capture(page, info, "erpnext-lead-details-report");
	await desk(page, "query-report", "WA Campaign Performance");
	const unavailableReport = page.getByRole("dialog");
	await expect(unavailableReport).toBeVisible({ timeout: 30_000 });
	await expect(unavailableReport.getByText("This report is not available yet", { exact: false })).toBeVisible();
	await capture(page, info, "marketing-unavailable-report");
});

test("restricted roles receive native permission denial for connection records", async ({ page, accounts }) => {
	await login(page, accounts.agent, "light");
	const response = await page.request.get(`/api/resource/WA%20Connection/${encodeURIComponent(accounts.connection)}`);
	expect(response.status()).toBe(403);
	await page.evaluate((name) => (window as any).frappe.set_route("Form", "WA Connection", name), accounts.connection);
	const deniedDialog = page.getByRole("dialog");
	await expect(deniedDialog).toBeVisible({ timeout: 30_000 });
	await expect(deniedDialog.getByText(/permission|access/i).first()).toBeVisible();
});
