frappe.listview_settings["Ops Entry"] = {
	onload(listview) {
		listview.page.add_button(__("Warehouse Dashboard"), () => {
			window.location.href = "/desk/warehouse_dashboard";
		});
	},
};