frappe.ui.form.on("WA Contact", {
	refresh(frm) {
		if (frm.is_new()) return;
		const roles = frappe.user_roles || [];
		if (roles.includes("Marketing User") || roles.includes("Marketing Manager")) {
			frm.add_custom_button(__("Record Consent"), () => open_consent_dialog(frm, "Granted"), __("Consent"));
			frm.add_custom_button(__("Record Withdrawal"), () => open_consent_dialog(frm, "Withdrawn"), __("Consent"));
			load_consent_history(frm);
		}
		if (roles.includes("Marketing Manager") || roles.includes("System Manager")) {
			frm.add_custom_button(__("Change Suppression"), () => open_suppression_dialog(frm), __("Consent"));
		}
	},
});

function open_consent_dialog(frm, eventType) {
	const granted = eventType === "Granted";
	const dialog = new frappe.ui.Dialog({
		title: granted ? __("Record Marketing Consent") : __("Record Marketing Withdrawal"),
		fields: [
			{ fieldname: "occurred_at", fieldtype: "Datetime", label: __("When it occurred"), default: frappe.datetime.now_datetime(), reqd: 1 },
			{ fieldname: "source", fieldtype: "Select", label: __("Evidence source"), options: granted ? "Web Form\nAgent Recorded" : "Agent Recorded\nInbound Keyword\nUnsubscribe Button", default: granted ? "Web Form" : "Agent Recorded", reqd: 1 },
			...(granted ? [
				{ fieldname: "notice_version", fieldtype: "Data", label: __("Notice version"), reqd: 1 },
				{ fieldname: "evidence_reference", fieldtype: "Small Text", label: __("Evidence reference"), reqd: 1 },
			] : []),
		],
		primary_action_label: granted ? __("Record Consent") : __("Record Withdrawal"),
		primary_action: async (values) => {
			try {
				await tag_marketing.ui.request("tag_marketing.api.audiences.record_consent", {
					contact: frm.doc.name,
					event_type: eventType,
					occurred_at: frappe.datetime.convert_to_system_tz(values.occurred_at, false).toISOString(),
					source: values.source,
					notice_version: values.notice_version || "",
					evidence_reference: values.evidence_reference || "",
					request_id: tag_marketing.ui.new_request_id(),
				}, { command: true, button: dialog.get_primary_btn() });
				dialog.hide();
				await frm.reload_doc();
				load_consent_history(frm);
			} catch (error) {
				tag_marketing.ui.show_error(error, { on_reload: () => frm.reload_doc() });
			}
		},
	});
	dialog.show();
}

function open_suppression_dialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Change Marketing Suppression"),
		fields: [
			{ fieldname: "active", fieldtype: "Check", label: __("Suppress marketing") , default: frm.doc.suppressed ? 1 : 0 },
			{ fieldname: "reason", fieldtype: "Select", label: __("Reason"), options: "Opt Out\nManual Block\nInvalid Address", default: "Manual Block", reqd: 1 },
		],
		primary_action_label: __("Save Suppression"),
		primary_action: async (values) => {
			try {
				await tag_marketing.ui.request("tag_marketing.api.audiences.set_suppression", {
					contact: frm.doc.name,
					active: values.active ? 1 : 0,
					reason: values.reason,
					expected_modified: frm.doc.modified,
					request_id: tag_marketing.ui.new_request_id(),
				}, { command: true, button: dialog.get_primary_btn() });
				dialog.hide();
				await frm.reload_doc();
			} catch (error) {
				tag_marketing.ui.show_error(error, { on_reload: () => frm.reload_doc() });
			}
		},
	});
	dialog.show();
}

async function load_consent_history(frm) {
	const history = await tag_marketing.ui.request("tag_marketing.api.audiences.consent_history", { contact: frm.doc.name, start: 0, page_length: 20 }).catch((error) => {
		if (error.code !== "NOT_FOUND" && error.code !== "REQUEST_FAILED") tag_marketing.ui.show_error(error);
		return null;
	});
	if (!history || !frm.fields_dict.consent_history) return;
	const wrapper = frm.fields_dict.consent_history.$wrapper.empty().addClass("tag-marketing");
	if (!history.items.length) {
		wrapper.text(__("No consent evidence has been recorded."));
		return;
	}
	const list = $("<ul class='list-unstyled'>");
	for (const event of history.items) {
		const item = $("<li class='margin-bottom'>");
		$("<strong>").text(__(event.event_type)).appendTo(item);
		$("<span class='text-muted'>").text(` · ${event.occurred_at} · ${__(event.source)}`).appendTo(item);
		if (event.notice_version) $("<div>").text(__("Notice: {0}", [event.notice_version])).appendTo(item);
		if (event.evidence_reference) $("<div>").text(__("Evidence: {0}", [event.evidence_reference])).appendTo(item);
		list.append(item);
	}
	wrapper.append(list);
}
