"""Dashboard: where the equipment is and what needs attention."""

import frappe

from rental_management.ui.catalog import unit_counts
from rental_management.ui.common import MAINTENANCE, MOVEMENT, STATUSES, TEMPLATE, UNIT, UNIT_LOG, template_index

LOW_AVAILABILITY = 0.25


def status_totals():
    rows = frappe.db.sql(
        "select movement_status, count(*) as n from `tabRental Item Unit` where disabled = 0 group by movement_status",
        as_dict=True,
    )
    found = {row.movement_status: row.n for row in rows}
    return {status: found.get(status, 0) for status in STATUSES}


def condition_totals():
    rows = frappe.db.sql(
        "select unit_condition, count(*) as n from `tabRental Item Unit` where disabled = 0 group by unit_condition order by n desc",
        as_dict=True,
    )
    return [{"condition": row.unit_condition or "Unknown", "count": row.n} for row in rows]


def events_out():
    """Where equipment currently is when it is not in the warehouse."""
    return frappe.db.sql(
        """
        select ifnull(nullif(unit_location, 'None'), 'Unknown') as location, movement_status, count(*) as units
        from `tabRental Item Unit`
        where disabled = 0 and movement_status in ('At Event', 'In Maintenance', 'Missing')
        group by location, movement_status
        order by units desc
        limit 12
        """,
        as_dict=True,
    )


def tight_templates():
    """Serialised templates with the least stock left in the warehouse in good condition."""
    counts = unit_counts()
    ranked = []
    for name, entry in counts.items():
        if entry["total"] >= 2:
            ranked.append((entry["available"] / entry["total"], name, entry))
    ranked.sort(key=lambda item: (item[0], -item[2]["total"]))
    templates = template_index([name for _ratio, name, _entry in ranked[:6]])
    return [
        {
            "name": name,
            "item_name": templates.get(name, {}).get("item_name") or name,
            "category": templates.get(name, {}).get("item_category"),
            "total": entry["total"],
            "available": entry["available"],
            "out": entry["At Event"],
            "tight": ratio <= LOW_AVAILABILITY,
        }
        for ratio, name, entry in ranked[:6]
    ]


def recent_movements():
    return frappe.get_all(
        MOVEMENT,
        fields=["name", "transaction_type", "posting_date", "from_location", "to_location", "creation", "owner"],
        order_by="creation desc",
        limit=8,
    )


def open_tickets():
    return frappe.get_all(
        MAINTENANCE,
        filters={"workflow_state": ["in", ["Attention Required", "In Repair"]], "docstatus": ["<", 2]},
        fields=["name", "unit_name", "serial_number", "workflow_state", "unit_condition", "issue_description", "creation"],
        order_by="creation desc",
        limit=8,
    )


def recent_activity():
    return frappe.get_all(
        UNIT_LOG,
        fields=["name", "unit", "event_type", "from_location", "to_location", "status", "date", "reference_doctype", "reference_name"],
        order_by="date desc",
        limit=12,
    )


@frappe.whitelist()
def get_dashboard():
    for doctype in (UNIT, TEMPLATE):
        frappe.has_permission(doctype, "read", throw=True)
    totals = status_totals()
    conditions = condition_totals()
    total = sum(totals.values())
    needs = sum(item["count"] for item in conditions if item["condition"] != "OK")
    return {
        "totals": {**totals, "total": total, "needs_attention": needs, "templates": frappe.db.count(TEMPLATE)},
        "conditions": conditions,
        "locations": events_out(),
        "tight": tight_templates(),
        "movements": recent_movements(),
        "tickets": open_tickets(),
        "activity": recent_activity(),
    }
