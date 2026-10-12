"""Rental fields added to the native Item, Serial No and Stock Entry doctypes.

Rental items live on the ERPNext Item master, individual units are native
Serial Nos and movements are Stock Entries. These fields carry the
rental-specific data on top of them.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from rental_management.rental.stock import MOVEMENT_TYPES

RENTAL_CONDITIONS = "OK\nNeed Cleaning\nPartially Ok\nDamaged\nScrapped"
LOCATION_DOCTYPES = ("Zone", "Aisle", "Section", "Level", "Position")


def get_custom_fields():
    item_fields = [
        {"fieldname": "rental_tab", "fieldtype": "Tab Break", "label": "Rental", "insert_after": "prices_html"},
        {
            "fieldname": "is_rental_item",
            "fieldtype": "Check",
            "label": "Is Rental Item",
            "insert_after": "rental_tab",
            "in_standard_filter": 1,
        },
        {
            "fieldname": "rental_tracking",
            "fieldtype": "Select",
            "label": "Tracked As",
            "options": "Unit\nBox\nBulk",
            "default": "Unit",
            "insert_after": "is_rental_item",
            "depends_on": "is_rental_item",
            "mandatory_depends_on": "is_rental_item",
            "description": "Unit and Box are tracked by serial number, Bulk by quantity.",
        },
        {
            "fieldname": "rental_item_type",
            "fieldtype": "Link",
            "label": "Rental Item Type",
            "options": "Rent Item Type",
            "insert_after": "rental_tracking",
            "depends_on": "is_rental_item",
        },
        {
            "fieldname": "rental_model",
            "fieldtype": "Data",
            "label": "Model",
            "insert_after": "rental_item_type",
            "depends_on": "is_rental_item",
            "mandatory_depends_on": "eval:doc.is_rental_item && doc.rental_tracking != 'Bulk'",
        },
        {
            "fieldname": "rental_size",
            "fieldtype": "Data",
            "label": "Size",
            "insert_after": "rental_model",
            "depends_on": "is_rental_item",
        },
        {"fieldname": "rental_column_break", "fieldtype": "Column Break", "insert_after": "rental_size"},
        {
            "fieldname": "rental_serial_digits",
            "fieldtype": "Select",
            "label": "Serial Digits",
            "options": "1\n2\n3\n4",
            "default": "3",
            "insert_after": "rental_column_break",
            "depends_on": "eval:doc.is_rental_item && doc.rental_tracking != 'Bulk'",
            "mandatory_depends_on": "eval:doc.is_rental_item && doc.rental_tracking != 'Bulk'",
        },
        {
            "fieldname": "rental_serial_preview",
            "fieldtype": "Data",
            "label": "Next Serial Looks Like",
            "read_only": 1,
            "no_copy": 1,
            "insert_after": "rental_serial_digits",
            "depends_on": "eval:doc.is_rental_item && doc.rental_tracking != 'Bulk'",
            "description": "Built from Model, Brand and Rental Item Type. Sets the Serial No Series below.",
        },
    ]

    serial_no_fields = [
        {
            "fieldname": "rental_details_section",
            "fieldtype": "Section Break",
            "label": "Rental",
            "insert_after": "brand",
        },
        {
            "fieldname": "rental_condition",
            "fieldtype": "Select",
            "label": "Condition",
            "options": RENTAL_CONDITIONS,
            "default": "OK",
            "insert_after": "rental_details_section",
            "in_list_view": 1,
            "in_standard_filter": 1,
        },
        {
            "fieldname": "parent_box",
            "fieldtype": "Link",
            "label": "Parent Box",
            "options": "Serial No",
            "insert_after": "rental_condition",
            "description": "The box serial this unit is packed in.",
        },
        {"fieldname": "rental_location_column", "fieldtype": "Column Break", "insert_after": "parent_box"},
    ]

    insert_after = "rental_location_column"
    for doctype in LOCATION_DOCTYPES:
        fieldname = f"rental_{doctype.lower()}"
        serial_no_fields.append(
            {
                "fieldname": fieldname,
                "fieldtype": "Link",
                "label": doctype,
                "options": doctype,
                "insert_after": insert_after,
            }
        )
        insert_after = fieldname

    serial_no_fields.append(
        {
            "fieldname": "location_code",
            "fieldtype": "Data",
            "label": "Location Code",
            "read_only": 1,
            "insert_after": insert_after,
            "in_standard_filter": 1,
        }
    )

    stock_entry_fields = [
        {
            "fieldname": "rental_movement_type",
            "fieldtype": "Select",
            "label": "Rental Movement",
            "options": "\n" + "\n".join(MOVEMENT_TYPES),
            "insert_after": "stock_entry_type",
            "read_only": 1,
            "in_standard_filter": 1,
            "description": "Set by the Rental app. The warehouse a serial is in is its rental status.",
        },
        {
            "fieldname": "rental_venue",
            "fieldtype": "Data",
            "label": "Venue",
            "insert_after": "rental_movement_type",
            "read_only": 1,
            "depends_on": "rental_movement_type",
        },
        {
            "fieldname": "rental_issued_to",
            "fieldtype": "Data",
            "label": "Issued To",
            "insert_after": "rental_venue",
            "read_only": 1,
            "depends_on": "rental_movement_type",
        },
        {
            "fieldname": "rental_received_by",
            "fieldtype": "Data",
            "label": "Received By",
            "insert_after": "rental_issued_to",
            "read_only": 1,
            "depends_on": "rental_movement_type",
        },
    ]

    return {"Item": item_fields, "Serial No": serial_no_fields, "Stock Entry": stock_entry_fields}


def setup_custom_fields():
    # rental status is the serial's warehouse since v2.0.2
    frappe.delete_doc("Custom Field", "Serial No-rental_status", ignore_missing=True, force=True)
    create_custom_fields(get_custom_fields(), update=True)
