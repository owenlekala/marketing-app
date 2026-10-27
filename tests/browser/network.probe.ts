import { test } from "./fixtures";

test("egress:http", async ({ page }) => {
  await page.evaluate(async () => {
    try { await fetch("https://provider.invalid/never-send"); } catch { /* Guard teardown must fail. */ }
  });
});

test("egress:websocket", async ({ page }) => {
  await page.evaluate(() => new Promise<void>(resolve => {
    const socket = new WebSocket("wss://provider.invalid/never-send");
    socket.onclose = () => resolve();
    socket.onerror = () => resolve();
  }));
});

test("egress:api", async ({ request }) => {
  try { await request.get("https://provider.invalid/never-send"); } catch { /* Guard teardown must fail. */ }
});
