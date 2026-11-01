frappe.listview_settings["WA Contact"] = {
	onload(listview) {
		listview.page.add_inner_button(__("Add ERPNext Source"), () => open_source_dialog(listview));
	},
};

function open_source_dialog(listview) {
	const dialog = new frappe.ui.Dialog({
		title: __("Add ERPNext Source"),
		fields: [
			{ fieldname: "source_doctype", fieldtype: "Select", label: __("ERPNext Record"), reqd: 1 },
			{ fieldname: "search", fieldtype: "Data", label: __("Search") },
			{ fieldname: "country_code", fieldtype: "Data", label: __("Phone country code (ISO 3166-1 alpha-2)"), reqd: 1, description: __("Enter the country for local-number validation. International numbers retain their + prefix.") },
			{ fieldname: "include_unassigned_lead", fieldtype: "Check", label: __("Include Leads with no ERPNext Company") },
			{ fieldname: "results", fieldtype: "HTML" },
		],
		primary_action_label: __("Search"),
		primary_action: async () => refresh_source_results(dialog),
	});
	dialog.show();
	tag_marketing.ui.request("tag_marketing.api.audiences.enabled_sources")
		.then((response) => {
			const options = response.items || [];
			if (!options.length) {
				dialog.get_field("results").$wrapper.text(__("Enable an ERPNext source in WhatsApp Marketing Settings first."));
				return;
			}
		dialog.set_value("source_doctype", options[0]);
		dialog.get_field("source_doctype").df.options = options.join("\n");
		dialog.get_field("source_doctype").refresh();
		})
		.catch((error) => tag_marketing.ui.show_error(error));
}

async function refresh_source_results(dialog) {
	const values = dialog.get_values();
	if (!values) return;
	const wrapper = dialog.get_field("results").$wrapper;
	wrapper.text(__("Loading permitted ERPNext records…"));
	try {
		const response = await tag_marketing.ui.request("tag_marketing.api.audiences.source_preview", {
			source_doctype: values.source_doctype,
			search: values.search || "",
			country_code: (values.country_code || "").toUpperCase(),
			start: 0,
			page_length: 20,
		});
		const items = response.items || [];
		wrapper.empty();
		if (!items.length) {
			wrapper.text(__("No permitted matching records with a valid mobile number were found."));
			return;
		}
		const table = $("<div class='wa-source-results'>");
		for (const item of items) {
			const row = $("<div class='wa-source-result'>").append($("<strong>").text(item.label));
			row.append($("<span class='text-muted'>").text(` · ${item.name}`));
			if (!item.phones.length) row.append($("<div class='text-muted'>").text(__("No valid mobile candidate for this country code.")));
			for (const phone of item.phones) {
				const add = $("<button class='btn btn-xs btn-default'>").text(`${phone.phone_e164} · ${__(phone.source)}`);
				add.on("click", () => save_source(dialog, item, phone));
				row.append(add);
			}
			if (item.unassigned_lead) row.append($("<div class='text-warning'>").text(__("This Lead has no Company. Select the explicit inclusion option before linking.")));
			table.append(row);
		}
		wrapper.append(table);
	} catch (error) {
		wrapper.text(__("Could not load ERPNext records. Check your source permissions and try again."));
		tag_marketing.ui.show_error(error);
	}
}

async function save_source(dialog, item, phone) {
	const values = dialog.get_values();
	if (item.unassigned_lead && !values.include_unassigned_lead) {
		frappe.msgprint(__("Confirm the explicit option to include a Lead with no ERPNext Company."));
		return;
	}
	try {
		const result = await tag_marketing.ui.request("tag_marketing.api.audiences.add_source", {
			source_doctype: values.source_doctype,
			source_name: item.name,
			selected_phone: phone.phone,
			country_code: values.country_code.toUpperCase(),
			include_unassigned_lead: values.include_unassigned_lead ? 1 : 0,
		}, { command: true });
		dialog.hide();
		frappe.set_route("Form", "WA Contact", result.contact);
		list_refresh();
	} catch (error) {
		tag_marketing.ui.show_error(error);
	}
}

function list_refresh() {
	if (cur_list?.doctype === "WA Contact") cur_list.refresh();
}
