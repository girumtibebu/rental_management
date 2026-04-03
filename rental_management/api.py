import frappe
from frappe import _


def _get_effective_unit_condition(unit_name, fallback_condition=None):
    """Prefer latest completed maintenance final condition as current condition."""
    final_condition = frappe.db.get_value(
        "Rental Item Maintenance",
        {
            "unit_serial_number": unit_name,
            "workflow_state": "Complete",
            "final_condition": ["is", "set"],
        },
        "final_condition",
        order_by="modified desc",
    )
    return final_condition or fallback_condition

@frappe.whitelist()
def create_rental_item_units(template_name, total_units=1):
    """
    Creates multiple Rental Item Unit records based on a template.
    """
    total_units = int(total_units)
    if not template_name:
        frappe.throw(_("Template name is required"))

    template = frappe.get_doc("Rental Item Template", template_name)
    series_template = template.sku_naming_series or "UNIT-###"

    # Determine prefix and digits by stripping trailing #'s
    i = len(series_template) - 1
    while i >= 0 and series_template[i] == "#":
        i -= 1

    prefix = series_template[:i+1]
    digits = len(series_template) - (i+1)
    if digits == 0:
        digits = 2  # default if no # at the end

    # Fetch existing serial numbers
    existing_serials = frappe.get_all(
        "Rental Item Unit",
        filters={"item_template": template_name},
        pluck="unit_serial_number"
    )

    # Find the highest numeric suffix used
    max_number = 0
    for s in existing_serials:
        if s.startswith(prefix):
            number_part = s.replace(prefix, "")
            if number_part.isdigit():
                max_number = max(max_number, int(number_part))

    # Create new units starting from max_number + 1
    units_created = []
    for i in range(1, total_units + 1):
        number = max_number + i
        number_part = str(number).zfill(digits)
        serial_number = prefix + number_part

        doc = frappe.get_doc({
            "doctype": "Rental Item Unit",
            "item_template": template_name,
            "unit_serial_number": serial_number
        })
        doc.insert()
        units_created.append(serial_number)

    frappe.db.commit()

    return {"units_created": units_created}

@frappe.whitelist()
def get_rental_unit_by_serial(serial_number):
    """
    Used by Maintenance barcode scan.
    """
    if not serial_number:
        return None

    serial = serial_number.strip()
    
    # Fetch data including unit_condition
    unit_data = frappe.db.get_value("Rental Item Unit", 
        {"unit_serial_number": serial}, 
        ["name", "unit_name", "unit_serial_number", "unit_condition"], 
        as_dict=True
    )
    
    if not unit_data:
        frappe.msgprint(_("Unit with Serial {0} not found.").format(serial))
        return None
        
    if unit_data.unit_condition != "OK":
        # Block the scan if not OK
        frappe.msgprint(_("Unit {0} is currently labeled '{1}'. It's already scheduled for maintenance.").format(unit_data.name, unit_data.unit_condition))
        return None

    return unit_data

@frappe.whitelist()
def handle_unit_scan(serial):
    """
    Used by Movement barcode scan.
    """
    serial = (serial or "").strip()

    if not serial:
        frappe.throw(_("No barcode provided."))

    unit_info = frappe.db.get_value('Rental Item Unit', 
        {'unit_serial_number': serial}, 
        ['name', 'unit_serial_number', 'unit_name', 'unit_condition', 'unit_location', 'movement_status'], 
        as_dict=True
    )

    if not unit_info:
        frappe.throw(_("Unit with Serial {0} not found.").format(serial))

    effective_condition = _get_effective_unit_condition(
        unit_info.name,
        unit_info.unit_condition,
    )
    unit_info.current_condition = effective_condition
    unit_info.unit_condition = effective_condition

    return unit_info

@frappe.whitelist()
def handle_unit_scan_2(barcode):
    """
    Used by Movement barcode scan on templates (Bulk items).
    """
    if not barcode:
        frappe.throw(_("Missing barcode"))

    # Alias the fields to match what the Client Script expects
    unit_data = frappe.db.sql("""
        SELECT 
            u.item_template, 
            t.item_name,
            t.rental_item_type_box as template_type
        FROM `tabRental Item Unit` u
        JOIN `tabRental Item Template` t ON u.item_template = t.name
        WHERE u.unit_serial_number = %s
    """, (barcode,), as_dict=True)

    if not unit_data:
        frappe.throw(_("Unit {0} not found").format(barcode))

    return unit_data[0]
