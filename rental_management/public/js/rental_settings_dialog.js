// Rental Settings: a dialog opened from the sidebar header menu (the menu at the top left).
// Company, default workspace name and the four rental warehouses are saved to the Rental Settings single.
(function () {
	const SINGLE = "Rental Settings";
	const WAREHOUSE_FIELDS = ["store_warehouse", "event_warehouse", "repair_warehouse", "missing_warehouse"];

	function open_rental_settings() {
		frappe.model.with_doctype(SINGLE, () => {
			frappe.db.get_doc(SINGLE).then((doc) => {
				const dialog = new frappe.ui.Dialog({
					title: __("Rental Settings"),
					fields: [
						{ fieldname: "company", fieldtype: "Link", options: "Company", label: __("Company"), reqd: 1, default: doc.company },
						{ fieldname: "workspace_name", fieldtype: "Data", label: __("Default Workspace Name"), default: doc.workspace_name },
						{ fieldtype: "Section Break", label: __("Warehouses") },
						...WAREHOUSE_FIELDS.map((field) => ({
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

	// The sidebar header's menu is built fresh on every open, so the row is added there.
	function install() {
		const Header = window.frappe?.ui?.SidebarHeader;
		if (!Header || Header.prototype.__rental_settings) return;
		const original = Header.prototype.menu_items;
		Header.prototype.menu_items = function () {
			const groups = original.call(this);
			const row = {
				name: "rental-settings",
				label: __("Rental Settings"),
				icon: "settings",
				onclick: open_rental_settings,
			};
			const at = Math.min(1, groups.length);
			return [...groups.slice(0, at), { group: "", options: [row] }, ...groups.slice(at)];
		};
		Header.prototype.__rental_settings = true;
	}

	install();
	$(document).on("app_ready", install);
})();
