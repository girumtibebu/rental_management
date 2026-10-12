"""Dashboard: where the equipment is and what needs attention."""

import frappe

from rental_management.rental.stock import STATUSES, get_venues, get_warehouse_statuses
from rental_management.ui.catalog import serial_counts
from rental_management.ui.common import MAINTENANCE, item_index
from rental_management.ui.movements import recent_movements

LOW_AVAILABILITY = 0.25
OUT_STATUSES = ("At Event", "In Maintenance", "Missing")


def get_rental_serials():
    """Serials of rental items that are in one of the rental warehouses."""
    statuses = get_warehouse_statuses()
    return frappe.db.sql(
        """
        select serial.name, serial.item_code, serial.warehouse, serial.rental_condition
        from `tabSerial No` serial
        join `tabItem` item on item.name = serial.item_code
        where item.is_rental_item = 1 and serial.warehouse in %(warehouses)s
        """,
        {"warehouses": list(statuses)},
        as_dict=True,
    )


def status_totals(serials):
    statuses = get_warehouse_statuses()
    totals = dict.fromkeys(STATUSES, 0)
    for serial in serials:
        totals[statuses[serial.warehouse]] += 1
    return totals


def condition_totals(serials):
    counts = {}
    for serial in serials:
        condition = serial.rental_condition or "Unknown"
        counts[condition] = counts.get(condition, 0) + 1
    return [{"condition": condition, "count": count} for condition, count in sorted(counts.items(), key=lambda item: -item[1])]


def events_out(serials):
    """Where equipment currently is when it is not in the warehouse."""
    statuses = get_warehouse_statuses()
    out = [serial for serial in serials if statuses[serial.warehouse] in OUT_STATUSES]
    venues = get_venues([serial.name for serial in out])
    groups = {}
    for serial in out:
        key = (venues.get(serial.name) or "Unknown", statuses[serial.warehouse])
        groups[key] = groups.get(key, 0) + 1
    rows = [{"location": location, "status": status, "units": units} for (location, status), units in groups.items()]
    return sorted(rows, key=lambda row: -row["units"])[:12]


def tight_items(serials):
    """Serialised items with the least stock left in the warehouse in good condition."""
    counts = serial_counts({serial.item_code for serial in serials})
    ranked = sorted(
        ((entry["available"] / entry["total"], name, entry) for name, entry in counts.items() if entry["total"] >= 2),
        key=lambda item: (item[0], -item[2]["total"]),
    )[:6]
    items = item_index([name for _ratio, name, _entry in ranked])
    return [
        {
            "name": name,
            "item_name": items.get(name, {}).get("item_name") or name,
            "category": items.get(name, {}).get("item_group"),
            "total": entry["total"],
            "available": entry["available"],
            "out": entry["At Event"],
            "tight": ratio <= LOW_AVAILABILITY,
        }
        for ratio, name, entry in ranked
    ]


def open_tickets():
    return frappe.get_all(
        MAINTENANCE,
        filters={"workflow_state": ["in", ["Attention Required", "In Repair"]], "docstatus": 0},
        fields=["name", "serial_no", "item_name", "workflow_state", "unit_condition", "issue_description", "creation"],
        order_by="creation desc",
        limit=8,
    )


@frappe.whitelist()
def get_dashboard():
    for doctype in ("Serial No", "Item"):
        frappe.has_permission(doctype, "read", throw=True)
    serials = get_rental_serials()
    totals = status_totals(serials)
    conditions = condition_totals(serials)
    return {
        "totals": {
            **totals,
            "total": len(serials),
            "needs_attention": sum(item["count"] for item in conditions if item["condition"] != "OK"),
            "items": frappe.db.count("Item", {"is_rental_item": 1, "disabled": 0}),
        },
        "conditions": conditions,
        "locations": events_out(serials),
        "tight": tight_items(serials),
        "movements": recent_movements(),
        "tickets": open_tickets(),
    }
