frappe.pages["wa-connections"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Connections"), single_column: true });
	const body = $("<div class='tag-marketing p-4'></div>").appendTo(page.main);
	const is_manager = frappe.user.has_role("Marketing Manager") && !frappe.user.has_role("System Manager");
	let loading = false;
	const request_id = () => crypto.randomUUID();
	const action = async (method, args, button) => {
		try {
			const result = await tag_marketing.ui.request(method, args, { command: true, button });
			tag_marketing.ui.show_operation(result.operation);
		} catch (error) {
			tag_marketing.ui.show_error(error, { on_reload: wrapper.refresh_connections });
		}
	};
	wrapper.refresh_connections = async function () {
		if (loading) return;
		loading = true;
		body.empty().attr("aria-busy", "true");
		const table = $("<div class='table-responsive'></div>").appendTo(body);
		try {
			const data = await tag_marketing.ui.request("tag_marketing.api.connections.health");
			const rows = data.items || [];
			if (!rows.length) {
				tag_marketing.ui.render_state(body, {
					title: __("No WhatsApp connections"),
					message: is_manager ? __("Ask a System Manager to configure a connection.") : __("Add a Meta connection to begin setup."),
				});
				return;
			}
			const grid = $("<table class='table table-bordered'></table>").appendTo(table);
			const head = $("<thead><tr></tr></thead>").appendTo(grid).find("tr");
			[__("Connection"), __("Status"), __("Last validation"), __("Last webhook"), __("Numbers"), __("Templates"), __("Diagnostic"), __("Actions")].forEach((label) => $("<th scope='col'></th>").text(label).appendTo(head));
			const rows_body = $("<tbody></tbody>").appendTo(grid);
			for (const row of rows) {
				const tr = $("<tr></tr>").appendTo(rows_body);
				[ row.connection_name, row.status, row.last_validated_at || __("Never"), row.last_webhook_at || __("Never"), row.number_count, row.template_count, row.last_error_code || __("None") ].forEach((value) => $("<td></td>").text(value ?? "").appendTo(tr));
				const buttons = $("<div class='btn-group btn-group-sm'></div>").appendTo($("<td></td>").appendTo(tr));
				const sync = $("<button type='button' class='btn btn-default'></button>").text(__("Sync Templates")).appendTo(buttons);
				sync.on("click", () => action("tag_marketing.api.connections.sync_templates", { connection: row.name, request_id: request_id() }, sync[0]));
				if (!is_manager) {
					const open = $("<button type='button' class='btn btn-default'></button>").text(__("Configure")).appendTo(buttons);
					open.on("click", () => frappe.set_route("Form", "WA Connection", row.name));
				}
			}
			if (!is_manager) {
				page.set_primary_action(__("Open Connection List"), () => frappe.set_route("List", "WA Connection"), "list");
			}
		} catch (error) {
			tag_marketing.ui.render_state(body, { title: __("Unable to load connections"), message: error.message, action: { label: __("Retry"), run: wrapper.refresh_connections } });
		} finally {
			loading = false;
			body.attr("aria-busy", "false");
		}
	};
	page.set_secondary_action(__("Refresh"), wrapper.refresh_connections, "refresh-cw");
};
frappe.pages["wa-connections"].on_page_show = function (wrapper) { wrapper.refresh_connections(); };
