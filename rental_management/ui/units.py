"""Units: rental equipment tracked by native Serial No."""

import frappe
from frappe import _

from rental_management.rental.item import get_box_contents
from rental_management.rental.stock import NOT_IN_STOCK, get_place, get_status, get_venues, get_warehouse
from rental_management.ui.common import MAINTENANCE, STOCK_ENTRY, describe_units, item_index, like, paging

UNIT_FIELDS = [
    "name",
    "item_code",
    "item_name",
    "warehouse",
    "rental_condition",
    "parent_box",
    "location_code",
    "rental_zone",
    "rental_aisle",
    "rental_section",
    "rental_level",
    "rental_position",
    "modified",
    "creation",
    "owner",
]
STORAGE_FIELDS = ("rental_zone", "rental_aisle", "rental_section", "rental_level", "rental_position")


def get_rental_items(item_code=None, category=None, kind=None):
    filters = {"is_rental_item": 1, "rental_tracking": ["in", ["Unit", "Box"]]}
    for field, value in (("name", item_code), ("item_group", category), ("rental_tracking", kind)):
        if value:
            filters[field] = value
    return frappe.get_all("Item", filters=filters, pluck="name") or ["-"]


def build_filters(status, condition, item_code, category, kind, boxed):
    filters = [["item_code", "in", get_rental_items(item_code, category, kind)]]
    if status == NOT_IN_STOCK:
        filters.append(["warehouse", "is", "not set"])
    elif status:
        filters.append(["warehouse", "=", get_warehouse(status)])
    if condition:
        filters.append(["rental_condition", "=", condition])
    if boxed == "boxed":
        filters.append(["parent_box", "is", "set"])
    return filters


def serials_at(location, filters):
    """Serials whose current venue matches `location`."""
    names = frappe.get_list("Serial No", filters=filters, pluck="name", limit_page_length=0)
    venues = get_venues(names)
    pattern = (location or "").strip().lower()
    return [name for name in names if pattern in (venues.get(name) or "").lower()] or ["-"]


@frappe.whitelist()
def list_units(
    search=None,
    status=None,
    condition=None,
    item_code=None,
    category=None,
    kind=None,
    location=None,
    boxed=None,
    page=1,
    page_length=25,
):
    start, length = paging(page, page_length)
    filters = build_filters(status, condition, item_code, category, kind, boxed)
    if location:
        filters.append(["name", "in", serials_at(location, filters)])
    or_filters = None
    if search:
        pattern = like(search)
        or_filters = [["name", "like", pattern], ["item_name", "like", pattern], ["location_code", "like", pattern]]
    rows = frappe.get_list(
        "Serial No",
        filters=filters,
        or_filters=or_filters,
        fields=UNIT_FIELDS,
        order_by="modified desc",
        limit_start=start,
        limit_page_length=length,
    )
    total = len(frappe.get_list("Serial No", filters=filters, or_filters=or_filters, pluck="name", limit_page_length=0))
    return {"rows": describe_units(rows), "total": total}


def resolve(code):
    """The rental serial for a scanned code, or None."""
    code = (code or "").strip()
    if not code:
        return None
    item_code = frappe.db.get_value("Serial No", code, "item_code")
    return code if item_code and frappe.db.get_value("Item", item_code, "is_rental_item") else None


def load_unit(name):
    return describe_units([frappe.db.get_value("Serial No", name, UNIT_FIELDS, as_dict=True)])[0]


@frappe.whitelist()
def find_unit(code):
    """Look a scanned code up; returns None (not an error) when nothing matches."""
    name = resolve(code)
    if not name:
        return None
    frappe.has_permission("Serial No", "read", doc=name, throw=True)
    return load_unit(name)


