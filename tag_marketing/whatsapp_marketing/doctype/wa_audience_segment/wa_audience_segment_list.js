frappe.listview_settings["WA Audience Segment"] = {
	onload(listview) {
		listview.page.add_inner_button(__("New audience segment"), async (button) => {
			const dialog = new frappe.ui.Dialog({
				title: __("New audience segment"),
				fields: [{ fieldname: "segment_name", fieldtype: "Data", label: __("Segment name"), reqd: 1 }],
				primary_action_label: __("Create"),
				primary_action: async () => {
					const values = dialog.get_values();
					if (!values) return;
					try {
						const result = await tag_marketing.ui.request("tag_marketing.api.audiences.save_audience_segment", {
							segment_name: values.segment_name,
							filters: { version: 1, logic: "and", rules: [], groups: [] },
						}, { command: true, button: dialog.get_primary_btn() });
						dialog.hide();
						frappe.set_route("Form", "WA Audience Segment", result.name);
					} catch (error) {
						tag_marketing.ui.show_error(error, { trigger: button });
					}
				},
			});
			dialog.show();
		});
	},
};
