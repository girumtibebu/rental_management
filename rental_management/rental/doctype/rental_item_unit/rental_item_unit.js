let scanTimer = null;

frappe.ui.form.on('Rental Item Unit', {
    onload: function (frm) {
        // Client Script: script for locations
        update_location_code(frm);
    },

    refresh: function (frm) {
        // Client Script: dashboard indicator test
        frappe.db.get_doc(frm.doctype, frm.docname).then(doc => {
            if (doc.movement_status) frm.dashboard.add_indicator(__(doc.movement_status), "blue");
            if (doc.unit_location) frm.dashboard.add_indicator(__(doc.unit_location), "blue");
            if (doc.unit_condition) frm.dashboard.add_indicator(__(doc.unit_condition), "blue");
            if (doc.maintenance_status) frm.dashboard.add_indicator(__(doc.maintenance_status), "blue");
        });

        // Client Script: Rental Item Unit (Parent Box )
        if (frm.get_field('scan_serial')) {
            frm.get_field('scan_serial').$input.focus();
        }

        // Client Script: Rental Item Unit - update box condition
        if (frm.doc.unit_type === 'Box' && frm.doc.item_unit_list && frm.doc.item_unit_list.length > 0) {
            sync_child_conditions(frm);
        }
    },

    zone: function (frm) { update_location_code(frm); },
    aisle: function (frm) { update_location_code(frm); },
    section: function (frm) { update_location_code(frm); },
    level: function (frm) { update_location_code(frm); },
    position: function (frm) { update_location_code(frm); },

    scan_serial: function (frm) {
        // Client Script: Rental Item Unit (Parent Box )
        clearTimeout(scanTimer);
        scanTimer = setTimeout(() => {
            if (frm.doc.scan_serial) {
                call_unit_api(frm, frm.doc.scan_serial);
            }
        }, 300);
    },

    item_unit_list_add: function (frm) {
        if (frm.doc.unit_type === 'Box') update_box_unit_condition(frm);
    },

    item_unit_list_remove: function (frm) {
        if (frm.doc.unit_type === 'Box') update_box_unit_condition(frm);
    }
});

frappe.ui.form.on('Box Item Unit Child Table', {
    unit_condition: function (frm) {
        if (frm.doc.unit_type === 'Box') {
            update_box_unit_condition(frm);
        }
    },

    document_id: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.document_id) {
            frappe.db.get_value('Rental Item Unit', row.document_id,
                ['name', 'unit_name', 'unit_condition', 'unit_serial_number', 'unit_type'],
                (d) => {
                    if (d) {
                        if (d.unit_type === "Box") {
                            frappe.msgprint({
                                title: __('Invalid Item'),
                                indicator: 'red',
                                message: __('Item <b>{0}</b> is a <b>Box</b>. Only "Unit" types can be added.', [d.name])
                            });
                            frm.get_field('item_unit_list').grid.grid_rows_by_docname[cdn].remove();
                            frm.refresh_field('item_unit_list');
                            return;
                        }
                        frappe.model.set_value(cdt, cdn, {
                            'unit_name': d.unit_name,
                            'unit_condition': d.unit_condition,
                            'unit_serial_number': d.unit_serial_number
                        });
                    }
                }
            );
        }
    }
});

function update_location_code(frm) {
    let parts = [];
    if (frm.doc.zone) parts.push(frm.doc.zone);
    if (frm.doc.aisle) parts.push(frm.doc.aisle);
    if (frm.doc.section) parts.push(frm.doc.section);
    if (frm.doc.level) parts.push(frm.doc.level);
    if (frm.doc.position) parts.push(frm.doc.position);
    let location = parts.join('-') || '-';
    frm.set_value('location_code', location);
}

function call_unit_api(frm, scan_value) {
    frappe.db.get_list('Rental Item Unit', {
        filters: [
            ["name", "=", scan_value],
            ["or", ["unit_serial_number", "=", scan_value]],
            ["or", ["unit_name", "=", scan_value]]
        ],
        fields: ['name', 'unit_name', 'unit_condition', 'unit_serial_number', 'unit_type'],
        limit: 1
    }).then(res => {
        if (res && res.length > 0) {
            let d = res[0];
            if (d.unit_type === "Box") {
                frappe.msgprint({
                    title: __('Invalid Item'),
                    indicator: 'red',
                    message: __('Item <b>{0}</b> is a <b>Box</b>. A Box cannot be placed inside another Box.', [d.name])
                });
                frm.set_value('scan_serial', '');
                return;
            }
            if (d.name === frm.doc.name) {
                frappe.msgprint(__('A box cannot contain itself.'));
                frm.set_value('scan_serial', '');
                return;
            }
            let exists = (frm.doc.item_unit_list || []).some(row => row.document_id === d.name);
            if (exists) {
                frappe.show_alert({ message: __('Unit already in list'), indicator: 'orange' });
            } else {
                let row = frm.add_child('item_unit_list');
                frappe.model.set_value(row.doctype, row.name, {
                    'document_id': d.name,
                    'unit_name': d.unit_name,
                    'unit_condition': d.unit_condition,
                    'unit_serial_number': d.unit_serial_number
                });
                frm.refresh_field('item_unit_list');
                frappe.show_alert({ message: __('Unit Added'), indicator: 'green' });
            }
        } else {
            frappe.msgprint(__('ID <b>{0}</b> not found.', [scan_value]));
        }
        frm.set_value('scan_serial', '');
        frm.get_field('scan_serial').$input.focus();
    });
}

function sync_child_conditions(frm) {
    const document_ids = frm.doc.item_unit_list.map(row => row.document_id).filter(Boolean);
    if (document_ids.length > 0) {
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Rental Item Unit',
                filters: [['name', 'in', document_ids]],
                fields: ['name', 'unit_condition']
            },
            callback: function (r) {
                if (r.message) {
                    const condition_map = {};
                    r.message.forEach(d => { condition_map[d.name] = d.unit_condition; });
                    frm.doc.item_unit_list.forEach(row => {
                        let latest_cond = condition_map[row.document_id];
                        if (latest_cond && row.unit_condition !== latest_cond) {
                            frappe.model.set_value(row.doctype, row.name, 'unit_condition', latest_cond);
                        }
                    });
                    update_box_unit_condition(frm);
                }
            }
        });
    }
}

function update_box_unit_condition(frm) {
    let conds = (frm.doc.item_unit_list || [])
        .map(r => r.unit_condition)
        .filter(Boolean);

    if (!conds.length) {
        frm.set_value('unit_condition', null);
        return;
    }

    let uniqueConds = [...new Set(conds)];
    let new_cond = uniqueConds.length === 1 ? uniqueConds[0] : 'Partially Ok';

    if (frm.doc.unit_condition !== new_cond) {
        frm.set_value('unit_condition', new_cond);
    }
}
