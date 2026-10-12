"""Shared helpers for the rental interface API."""

import frappe

UNIT = "Rental Item Unit"
TEMPLATE = "Rental Item Template"
MOVEMENT = "Rental Movement"
MAINTENANCE = "Rental Item Maintenance"
UNIT_LOG = "Rental Unit Log"
BULK_ITEM = "Bulk Item"

STATUSES = ("Warehouse", "At Event", "In Maintenance", "Missing")
CONDITIONS = ("OK", "Need Cleaning", "Damaged", "Partially Ok", "Scrapped")


def paging(page=1, page_length=25):
    length = max(1, min(int(page_length or 25), 200))
    return (max(1, int(page or 1)) - 1) * length, length


def like(text):
    return f"%{(text or '').strip()}%"


def location_label(unit):
    """A readable place for a unit: 'Warehouse' for stocked units, the event/venue otherwise."""
    place = (unit.get("unit_location") or "").strip()
    if place and place.lower() != "none":
        return place
    return "Warehouse" if unit.get("movement_status") == "Warehouse" else ""


def storage_path(unit):
    """Warehouse storage address: zone / section / level / position."""
    parts = [unit.get(field) for field in ("zone", "section", "level", "position")]
    return " / ".join(part for part in parts if part)


def template_index(names):
    """{template name: summary} for the templates in `names`."""
    names = [name for name in set(names) if name]
    if not names:
        return {}
    rows = frappe.get_all(
        TEMPLATE,
        filters={"name": ["in", names]},
        fields=[
            "name",
            "item_name",
            "item_model",
            "item_category",
            "item_type",
            "item_brand",
            "rental_item_type_box",
            "image",
            "uom",
            "status",
        ],
    )
    return {row.name: row for row in rows}
