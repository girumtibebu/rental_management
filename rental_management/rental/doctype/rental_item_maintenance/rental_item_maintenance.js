frappe.ui.form.on("Rental Item Maintenance", {
	refresh(frm) {
		frm.trigger("update_fields_ui");
	},

	workflow_state(frm) {
		frm.trigger("update_fields_ui");
	},

	scan_barcode(frm) {
		const code = (frm.doc.scan_barcode || "").trim();
		if (!code) return;
		frappe.db.exists("Serial No", code).then((found) => {
			if (found) {
				frm.set_value("serial_no", code);
			} else {
				frappe.show_alert({ message: __("No serial number {0}", [code]), indicator: "red" });
			}
			frm.set_value("scan_barcode", "");
		});
	},

	update_fields_ui(frm) {
		const state = frm.doc.workflow_state;
		const repairing = state === "In Repair" || state === "Complete";
		frm.toggle_display("maintained_by", state !== "Attention Required");
		frm.toggle_display("maintenance_result", repairing);
		frm.toggle_display("final_condition", repairing);
		frm.set_df_property("issue_description", "read_only", state === "Complete");
	},

	before_workflow_action(frm) {
		if (frm.is_new()) {
			return frm.save();
		}
	},
});