def movement_events(name):
    """Every Stock Entry that moved this serial, with where it came from and went to."""
    rows = frappe.db.sql(
        """
        select entry.voucher_no, entry.type_of_transaction, entry.warehouse
        from `tabSerial and Batch Entry` entry
        join `tabSerial and Batch Bundle` bundle on bundle.name = entry.parent
        where entry.serial_no = %s and bundle.voucher_type = 'Stock Entry'
            and bundle.docstatus = 1 and bundle.is_cancelled = 0
        """,
        name,
        as_dict=True,
    )
    moves = {}
    for row in rows:
        side = "to" if row.type_of_transaction == "Inward" else "from"
        moves.setdefault(row.voucher_no, {})[side] = get_status(row.warehouse)
    if not moves:
        return []
    entries = frappe.get_all(
        STOCK_ENTRY,
        filters={"name": ["in", list(moves)]},
        fields=["name", "rental_movement_type", "purpose", "rental_venue", "posting_date", "posting_time", "owner"],
    )
    return [
        {
            "name": entry.name,
            "kind": "Movement",
            "reference_name": entry.name,
            "status": entry.rental_movement_type or entry.purpose,
            "from_location": get_place(moves[entry.name].get("from")) if moves[entry.name].get("from") else "",
            "to_location": get_place(moves[entry.name].get("to"), entry.rental_venue) if moves[entry.name].get("to") else "",
            "when": f"{entry.posting_date} {entry.posting_time}",
            "owner": entry.owner,
        }
        for entry in entries
    ]


def ticket_events(name):
    tickets = frappe.get_all(
        MAINTENANCE,
        filters={"serial_no": name},
        fields=["name", "workflow_state", "issue_description", "creation", "owner"],
        order_by="creation desc",
        limit=30,
    )
    return [
        {
            "name": ticket.name,
            "kind": "Maintenance ticket",
            "reference_name": ticket.name,
            "status": ticket.workflow_state,
            "detail": ticket.issue_description,
            "when": str(ticket.creation),
            "owner": ticket.owner,
        }
        for ticket in tickets
    ]


def history(name):
    """Movements and maintenance for a serial, newest first."""
    events = movement_events(name) + ticket_events(name)
    events.sort(key=lambda event: event["when"], reverse=True)
    return events[:80]


def open_ticket(name):
    return frappe.db.get_value(
        MAINTENANCE,
        {"serial_no": name, "docstatus": 0},
        ["name", "workflow_state"],
        as_dict=True,
    )


@frappe.whitelist()
def get_unit(name):
    doc = frappe.get_doc("Serial No", name)
    doc.check_permission("read")
    unit = load_unit(name)
    item = item_index([doc.item_code]).get(doc.item_code) or {}
    contents = get_box_contents(name) if unit["kind"] == "Box" else []
    return {
        "unit": unit,
        "item": item,
        "parent_box": doc.parent_box,
        "contents": describe_units([frappe.db.get_value("Serial No", child, UNIT_FIELDS, as_dict=True) for child in contents]),
        "open_ticket": open_ticket(name),
        "history": history(name),
        "can": {
            "write": bool(frappe.has_permission("Serial No", "write", doc=doc)),
            "move": bool(frappe.has_permission(STOCK_ENTRY, "submit")),
            "maintain": bool(frappe.has_permission(MAINTENANCE, "create")),
        },
    }


@frappe.whitelist()
def update_storage(name, rental_zone=None, rental_aisle=None, rental_section=None, rental_level=None, rental_position=None):
    """Set where a stocked unit lives in the warehouse."""
    doc = frappe.get_doc("Serial No", name)
    doc.check_permission("write")
    if get_status(doc.warehouse) != "Warehouse":
        frappe.throw(_("Only units in the warehouse can be given a storage address"))
    values = (rental_zone, rental_aisle, rental_section, rental_level, rental_position)
    for field, value in zip(STORAGE_FIELDS, values, strict=True):
        doc.set(field, value or None)
    doc.save()
    return get_unit(name)


@frappe.whitelist()
def pack(box, units):
    """Put units into a box serial, or take them out when `box` is empty."""
    for code in frappe.parse_json(units) or []:
        name = resolve(code)
        if not name:
            frappe.throw(_("No unit with serial {0}").format(code))
        doc = frappe.get_doc("Serial No", name)
        doc.check_permission("write")
        doc.parent_box = box or None
        doc.save()
    return get_unit(box) if box else None
