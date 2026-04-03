let scanTimer = null;

frappe.ui.form.on('Rental Movement', {
    refresh: function (frm) {
        // Client Script: Client Script for Movement
        if (frm.get_field('scan_barcode')) {
            frm.get_field('scan_barcode').$input.focus();
        }

        // Client Script: Scan_template
        frm.set_query("item_template", "table_qnvp", function () {
            return { filters: { "rental_item_type_box": "Bulk" } };
        });

        // Stable CSS for Bulk table
        $("<style>")
            .prop("type", "text/css")
            .html(`
                .grid-body .rows .grid-static-col[data-fieldname="scanned_units"] {
                    white-space: pre-wrap !important;
                    word-wrap: break-word !important;
                    height: auto !important;
                }
                .grid-row { height: auto !important; }
            `)
            .appendTo("head");

        frm.add_custom_button(__('Remove Serial'), function () {
            show_remove_dialog(frm);
        }, __("Actions"));

        if (frm.fields_dict['scan_barcode_2']) {
            frm.fields_dict['scan_barcode_2'].$input.on('keypress', function (e) {
                if (e.which == 13) {
                    let barcode = $(this).val().trim();
                    if (barcode) process_bulk_scan(frm, barcode);
                }
            });
        }
    },

    transaction_type: function (frm) {
        const default_warehouse = "Main Warehouse";
        if (['CHECK_OUT', 'MAINTENANCE_OUT', 'LOST'].includes(frm.doc.transaction_type)) {
            frm.set_value('from_location', default_warehouse);
        } else if (['CHECK_IN', 'MAINTENANCE_IN'].includes(frm.doc.transaction_type)) {
            frm.set_value('to_location', default_warehouse);
            frm.set_value('from_location', '');
        }
    },

    scan_barcode: function (frm) {
        clearTimeout(scanTimer);
        scanTimer = setTimeout(() => {
            if (frm.doc.scan_barcode) {
                if (frm.doc.transaction_type === 'CHECK_OUT' && !frm.doc.to_location) {
                    frappe.msgprint(__('Please set the "To Location" before scanning.'));
                    frm.set_value('scan_barcode', '');
                    return;
                }
                call_scan_api(frm, frm.doc.scan_barcode);
            }
        }, 300);
    }
});

frappe.ui.form.on('Rental Item Unit Child Table', {
    unit_doc_id: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.unit_doc_id) {
            frappe.db.get_value('Rental Item Unit', row.unit_doc_id,
                ['name', 'unit_serial_number', 'unit_name', 'unit_condition', 'unit_location', 'movement_status'],
                (d) => {
                    if (d) {
                        if (!validate_ui_logic(frm, d)) {
                            frm.get_field('rental_item_unit_child_table').grid.grid_rows_by_docname[cdn].remove();
                            frm.refresh_field('rental_item_unit_child_table');
                            return;
                        }
                        frappe.model.set_value(cdt, cdn, {
                            'unit_serial_number': d.unit_serial_number,
                            'unit_name': d.unit_name,
                            'unit_condition': d.unit_condition,
                            'prev_location': d.unit_location,
                            'prev_movement_status': d.movement_status
                        });
                    }
                }
            );
        }
    }
});

// Bulk Item Child Table Logic (from Scan_template)
frappe.ui.form.on("Rent Bulk Item Child Table_2", {
    scanned_units: function (frm, cdt, cdn) {
        let child = locals[cdt][cdn];
        let serials = child.scanned_units ? child.scanned_units.split('\n').filter(s => s.trim().length > 0) : [];
        frappe.model.set_value(cdt, cdn, "qty", serials.length || 0);
    },

    qty: function (frm, cdt, cdn) {
        let child = locals[cdt][cdn];
        if (child.item_template) {
            frappe.db.get_value("Rental Item Template", child.item_template, "rental_item_type_box", (r) => {
                if (r && (r.rental_item_type_box === "Unit" || r.rental_item_type_box === "Box")) {
                    let serials = child.scanned_units ? child.scanned_units.split('\n').filter(s => s.trim()) : [];
                    let correct_qty = serials.length;
                    if (child.qty !== correct_qty) {
                        frappe.model.set_value(cdt, cdn, "qty", correct_qty);
                    }
                }
            });
        }
    }
});

function call_scan_api(frm, serial) {
    frappe.call({
        method: "rental_management.api.handle_unit_scan",
        args: { serial: serial },
        callback: function (r) {
            if (r.message) {
                let d = r.message;
                if (!validate_ui_logic(frm, d)) {
                    frm.set_value('scan_barcode', '');
                    return;
                }
                let row = frm.add_child('rental_item_unit_child_table');
                frappe.model.set_value(row.doctype, row.name, {
                    'unit_doc_id': d.name,
                    'unit_serial_number': d.unit_serial_number,
                    'unit_name': d.unit_name,
                    'unit_condition': d.unit_condition,
                    'prev_location': d.unit_location,
                    'prev_movement_status': d.movement_status
                });
                frm.refresh_field('rental_item_unit_child_table');
                frappe.show_alert({ message: __('Unit Added'), indicator: 'green' });
            }
            frm.set_value('scan_barcode', '');
            frm.get_field('scan_barcode').$input.focus();
        }
    });
}

