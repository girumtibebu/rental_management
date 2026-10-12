"""Rental behaviour on the native Item and Serial No doctypes."""

import re

import frappe
from frappe import _

from rental_management.rental.setup.custom_fields import LOCATION_DOCTYPES

SERIAL_TRACKING = ("Unit", "Box")


def _full_code(value):
    return re.sub(r"[^a-zA-Z0-9]", "", value or "").upper()


def get_serial_prefix(model, brand=None, item_type=None, tracking="Unit"):
    """Serial prefix, identical to the SKU the old Rental Item Template generated.

    Unit: MODEL-BR-TY  (first two characters of brand and type)
    Box:  MODEL
    """
    model_code = _full_code(model)
    if not model_code:
        return None
    if tracking == "Box":
        return model_code
    return f"{model_code}-{_full_code(brand)[:2]}-{_full_code(item_type)[:2]}"


def get_serial_no_series(prefix, digits):
    # "TBL-AC-FU-.###" makes TBL-AC-FU-001, TBL-AC-FU-002, ...
    return f"{prefix}-.{'#' * int(digits)}"


def validate_item(doc, method=None):
    if not doc.is_rental_item:
        return

    doc.is_stock_item = 1

    if doc.rental_tracking == "Bulk":
        doc.has_serial_no = 0
        doc.rental_serial_preview = None
        return

    prefix = get_serial_prefix(doc.rental_model, doc.brand, doc.rental_item_type, doc.rental_tracking)
    if not prefix:
        frappe.throw(_("Model is required to build the serial number for a rental item."))

    digits = int(doc.rental_serial_digits or 3)
    series = get_serial_no_series(prefix, digits)

    if doc.serial_no_series and doc.serial_no_series != series and _has_serial_nos(doc.name):
        frappe.throw(
            _(
                "Serial numbers already exist for this item under {0}. Changing Model, Brand, "
                "Rental Item Type or Serial Digits would start a new series {1}."
            ).format(frappe.bold(doc.serial_no_series), frappe.bold(series))
        )

    doc.has_serial_no = 1
    doc.serial_no_series = series
    doc.rental_serial_preview = f"{prefix}-{'0' * (digits - 1)}1"


def _has_serial_nos(item_code):
    return bool(item_code) and frappe.db.exists("Serial No", {"item_code": item_code})


def get_location_code(doc):
    """Zone-Aisle-Section-Level-Position, matching the codes on existing shelf labels."""
    parts = [doc.get(f"rental_{doctype.lower()}") for doctype in LOCATION_DOCTYPES]
    return "-".join(p for p in parts if p) or "-"


def validate_serial_no(doc, method=None):
    doc.location_code = get_location_code(doc)

    if doc.parent_box:
        if doc.parent_box == doc.name:
            frappe.throw(_("A serial number cannot be its own parent box."))
        box = frappe.db.get_value("Serial No", doc.parent_box, ["item_code", "warehouse"], as_dict=True)
        if frappe.db.get_value("Item", box.item_code, "rental_tracking") != "Box":
            frappe.throw(_("{0} is not a box serial number.").format(frappe.bold(doc.parent_box)))
        if doc.has_value_changed("parent_box") and box.warehouse != doc.warehouse:
            frappe.throw(_("{0} and the box {1} are not in the same warehouse.").format(doc.name, doc.parent_box))


def on_update_serial_no(doc, method=None):
    if doc.has_value_changed("parent_box"):
        for box in {doc.parent_box, (doc.get_doc_before_save() or {}).get("parent_box")}:
            refresh_box_condition(box)


def get_box_contents(box):
    return frappe.get_all("Serial No", filters={"parent_box": box}, pluck="name", order_by="name asc")


def set_condition(serial, condition):
    frappe.db.set_value("Serial No", serial, "rental_condition", condition)
    refresh_box_condition(frappe.db.get_value("Serial No", serial, "parent_box"))


def refresh_box_condition(box):
    """A box takes the condition its contents share, or Partially Ok when they differ."""
    if not box:
        return
    conditions = set(frappe.get_all("Serial No", filters={"parent_box": box}, pluck="rental_condition"))
    if conditions:
        frappe.db.set_value("Serial No", box, "rental_condition", conditions.pop() if len(conditions) == 1 else "Partially Ok")
