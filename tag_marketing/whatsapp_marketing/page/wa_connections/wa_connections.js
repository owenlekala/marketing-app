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
			[__("Connection"), __("Status"), __("Last validation"), __("Last webhook verification"), __("Last signed event"), __("Numbers"), __("Templates"), __("Events pending / failed"), __("Diagnostic"), __("Actions")].forEach((label) => $("<th scope='col'></th>").text(label).appendTo(head));
			const rows_body = $("<tbody></tbody>").appendTo(grid);
			for (const row of rows) {
				const tr = $("<tr></tr>").appendTo(rows_body);
				[ row.connection_name, row.status, row.last_validated_at || __("Never"), row.last_webhook_verified_at || __("Never"), row.last_webhook_at || __("Never"), row.number_count, row.template_count, `${row.webhook_pending_count || 0} / ${row.webhook_failed_count || 0}`, row.last_error_code || __("None") ].forEach((value) => $("<td></td>").text(value ?? "").appendTo(tr));
				const buttons = $("<div class='btn-group btn-group-sm'></div>").appendTo($("<td></td>").appendTo(tr));
				const sync = $("<button type='button' class='btn btn-default'></button>").text(__("Sync Templates")).appendTo(buttons);
				sync.on("click", () => action("tag_marketing.api.connections.sync_templates", { connection: row.name, request_id: request_id() }, sync[0]));
				if (!is_manager) {
					const diagnostics = $("<button type='button' class='btn btn-default'></button>").text(__("Check Webhook")).appendTo(buttons);
					diagnostics.on("click", async () => {
						try {
							const result = await tag_marketing.ui.request("tag_marketing.api.connections.check_webhook", { connection: row.name });
							const dialog = new frappe.ui.Dialog({
								title: __("Webhook diagnostics"),
								fields: [
									{ fieldname: "readiness", label: __("Readiness"), fieldtype: "Data", read_only: 1 },
									{ fieldname: "subscription", label: __("Meta GET verification"), fieldtype: "Data", read_only: 1 },
									{ fieldname: "verified_at", label: __("Last verified"), fieldtype: "Data", read_only: 1 },
									{ fieldname: "signed_post_at", label: __("Last signed POST"), fieldtype: "Data", read_only: 1 },
									{ fieldname: "pending", label: __("Pending events"), fieldtype: "Int", read_only: 1 },
									{ fieldname: "processing", label: __("Processing events"), fieldtype: "Int", read_only: 1 },
									{ fieldname: "failed", label: __("Failed events"), fieldtype: "Int", read_only: 1 },
									{ fieldname: "diagnostic", label: __("Safe diagnostic code"), fieldtype: "Data", read_only: 1 },
								],
								primary_action_label: __("Close"),
								primary_action: () => dialog.hide(),
							});
							dialog.$wrapper.attr("aria-label", __("Webhook diagnostics"));
							dialog.set_values({ readiness: result.readiness, subscription: result.subscription_diagnostic, verified_at: result.last_verified_at || __("Never"), signed_post_at: result.last_signed_post_at || __("Never"), pending: result.events.ready || 0, processing: result.events.processing || 0, failed: result.events.failed || 0, diagnostic: result.last_error_code || __("None") });
							dialog.show();
						} catch (error) {
							tag_marketing.ui.show_error(error, { on_reload: wrapper.refresh_connections });
						}
					});
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