function process_bulk_scan(frm, barcode) {
    frappe.call({
        method: "rental_management.api.handle_unit_scan_2",
        args: { barcode: barcode },
        freeze: true,
        callback: function (r) {
            if (r.message) {
                const res = r.message;
                const table_field = "table_qnvp";
                let rows = frm.doc[table_field] || [];
                let found_row = rows.find(row => row.item_template === res.item_template);

                if (found_row) {
                    let current_scans = found_row.scanned_units || "";
                    let scans_array = current_scans.split('\n').map(s => s.trim()).filter(s => s);
                    if (scans_array.includes(barcode)) {
                        frappe.show_alert({ message: __("{0} already scanned", [barcode]), indicator: 'orange' });
                    } else {
                        let new_scans = current_scans.trim() + "\n" + barcode;
                        frappe.model.set_value(found_row.doctype, found_row.name, "scanned_units", new_scans);
                    }
                } else {
                    let new_row = frappe.model.add_child(frm.doc, "Rent Bulk Item Child Table_2", table_field);
                    frappe.model.set_value(new_row.doctype, new_row.name, {
                        "item_template": res.item_template,
                        "item_name": res.item_name,
                        "qty": 1,
                        "scanned_units": barcode
                    });
                }
                frm.refresh_field(table_field);
                frm.set_value("scan_barcode_2", "");
                setTimeout(() => frm.fields_dict['scan_barcode_2'].$input.focus(), 100);
            }
        },
        error: () => {
            frappe.show_alert({ message: __("Unit {0} not found", [barcode]), indicator: 'red' });
            frm.set_value("scan_barcode_2", "");
        }
    });
}

function show_remove_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Remove Serial Number'),
        fields: [{ label: __('Scan/Type Serial'), fieldname: 'barcode', fieldtype: 'Data', reqd: 1 }],
        primary_action_label: __('Remove'),
        primary_action(values) {
            remove_serial_logic(frm, values.barcode.trim());
            d.hide();
        }
    });
    d.show();
}

function remove_serial_logic(frm, barcode) {
    const table_field = "table_qnvp";
    let found = false;
    (frm.doc[table_field] || []).forEach(row => {
        let scans_array = (row.scanned_units || "").split('\n').map(s => s.trim()).filter(s => s);
        if (scans_array.includes(barcode)) {
            found = true;
            let updated_scans = scans_array.filter(s => s !== barcode);
            if (updated_scans.length === 0) {
                frappe.model.clear_row(frm.doc, table_field, row.idx);
            } else {
                frappe.model.set_value(row.doctype, row.name, "scanned_units", updated_scans.join('\n'));
            }
            frappe.show_alert({ message: __("Removed {0}", [barcode]), indicator: 'red' });
        }
    });
    if (!found) frappe.show_alert({ message: __("Serial {0} not found", [barcode]), indicator: 'orange' });
    frm.refresh_field(table_field);
}

function validate_ui_logic(frm, unit) {
    const tx = frm.doc.transaction_type;
    const current_condition = unit.current_condition || unit.unit_condition;
    let existing_rows = (frm.doc.rental_item_unit_child_table || []).filter(row => row.unit_doc_id === unit.name);
    if (existing_rows.length > 1) {
        frappe.msgprint({ title: __('Duplicate'), indicator: 'orange', message: __(`Unit <b>${unit.unit_serial_number}</b> is already in this list.`) });
        return false;
    }
    if (tx === 'CHECK_OUT') {
        if (unit.movement_status !== 'Warehouse') {
            frappe.msgprint({ title: __('Invalid Status'), indicator: 'red', message: __(`Unit <b>${unit.unit_serial_number}</b> is currently <b>${unit.movement_status}</b>. It must be in 'Warehouse' to Check Out.`) });
            return false;
        }
        if (current_condition !== 'OK') {
            frappe.msgprint({ title: __('Condition Issue'), indicator: 'orange', message: __(`Unit <b>${unit.unit_serial_number}</b> is <b>${current_condition}</b>. Only 'OK' units can be Checked Out.`) });
            return false;
        }
    }
    if (tx === 'MAINTENANCE_IN' && unit.movement_status !== 'In Maintenance') {
        frappe.msgprint({ title: __('Status Mismatch'), indicator: 'red', message: __(`Unit <b>${unit.unit_serial_number}</b> is not currently marked as 'In Maintenance'.`) });
        return false;
    }
    return true;
}
