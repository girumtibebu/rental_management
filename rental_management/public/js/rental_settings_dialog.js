// Rental settings dialog: company, default workspace name and the four rental warehouses.
// Opened from the Rental Workspace list ("Rental Settings" button).
(function () {
	const SINGLE = "Rental Settings";

	function open_rental_settings() {
		frappe.model.with_doctype(SINGLE, () => {
			frappe.db.get_doc(SINGLE).then((doc) => {
				const dialog = new frappe.ui.Dialog({
					title: __("Rental Settings"),
					fields: [
						{ fieldname: "company", fieldtype: "Link", options: "Company", label: __("Company"), reqd: 1, default: doc.company },
						{ fieldname: "workspace_name", fieldtype: "Data", label: __("Default Workspace Name"), default: doc.workspace_name },
						{ fieldtype: "Section Break", label: __("Warehouses") },
						...["store_warehouse", "event_warehouse", "repair_warehouse", "missing_warehouse"].map((field) => ({
							fieldname: field,
							fieldtype: "Link",
							options: "Warehouse",
							label: frappe.meta.get_docfield(SINGLE, field)?.label || field,
							default: doc[field],
							get_query: () => ({ filters: { company: dialog.get_value("company") } }),
						})),
					],
					primary_action_label: __("Save"),
					primary_action(values) {
						frappe.call({
							method: "frappe.client.set_value",
							args: { doctype: SINGLE, name: SINGLE, fieldname: values },
							callback: () => {
								frappe.show_alert({ message: __("Rental settings saved"), indicator: "green" });
								dialog.hide();
							},
						});
					},
				});
				dialog.show();
			});
		});
	}

	frappe.listview_settings["Rental Workspace"] = Object.assign({}, frappe.listview_settings["Rental Workspace"], {
		onload(listview) {
			listview.page.add_inner_button(__("Rental Settings"), open_rental_settings);
		},
	});
})();
