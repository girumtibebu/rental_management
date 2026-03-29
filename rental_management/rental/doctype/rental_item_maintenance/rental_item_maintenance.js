frappe.ui.form.on('Rental Item Maintenance', {
    onload: function (frm) {
        // Client Script: Maintenance Barcode
        if (frm.is_new()) {
            reset_unit_fields(frm);
        }
        frm.trigger("update_fields_ui");
    },

    refresh: function (frm) {
        frm.trigger("update_fields_ui");
    },

    workflow_state: function (frm) {
        frm.trigger("update_fields_ui");
    },

    scan_barcode: function (frm) {
        // Client Script: Maintenance Barcode
        if (!frm.doc.scan_barcode) return;

        frappe.call({
            method: "rental_management.api.get_rental_unit_by_serial",
            args: {
                serial_number: frm.doc.scan_barcode.trim()
            },
            callback: function (r) {
                if (r.message) {
                    const unit = r.message;
                    frm.set_value('unit_serial_number', unit.name);
                    frm.set_value('serial_number', unit.unit_serial_number);
                    frm.set_value('unit_name', unit.unit_name);
                    frappe.show_alert({ message: __("Unit Linked"), indicator: 'green' });
                } else {
                    reset_unit_fields(frm);
                }
                frm.set_value('scan_barcode', '');
                setTimeout(() => frm.get_field('scan_barcode').$input.focus(), 100);
            }
        });
    },

    update_fields_ui: function (frm) {
        // Client Script: Rental Maintenance
        const state = frm.doc.workflow_state;
        frm.toggle_display("maintained_by", state !== "Attention Required");

        const show_maintenance_fields = state === "In Repair" || state === "Complete";
        frm.toggle_display("maintenance_result", show_maintenance_fields);
        frm.toggle_display("final_condition", show_maintenance_fields);

        frm.toggle_display("unit_condition", true);
        frm.toggle_display("issue_description", true);
        frm.set_df_property("issue_description", "hidden", false);
        frm.set_df_property("issue_description", "read_only", state === "Complete");
    },

    before_workflow_action: function (frm) {
        // Client Script: Rental Item Maintenance(Save)
        if (frm.is_new()) {
            return frm.save();
        }
    },

    before_save: function (frm) {
        // Client Script: Rental Maintenance
        const state = frm.doc.workflow_state;
        if (state === "Attention Required") {
            frm.doc.maintained_by = null;
            frm.doc.final_condition = null;
            frm.doc.maintenance_result = null;
        } else if (state === "In Repair" || state === "Complete") {
            frm.doc.unit_condition = null;
        }
    }
});

function reset_unit_fields(frm) {
    frm.set_value('unit_name', '-');
    frm.set_value('serial_number', '-');
}
