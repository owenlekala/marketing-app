frappe.listview_settings["WA Template"] = {
	onload(listview) {
		listview.page.add_inner_button(__("Create Draft"), () => create_template_draft());
	},
};

async function create_template_draft() {
	let connections;
	try {
		const result = await tag_marketing.ui.request("tag_marketing.api.templates.connections", {});
		connections = result.items || [];
	} catch (error) {
		tag_marketing.ui.show_error(error);
		return;
	}
	if (!connections.length) {
		frappe.msgprint(__("No Ready or Degraded marketing connections are available."));
		return;
	}
	const dialog = new frappe.ui.Dialog({
		title: __("Create WhatsApp template draft"),
		fields: [
			{ fieldname: "connection", fieldtype: "Select", options: connections.map((row) => row.name), label: __("Connection"), reqd: 1 },
			{ fieldname: "template_name", fieldtype: "Data", label: __("Template name"), reqd: 1, description: __("Use lowercase letters, digits and underscores.") },
			{ fieldname: "language_code", fieldtype: "Data", label: __("Language code"), reqd: 1, default: "en_US" },
			{ fieldname: "category", fieldtype: "Select", label: __("Category"), options: "Marketing\nUtility", reqd: 1, default: "Marketing" },
			{ fieldname: "components", fieldtype: "Code", options: "JSON", label: __("Components"), reqd: 1, default: '[{"type":"BODY","text":"Hello {{1}}, here is your update."}]' },
			{ fieldname: "media_file", fieldtype: "Link", options: "File", label: __("Private header media (optional)"), description: __("Select an owned, private, unattached JPEG, PNG or PDF. The server verifies bytes and provider size limits.") },
		],
		primary_action_label: __("Save draft"),
		primary_action: async () => {
			const values = dialog.get_values();
			if (!values) return;
			try {
				const components = JSON.parse(values.components);
				const saved = await tag_marketing.ui.request("tag_marketing.api.templates.save", {
					...values,
					components: JSON.stringify(components),
					request_id: tag_marketing.ui.new_request_id(),
				}, { command: true, button: dialog.get_primary_btn() });
				dialog.hide();
				frappe.show_alert({ message: __("Template draft saved"), indicator: "green" });
				frappe.set_route("Form", "WA Template", saved.template);
			} catch (error) {
				tag_marketing.ui.show_error(error);
			}
		},
	});
	dialog.show();
}
