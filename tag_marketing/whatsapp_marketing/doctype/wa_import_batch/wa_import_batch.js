frappe.ui.form.on("WA Import Batch", {
	refresh(frm) {
		if (frm.is_new()) return;
		if (frm.doc.status === "Preview Ready") {
			frm.add_custom_button(__("Revalidate CSV"), async (button) => {
				try {
					const result = await tag_marketing.ui.request("tag_marketing.api.audiences.validate_import_batch", {
						batch: frm.doc.name,
						expected_modified: frm.doc.modified,
						request_id: tag_marketing.ui.new_request_id(),
					}, { command: true, button });
					if (result.operation) tag_marketing.ui.show_operation(result.operation, { trigger: button });
					await frm.reload_doc();
				} catch (error) {
					tag_marketing.ui.show_error(error, { on_reload: () => frm.reload_doc(), trigger: button });
				}
			});
			frm.add_custom_button(__("Confirm Import"), () => confirm_import(frm), __("Import"));
		}
	},
});

async function confirm_import(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Confirm contact import"),
		fields: [{
			fieldtype: "HTML",
			fieldname: "summary",
			options: `<p>${__("Import {0} valid rows. Rows without evidence remain ineligible; rejected rows will be skipped.", [frm.doc.valid_count || 0])}</p><p>${__("Rows missing consent evidence: {0}", [frm.doc.evidence_missing_count || 0])}</p>`,
		}],
		primary_action_label: __("Confirm Import"),
		primary_action: async () => {
			try {
				const result = await tag_marketing.ui.request("tag_marketing.api.audiences.confirm_import_batch", {
					batch: frm.doc.name,
					input_hash: frm.doc.input_hash,
					expected_modified: frm.doc.modified,
					request_id: tag_marketing.ui.new_request_id(),
				}, { command: true, button: dialog.get_primary_btn() });
				dialog.hide();
				if (result.operation) tag_marketing.ui.show_operation(result.operation, { trigger: frm.page.btn_primary });
				await frm.reload_doc();
			} catch (error) {
				tag_marketing.ui.show_error(error, { on_reload: () => frm.reload_doc() });
			}
		},
	});
	dialog.show();
}
