frappe.listview_settings["WA Contact"] = {
	onload(listview) {
		listview.page.add_inner_button(__("Add ERPNext Source"), () => open_source_dialog(listview));
		listview.page.add_inner_button(__("Import CSV"), open_csv_uploader);
	},
};

function open_csv_uploader() {
	new frappe.ui.FileUploader({
		folder: "Home/Attachments",
		allow_multiple: false,
		make_attachments_public: false,
		allow_toggle_private: false,
		disable_file_browser: true,
		restrictions: { allowed_file_types: [".csv"] },
		dialog_title: __("Upload private contact CSV"),
		on_success: (file) => open_import_mapping(file.name),
	});
}

async function open_import_mapping(fileName) {
	try {
		const inspected = await tag_marketing.ui.request("tag_marketing.api.audiences.inspect_import_csv", { source_file: fileName });
		const headers = inspected.columns || [];
		const optional = ["", ...headers].join("\n");
		const dialog = new frappe.ui.Dialog({
			title: __("Map CSV columns"),
			fields: [
				{ fieldname: "phone", fieldtype: "Select", label: __("Mobile number"), options: headers.join("\n"), reqd: 1 },
				{ fieldname: "display_name", fieldtype: "Select", label: __("Display name"), options: optional },
				{ fieldname: "default_country_code", fieldtype: "Data", label: __("Default phone country (ISO alpha-2)"), reqd: 1 },
				{ fieldtype: "Section Break", label: __("Optional consent evidence") },
				{ fieldname: "consent_occurred_at", fieldtype: "Select", label: __("Consent date/time"), options: optional },
				{ fieldname: "consent_notice_version", fieldtype: "Select", label: __("Notice version"), options: optional },
				{ fieldname: "consent_reference", fieldtype: "Select", label: __("Evidence reference"), options: optional },
			],
			primary_action_label: __("Validate preview"),
			primary_action: async (values) => {
				const columns = { phone: values.phone };
				if (values.display_name) columns.display_name = values.display_name;
				for (const field of ["consent_occurred_at", "consent_notice_version", "consent_reference"]) {
					if (values[field]) columns[field] = values[field];
				}
				try {
					const result = await tag_marketing.ui.request("tag_marketing.api.audiences.create_import_batch", {
						source_file: fileName,
						mapping: { columns, default_country_code: values.default_country_code.toUpperCase() },
					}, { command: true, button: dialog.get_primary_btn() });
					dialog.hide();
					frappe.set_route("Form", "WA Import Batch", result.batch);
				} catch (error) {
					tag_marketing.ui.show_error(error);
				}
			},
		});
		dialog.show();
	} catch (error) {
		tag_marketing.ui.show_error(error);
	}
}

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
