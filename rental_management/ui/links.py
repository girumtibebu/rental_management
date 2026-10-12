"""Create missing link records (brands, categories, types, storage places) from the rental app."""

import re

import frappe
from frappe import _

from rental_management.rental.setup.install import RENTAL_ITEM_GROUP

# doctype -> the field holding the typed name, plus fixed values for the new record
CREATABLE = {
    "Brand": ("brand", {}),
    "UOM": ("uom_name", {}),
    "Item Group": ("item_group_name", {"parent_item_group": RENTAL_ITEM_GROUP, "is_group": 0}),
    "Rent Item Type": ("type_name", {}),
    "Zone": ("zone_name", {}),
    "Aisle": ("aisle_name", {}),
    "Section": ("section_name", {}),
    "Level": ("level_name", {}),
    "Position": ("position_name", {}),
}


@frappe.whitelist(methods=["POST"])
def quick_create(doctype, value):
    """Insert a `doctype` record named `value` (or return the existing one) and give back its name."""
    if doctype not in CREATABLE:
        frappe.throw(_("{0} records can't be created from the rental app").format(doctype))
    value = (value or "").strip()
    if not value:
        frappe.throw(_("Enter a name first"))
    if frappe.db.exists(doctype, value):
        return value
    field, defaults = CREATABLE[doctype]
    doc = frappe.get_doc({"doctype": doctype, field: value, **defaults})
    if doctype == "Rent Item Type":
        doc.type_code = unique_type_code(value)
    doc.insert()
    return doc.name


def unique_type_code(name):
    base = re.sub(r"[^A-Za-z0-9]", "", name).upper()[:3] or "TYP"
    code, n = base, 1
    while frappe.db.exists("Rent Item Type", {"type_code": code}):
        n += 1
        code = f"{base}{n}"
    return code
