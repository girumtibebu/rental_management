// Live preview of the rental serial number; the server sets the real Serial No Series on save.
frappe.ui.form.on('Item', {
    is_rental_item: update_rental_serial_preview,
    rental_tracking: update_rental_serial_preview,
    rental_model: update_rental_serial_preview,
    rental_item_type: update_rental_serial_preview,
    rental_serial_digits: update_rental_serial_preview,
    brand: update_rental_serial_preview,
});

function update_rental_serial_preview(frm) {
    if (!frm.doc.is_rental_item || frm.doc.rental_tracking === 'Bulk') return;

    const full_code = (val) => (val || '').replace(/[^a-zA-Z0-9]/g, '').toUpperCase();
    const model = full_code(frm.doc.rental_model);
    if (!model) {
        frm.set_value('rental_serial_preview', '');
        return;
    }

    const prefix = frm.doc.rental_tracking === 'Box'
        ? model
        : `${model}-${full_code(frm.doc.brand).substring(0, 2)}-${full_code(frm.doc.rental_item_type).substring(0, 2)}`;
    const digits = parseInt(frm.doc.rental_serial_digits || 3);
    frm.set_value('rental_serial_preview', `${prefix}-${'0'.repeat(digits - 1)}1`);
}
