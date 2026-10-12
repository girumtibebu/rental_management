const RENTAL_LOCATION_FIELDS = ['rental_zone', 'rental_aisle', 'rental_section', 'rental_level', 'rental_position'];

frappe.ui.form.on('Serial No', Object.fromEntries(
    RENTAL_LOCATION_FIELDS.map(field => [field, update_location_code])
));

function update_location_code(frm) {
    const parts = RENTAL_LOCATION_FIELDS.map(field => frm.doc[field]).filter(Boolean);
    frm.set_value('location_code', parts.join('-') || '-');
}
