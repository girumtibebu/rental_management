"""Shared helpers for the rental interface API."""

import frappe

from rental_management.rental.stock import get_place, get_status, get_venues

MAINTENANCE = "Rental Item Maintenance"
STOCK_ENTRY = "Stock Entry"
CONDITIONS = ("OK", "Need Cleaning", "Damaged", "Partially Ok", "Scrapped")
ITEM_FIELDS = [
    "name",
    "item_name",
    "item_group",
    "brand",
    "rental_item_type",
    "rental_model",
    "rental_tracking",
    "rental_size",
    "stock_uom",
    "image",
    "serial_no_series",
    "rental_serial_preview",
    "disabled",
    "modified",
]


def has_app_permission():
    return bool(frappe.has_permission("Serial No", "read") and frappe.has_permission("Item", "read"))


def paging(page=1, page_length=25):
    length = max(1, min(int(page_length or 25), 200))
    return (max(1, int(page or 1)) - 1) * length, length


def like(text):
    return f"%{(text or '').strip()}%"


def item_index(names):
    """{item_code: summary} for the rental items in `names`."""
    names = [name for name in set(names) if name]
    if not names:
        return {}
    return {row.name: row for row in frappe.get_all("Item", filters={"name": ["in", names]}, fields=ITEM_FIELDS)}


def describe_item(item):
    return {**item, "item_code": item.name, "category": item.item_group, "kind": item.rental_tracking}


def describe_units(units):
    """Add status, place, storage and item details to Serial No rows."""
    items = item_index([unit.item_code for unit in units])
    venues = get_venues([unit.name for unit in units])
    described = []
    for unit in units:
        item = items.get(unit.item_code) or {}
        status = get_status(unit.warehouse)
        described.append(
            {
                **unit,
                "serial_no": unit.name,
                "status": status,
                "condition": unit.rental_condition,
                "location": get_place(status, venues.get(unit.name)),
                "storage": unit.location_code if unit.location_code not in (None, "", "-") else "",
                "category": item.get("item_group"),
                "kind": item.get("rental_tracking"),
                "image": item.get("image"),
            }
        )
    return described
