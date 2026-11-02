const pending = new WeakMap();
const terminal = new Set(["Succeeded", "Failed", "Cancelled"]);

export class RequestError extends Error {
 constructor(code, message, { field = null, correlation_id = null, retryable = false } = {}) {
  super(message); Object.assign(this, { code, field, correlation_id, retryable });
 }
}

export function new_request_id() {
 const bytes = globalThis.crypto?.getRandomValues?.(new Uint8Array(16));
 if (!bytes) throw new RequestError("UNAVAILABLE", __("Secure request identifiers are unavailable in this browser."));
 bytes[6] = (bytes[6] & 0x0f) | 0x40;
 bytes[8] = (bytes[8] & 0x3f) | 0x80;
 const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
 return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

export function normalize_error(status, payload, command = false) {
 const error = payload?.message?.ok === false ? payload.message.error : null;
 if (error && /^[A-Z_]{1,64}$/.test(error.code || "")) {
  return new RequestError(error.code, typeof error.message === "string" ? error.message.slice(0, 500) : __("Request failed."), {
   field: /^[a-z_]{1,64}$/.test(error.field || "") ? error.field : null,
   correlation_id: /^[a-f0-9]{32}$/.test(error.correlation_id || "") ? error.correlation_id : null,
   retryable: !command && error.retryable === true,
  });
 }
 const messages = { 401: __("Your session expired. Sign in again."), 403: __("You do not have permission to perform this action."), 404: __("This record is unavailable or outside your permitted scope.") };
 if (!status) return new RequestError(command ? "UNCONFIRMED" : "NETWORK_ERROR", command
  ? __("The request outcome is unconfirmed. Check operation status before trying again.")
  : __("Connection lost. Check your connection and retry this query."), { retryable: !command });
 return new RequestError("REQUEST_FAILED", messages[status] || __("Unable to complete this request."));
}

export function request(method, args = {}, { command = false, button = null } = {}) {
 if (!/^tag_marketing\.api\.[a-z_]+\.[a-z_]+$/.test(method)) return Promise.reject(new RequestError("INVALID_INPUT", __("Unsupported marketing method.")));
 const element = button?.jquery ? button[0] : button;
 const key = JSON.stringify([method, args, command]);
 if (element && pending.has(element)) {
  const previous = pending.get(element);
  return previous.key === key ? previous.promise : Promise.reject(new RequestError("REQUEST_PENDING", __("An action is already running.")));
 }
 const disabled = element?.disabled;
 if (element) element.disabled = true;
 const promise = (async () => {
  const query = new URLSearchParams();
  for (const [name, value] of Object.entries(args)) if (value !== undefined) query.set(name, typeof value === "object" ? JSON.stringify(value) : String(value));
  let response;
  try {
   response = await fetch(`/api/method/${method}${command ? "" : "?" + query}`, {
    method: command ? "POST" : "GET", credentials: "same-origin",
    headers: { "Accept": "application/json", ...(command ? { "Content-Type": "application/json", "X-Frappe-CSRF-Token": frappe.csrf_token } : {}) },
    ...(command ? { body: JSON.stringify(args) } : {}),
   });
  } catch { throw normalize_error(0, null, command); }
  let payload;
  try { payload = await response.json(); } catch { throw normalize_error(response.status, null, command); }
  if (!response.ok || payload?.message?.ok === false) throw normalize_error(response.status, payload, command);
  if (!Object.prototype.hasOwnProperty.call(payload, "message")) throw new RequestError("INVALID_RESPONSE", __("The server returned an invalid response."));
  return payload.message?.ok === true ? payload.message.data : payload.message;
 })().finally(() => { if (element) { element.disabled = disabled; pending.delete(element); } });
 if (element) pending.set(element, { key, promise });
 return promise;
}

export function render_state(container, { title, message, loading = false, action = null }) {
 const body = $(container).empty().addClass("tag-marketing").attr({ "aria-busy": String(loading) });
 const state = $("<section class='wa-state' role='status' aria-live='polite'></section>").appendTo(body);
 $("<h4></h4>").text(title).appendTo(state);
 $("<p class='text-muted'></p>").text(message || "").appendTo(state);
 if (action) $("<button type='button' class='btn btn-default'></button>").text(action.label).on("click", action.run).appendTo(state);
 return state;
}

function restore_focus(element) {
 window.setTimeout(() => { if (element?.isConnected && !window.cur_dialog) element.focus({ preventScroll: true }); }, 0);
}

export function show_error(error, { on_reload = null, trigger = document.activeElement } = {}) {
 const dialog = new frappe.ui.Dialog({ title: error.code === "STALE_DOCUMENT" ? __("Review changes") : __("Unable to complete action"), fields: [{ fieldname: "feedback", fieldtype: "HTML" }] });
 const state = render_state(dialog.fields_dict.feedback.$wrapper, { title: __("Action needs attention"), message: error.message || __("Request failed.") });
 if (error.correlation_id) $("<p class='text-muted'></p>").text(__("Reference: {0}", [error.correlation_id])).appendTo(state);
 if (error.field) $("<p></p>").text(__("Check field: {0}", [error.field])).appendTo(state);
 dialog.set_primary_action(__("Close"), () => dialog.hide());
 if (error.code === "STALE_DOCUMENT" && on_reload) { dialog.set_secondary_action_label(__("Reload and review")); dialog.set_secondary_action(() => { dialog.hide(); on_reload(); }); }
 dialog.$wrapper.one("hidden.bs.modal", () => restore_focus(trigger));
 dialog.show();
 return dialog;
}

export function show_operation(operation, { trigger = document.activeElement, on_succeeded = null } = {}) {
 if (typeof operation !== "string" || !operation || operation.length > 140) throw new RequestError("INVALID_INPUT", __("Choose a valid operation."));
 const dialog = new frappe.ui.Dialog({ title: __("Operation progress"), fields: [
  { fieldname: "operation", fieldtype: "Data", label: __("Operation"), read_only: 1, default: operation },
  { fieldname: "progress", fieldtype: "HTML" },
 ] });
 let closed = false, timer = null, inflight = false, last = null, notified = false;
 const body = dialog.fields_dict.progress.$wrapper;
 dialog.set_primary_action(__("Close"), () => dialog.hide());
 dialog.set_secondary_action_label(__("Refresh status"));
 const refresh = async () => {
  if (closed || inflight) return;
  window.clearTimeout(timer); inflight = true;
  if (!last) render_state(body, { title: __("Loading..."), message: __("Retrieving saved operation status."), loading: true });
  try {
   const data = await request("tag_marketing.api.operations.get", { operation }, { button: dialog.get_secondary_btn() });
   if (closed) return;
   const signature = JSON.stringify([data.status, data.progress_percent, data.error]);
   if (last !== signature) {
    const labels = { Pending: __("Pending"), Running: __("Running"), Succeeded: __("Succeeded"), Failed: __("Failed"), Cancelled: __("Cancelled") };
    const state = render_state(body, { title: labels[data.status] || __("Unavailable"), message: data.error?.message || __("Progress: {0}%", [data.progress_percent]) });
    $("<div class='progress'></div>").append($("<div class='progress-bar' role='progressbar'></div>").attr({ "aria-valuenow": data.progress_percent, "aria-valuemin": 0, "aria-valuemax": 100, "aria-label": __("Operation progress") }).css("width", data.progress_percent + "%")).appendTo(state);
    last = signature;
   }
   if (data.status === "Succeeded" && !notified && typeof on_succeeded === "function") {
    notified = true;
    dialog.hide();
    on_succeeded(data.result);
    return;
   }
   if (!terminal.has(data.status)) timer = window.setTimeout(refresh, 3000);
  } catch (error) {
   if (!closed) { last = null; render_state(body, { title: __("Status unavailable"), message: error.message }); }
  } finally { inflight = false; }
 };
 dialog.set_secondary_action(refresh);
 dialog.onhide = () => { closed = true; window.clearTimeout(timer); };
 dialog.$wrapper.one("hidden.bs.modal", () => restore_focus(trigger));
 dialog.show(); refresh();
 return dialog;
}
