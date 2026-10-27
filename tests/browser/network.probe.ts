import { test } from "./fixtures";

test("deliberate external traffic must fail even when its error is caught", async ({ page }) => {
  await page.goto("/login");
  await page.evaluate(async () => {
    try { await fetch("https://provider.invalid/never-send"); } catch { /* Teardown must still fail. */ }
  });
});
