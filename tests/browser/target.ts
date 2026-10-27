// Compose owns the service address; the runtime lock owns the realtime port.
if (!process.env.WA_BASE_URL || !process.env.WA_REALTIME_PORT) {
  throw new Error("Run browser checks through the locked quality controller");
}
export const baseURL = process.env.WA_BASE_URL;
export const pageRealtime = new URL(baseURL);
pageRealtime.port = process.env.WA_REALTIME_PORT;
export const realtime = new URL(pageRealtime);
realtime.hostname = "realtime";
export const allowed = new Set([
  new URL(baseURL).origin, pageRealtime.origin, realtime.origin,
  pageRealtime.origin.replace("http:", "ws:"), realtime.origin.replace("http:", "ws:")
]);
