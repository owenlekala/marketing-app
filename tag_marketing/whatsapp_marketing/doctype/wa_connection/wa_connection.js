frappe.ui.form.on("WA Connection", {
	refresh(frm) {
		if (frm.is_new() || !frappe.user.has_role("System Manager")) return;
		const invoke = async (label, method, args) => {
			let button;
			button = frm.add_custom_button(__(label), async () => {
				try {
					const result = await tag_marketing.ui.request(method, args(), { command: true, button: button?.[0] });
					tag_marketing.ui.show_operation(result.operation);
				} catch (error) {
					tag_marketing.ui.show_error(error, { on_reload: () => frm.reload_doc() });
				}
			});
			button.attr("aria-label", __(label));
		};
		invoke("Validate Connection", "tag_marketing.api.connections.validate_connection", () => ({ connection: frm.doc.name, expected_modified: frm.doc.modified, request_id: tag_marketing.ui.new_request_id() }));
		invoke("Sync Numbers", "tag_marketing.api.connections.sync_numbers", () => ({ connection: frm.doc.name, request_id: tag_marketing.ui.new_request_id() }));
		invoke("Sync Templates", "tag_marketing.api.connections.sync_templates", () => ({ connection: frm.doc.name, request_id: tag_marketing.ui.new_request_id() }));
		let toggle_button;
		toggle_button = frm.add_custom_button(__(frm.doc.status === "Disabled" ? "Reconnect" : "Disable"), async () => {
			try {
				const result = await tag_marketing.ui.request("tag_marketing.api.connections.set_enabled", {
					connection: frm.doc.name,
					enabled: frm.doc.status === "Disabled",
					expected_modified: frm.doc.modified,
					request_id: tag_marketing.ui.new_request_id(),
				}, { command: true, button: toggle_button?.[0] });
				tag_marketing.ui.show_operation(result.operation);
				await frm.reload_doc();
			} catch (error) {
				tag_marketing.ui.show_error(error, { on_reload: () => frm.reload_doc() });
			}
		});
	},
});
