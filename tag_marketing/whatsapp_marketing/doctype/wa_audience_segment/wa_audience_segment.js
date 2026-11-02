frappe.ui.form.on("WA Audience Segment", {
	refresh(frm) {
		frm.disable_save();
		if (frm.is_new()) return;
		frm.add_custom_button(__("Edit audience"), () => edit_segment(frm));
		if (!frm.doc.disabled) frm.add_custom_button(__("Preview audience"), () => preview_segment(frm));
		frm.add_custom_button(frm.doc.disabled ? __("Enable") : __("Disable"), async (button) => {
			try {
				await tag_marketing.ui.request("tag_marketing.api.audiences.disable_audience_segment", {
					segment: frm.doc.name,
					disabled: !frm.doc.disabled,
					expected_modified: frm.doc.modified,
				}, { command: true, button });
				await frm.reload_doc();
			} catch (error) {
				tag_marketing.ui.show_error(error, { on_reload: () => frm.reload_doc(), trigger: button });
			}
		});
	},
});

function edit_segment(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Edit audience filters"),
		fields: [
			{ fieldname: "segment_name", fieldtype: "Data", label: __("Segment name"), reqd: 1, default: frm.doc.segment_name },
			{
				fieldname: "filters_json",
				fieldtype: "Code",
				label: __("Versioned filter definition (JSON)"),
				options: "JSON",
				reqd: 1,
				description: __("Use version 1 with AND/OR groups. Allowed fields include tag, language, source_type, created_on, archived and the documented Lead, Customer, Contact and Sales Order attributes. The server enforces the exact allowlist, operators and limits."),
				default: JSON.stringify(parse_filters(frm.doc.filters_json), null, 2),
			},
		],
		primary_action_label: __("Save filters"),
		primary_action: async () => {
			const values = dialog.get_values();
			if (!values) return;
			try {
				const filters = JSON.parse(values.filters_json);
				const saved = await tag_marketing.ui.request("tag_marketing.api.audiences.save_audience_segment", {
					segment_name: values.segment_name,
					filters,
					segment: frm.doc.name,
					expected_modified: frm.doc.modified,
				}, { command: true, button: dialog.get_primary_btn() });
				dialog.hide();
				await frm.reload_doc();
				frappe.show_alert({ message: __("Audience filters saved"), indicator: "green" });
			} catch (error) {
				tag_marketing.ui.show_error(error, { on_reload: () => frm.reload_doc() });
			}
		},
	});
	dialog.show();
}

function preview_segment(frm) {
	let cursor = "";
	const dialog = new frappe.ui.Dialog({
		title: __("Audience preview"),
		fields: [
			{ fieldname: "exclusions", fieldtype: "Code", label: __("Exclusions (JSON, optional)"), options: "JSON", default: '{"contacts":[],"tags":[]}' },
			{ fieldname: "result", fieldtype: "HTML" },
		],
		primary_action_label: __("Preview"),
		primary_action: async () => {
			cursor = "";
			await load_preview(frm, dialog, cursor);
		},
	});
	dialog.show();
	load_preview(frm, dialog, cursor);
}

async function load_preview(frm, dialog, cursor) {
	const values = dialog.get_values() || {};
	let exclusions;
	try {
		exclusions = JSON.parse(values.exclusions || "{}");
	} catch (_error) {
		frappe.msgprint(__("Exclusions must be valid JSON."));
		return;
	}
	try {
		const result = await tag_marketing.ui.request("tag_marketing.api.audiences.preview", {
			segment: frm.doc.name,
			exclusions,
			limit: 20,
			cursor: cursor || "",
			request_id: tag_marketing.ui.new_request_id(),
		}, { command: true, button: dialog.get_primary_btn() });
		if (result.operation) {
			dialog.hide();
			tag_marketing.ui.show_operation(result.operation, {
				trigger: frm.page.btn_primary,
				on_succeeded: (previewResult) => {
					dialog.show();
					render_preview_result(frm, dialog, previewResult);
				},
			});
			return;
		}
		render_preview_result(frm, dialog, result.preview);
	} catch (error) {
		tag_marketing.ui.show_error(error, { on_reload: () => frm.reload_doc() });
	}
}

function render_preview_result(frm, dialog, result) {
	const rows = result.items.map((item) => `<li>${frappe.utils.escape_html(item.display_name || item.name)} · ${frappe.utils.escape_html(item.phone)}</li>`).join("");
	const excluded = result.excluded;
	dialog.fields_dict.result.$wrapper.html(
		`<p>${__("Matched")}: ${result.matched_count} · ${__("Eligible")}: ${result.eligible_count}</p>` +
		`<p>${__("Suppressed")}: ${excluded.suppressed} · ${__("Archived")}: ${excluded.archived} · ${__("Withdrawn")}: ${excluded.withdrawn} · ${__("Unknown consent")}: ${excluded.unknown_consent}</p>` +
		`<ul>${rows || `<li>${__("No eligible contacts match these filters.")}</li>`}</ul>` +
		(result.next_cursor ? `<button class="btn btn-default btn-sm wa-audience-next">${__("Next page")}</button>` : "") +
		`<p class="text-muted">${__("Live advisory preview. Campaign approval uses a separate frozen snapshot.")}</p>`
	);
	if (result.next_cursor) {
		dialog.fields_dict.result.$wrapper.find(".wa-audience-next").on("click", () => {
			load_preview(frm, dialog, result.next_cursor);
		});
	}
}

function parse_filters(value) {
	if (typeof value === "string") return JSON.parse(value);
	return value || { version: 1, logic: "and", rules: [], groups: [] };
}
