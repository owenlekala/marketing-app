frappe.ui.form.on("WA Template", {
	refresh(frm) {
		frm.disable_save();
		if (frm.is_new()) return;
		frm.add_custom_button(__("Preview"), () => preview_template(frm));
		frm.add_custom_button(__("Validate Draft"), async (button) => {
			try {
				const result = await tag_marketing.ui.request("tag_marketing.api.templates.validate", {
					template: frm.doc.name,
					expected_modified: frm.doc.modified,
				}, { command: true, button });
				if (!result.valid) throw new Error(__("The saved content hash is stale. Edit and save the draft again."));
				frappe.show_alert({ message: __("Draft is valid"), indicator: "green" });
			} catch (error) {
				tag_marketing.ui.show_error(error, { on_reload: () => frm.reload_doc(), trigger: button });
			}
		});
		if (["Marketing Manager", "System Manager"].some((role) => frappe.user.has_role(role))) {
			frm.add_custom_button(__("Sync provider status"), async (button) => {
				try {
					const result = await tag_marketing.ui.request("tag_marketing.api.templates.sync", {
						template: frm.doc.name,
						request_id: tag_marketing.ui.new_request_id(),
					}, { command: true, button });
					tag_marketing.ui.show_operation(result.operation, {
						trigger: button,
						on_succeeded: () => frm.reload_doc(),
					});
				} catch (error) {
					tag_marketing.ui.show_error(error, { on_reload: () => frm.reload_doc(), trigger: button });
				}
			});
			if (["Draft", "Rejected"].includes(frm.doc.status) && !frm.doc.provider_template_id) {
				frm.add_custom_button(__("Submit for review"), async (button) => {
					try {
						const validation = await tag_marketing.ui.request("tag_marketing.api.templates.validate", {
							template: frm.doc.name,
							expected_modified: frm.doc.modified,
						}, { command: true, button });
						const result = await tag_marketing.ui.request("tag_marketing.api.templates.submit", {
							template: frm.doc.name,
							content_hash: validation.content_hash,
							expected_modified: frm.doc.modified,
							request_id: tag_marketing.ui.new_request_id(),
						}, { command: true, button });
						tag_marketing.ui.show_operation(result.operation, {
							trigger: button,
							on_succeeded: () => frm.reload_doc(),
						});
					} catch (error) {
						tag_marketing.ui.show_error(error, { on_reload: () => frm.reload_doc(), trigger: button });
					}
				});
			}
		}
		if (["Draft", "Rejected", "Approved"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Edit Draft"), () => edit_template(frm));
		}
	},
});

function edit_template(frm) {
	const current = parse_components(frm.doc.components_json);
	const dialog = new frappe.ui.Dialog({
		title: __("Edit WhatsApp template draft"),
		fields: [
			{ fieldname: "template_name", fieldtype: "Data", label: __("Template name"), reqd: 1, default: frm.doc.template_name },
			{ fieldname: "language_code", fieldtype: "Data", label: __("Language code"), reqd: 1, default: frm.doc.language_code },
			{ fieldname: "category", fieldtype: "Select", label: __("Category"), options: "Marketing\nUtility", reqd: 1, default: frm.doc.category },
			{ fieldname: "components", fieldtype: "Code", options: "JSON", label: __("Components"), reqd: 1, default: JSON.stringify(current, null, 2) },
			{ fieldname: "media_file", fieldtype: "Link", options: "File", label: __("Private header media (optional)"), default: frm.doc.media_file },
		],
		primary_action_label: __("Save draft revision"),
		primary_action: async () => {
			const values = dialog.get_values();
			if (!values) return;
			try {
				const components = JSON.parse(values.components);
				await tag_marketing.ui.request("tag_marketing.api.templates.save", {
					...values,
					connection: frm.doc.connection,
					template: frm.doc.name,
					expected_modified: frm.doc.modified,
					components: JSON.stringify(components),
					request_id: tag_marketing.ui.new_request_id(),
				}, { command: true, button: dialog.get_primary_btn() });
				dialog.hide();
				await frm.reload_doc();
				frappe.show_alert({ message: __("Draft revision saved; provider approval is unchanged until submission and sync."), indicator: "green" });
			} catch (error) {
				tag_marketing.ui.show_error(error, { on_reload: () => frm.reload_doc() });
			}
		},
	});
	dialog.show();
}

function preview_template(frm) {
	const components = parse_components(frm.doc.components_json);
	const dialog = new frappe.ui.Dialog({
		title: __("Template preview"),
		fields: [
			{ fieldname: "samples", fieldtype: "Code", options: "JSON", label: __("Sample values (JSON array)"), default: "[]" },
			{ fieldname: "preview", fieldtype: "HTML" },
		],
		primary_action_label: __("Render preview"),
		primary_action: async () => {
			try {
				const values = JSON.parse(dialog.get_value("samples") || "[]");
				const rendered = await tag_marketing.ui.request("tag_marketing.api.templates.preview", {
					components: JSON.stringify(components),
					sample_values: JSON.stringify(values),
				}, { command: true, button: dialog.get_primary_btn() });
				dialog.fields_dict.preview.$wrapper.html(`<pre class="wa-template-preview">${frappe.utils.escape_html(rendered.body)}</pre>`);
			} catch (error) {
				tag_marketing.ui.show_error(error);
			}
		},
	});
	dialog.show();
	dialog.get_primary_btn().trigger("click");
}

function parse_components(value) {
	return typeof value === "string" ? JSON.parse(value) : value;
}
