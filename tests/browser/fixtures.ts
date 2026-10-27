import { readFileSync } from "node:fs";
import { test as base, expect, type APIRequestContext, type Page } from "@playwright/test";

export type Identity = { username: string; password: string };
type Accounts = Record<"parity" | "agent" | "manager" | "marketing" | "marketing_manager" | "analyst" | "inbox", Identity> & { connection: string; operations: Record<"Pending" | "Running" | "Succeeded" | "Failed" | "Cancelled", string> };
import { allowed, baseURL, pageRealtime, realtime } from "./target";


function restrictRequest(original: APIRequestContext, blocked: string[]): APIRequestContext {
  return new Proxy(original, {
    get(target, key) {
      const value = Reflect.get(target, key, target);
      if (typeof value !== "function") return value;
      return (...args: any[]) => {
        if (["get", "post", "put", "patch", "delete", "head", "fetch"].includes(String(key))) {
          const raw = typeof args[0] === "string" ? args[0] : args[0].url();
          const origin = new URL(raw, baseURL).origin;
          if (!allowed.has(origin)) {
            blocked.push(origin);
            throw new Error("Unexpected outbound request from browser API client");
          }
        }
        // Redirect targets must be validated by another explicit request.
        if (["get", "post", "put", "patch", "delete", "head", "fetch"].includes(String(key))) {
          args[1] = { ...args[1], maxRedirects: 0 };
        }
        return Reflect.apply(value, target, args);
      };
    }
  });
}

export const test = base.extend<{ accounts: Accounts }>({
  accounts: async ({}, use) => {
    const path = process.env.WA_TEST_USERS;
    if (!path) throw new Error("Prepare the disposable browser fixtures through quality.py");
    await use(JSON.parse(readFileSync(path, "utf8")) as Accounts);
  },
  request: async ({ request }, use) => {
    const blocked: string[] = [];
    await use(restrictRequest(request, blocked));
    expect(blocked, "WA_EGRESS_GUARD: unexpected API fixture destination").toEqual([]);
  },
  context: async ({ context }, use) => {
    const blocked: string[] = [];
    Object.defineProperty(context, "request", { value: restrictRequest(context.request, blocked), configurable: true });
    context.on("request", request => {
      const origin = new URL(request.url()).origin;
      if (!allowed.has(origin)) blocked.push(origin);
    });
    await context.route("**/*", async route => {
      const origin = new URL(route.request().url()).origin;
      if (origin === pageRealtime.origin) {
        // Route native dev-server polling to its real separate Compose service.
        const target = new URL(route.request().url());
        target.hostname = realtime.hostname;
        await route.continue({ url: target.toString() });
      } else if (allowed.has(origin)) await route.continue();
      else {
        blocked.push(origin);
        await route.abort("blockedbyclient");
      }
    });
    await context.routeWebSocket(/.*/, async socket => {
      const origin = new URL(socket.url()).origin;
      if (allowed.has(origin)) socket.connectToServer();
      else {
        blocked.push(origin);
        await socket.close();
      }
    });
    await use(context);
    expect(blocked, "WA_EGRESS_GUARD: unexpected browser destination").toEqual([]);
  }
});

export { expect };


export async function login(page: Page, identity: Identity, theme: "light" | "dark") {
  await page.goto("/login");
  await page.locator("#login_email").fill(identity.username);
  await page.locator("#login_password").fill(identity.password);
  await page.locator("#login_password").press("Enter");
  // Authentication navigates before the large native Desk assets finish loading.
  // Commit and application readiness are distinct, bounded checks; no retries.
  await page.waitForURL(/\/(app|desk)(\/|$)/, { waitUntil: "commit", timeout: 60_000 });
  await page.waitForFunction(() => Boolean(
    (window as any).frappe?.app?.sidebar &&
    typeof (window as any).frappe?.ui?.set_theme === "function"
  ), undefined, { timeout: 60_000 });
  await page.evaluate(theme => {
    document.documentElement.setAttribute("data-theme-mode", theme);
    (window as any).frappe.ui.set_theme(theme);
  }, theme);
  await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
}
