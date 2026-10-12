"""Movements: check-out, check-in, repair moves and write-offs, scan first. Each one is a Stock Entry."""

import frappe
from frappe import _
from frappe.utils import flt

from rental_management.rental.item import get_box_contents
from rental_management.rental.stock import NOT_IN_STOCK, get_place, get_status, post_movement
from rental_management.ui.common import STOCK_ENTRY, describe_units, like, paging
from rental_management.ui.units import UNIT_FIELDS, load_unit, resolve

UNIT_TYPES = ("CHECK_OUT", "CHECK_IN", "MAINTENANCE_OUT", "MAINTENANCE_IN", "LOST")
BULK_TYPES = ("CHECK_OUT", "CHECK_IN")
REPAIR_SHOP = "Repair Shop"


def status_problem(tx, status):
    if status == NOT_IN_STOCK:
        return _("It is not in rental stock")
    if tx == "CHECK_OUT" and status != "Warehouse":
        return _("It is {0}, not in the warehouse").format(status)
    if tx == "CHECK_IN" and status == "Warehouse":
        return _("It is already in the warehouse")
    if tx == "MAINTENANCE_IN" and status != "In Maintenance":
        return _("It is not in maintenance")
    if tx == "MAINTENANCE_OUT" and status == "In Maintenance":
        return _("It is already in maintenance")
    if tx == "LOST" and status == "Missing":
        return _("It is already marked missing")
    return None


def scan_problem(tx, unit):
    """Why this unit cannot take part in `tx` (None when it can)."""
    if unit["parent_box"]:
        return _("It is packed in box {0}; scan the box or unpack it first").format(unit["parent_box"])
    problem = status_problem(tx, unit["status"])
    if not problem and tx == "CHECK_OUT" and unit["condition"] != "OK":
        problem = _("Its condition is {0}; only OK units can go out").format(unit["condition"])
    return problem or contents_problem(tx, unit)


def contents_problem(tx, unit):
    """A box moves with everything in it, so every unit inside must be able to move too."""
    if unit["kind"] != "Box":
        return None
    for child in get_box_contents(unit["name"]):
        child_unit = load_unit(child)
        problem = status_problem(tx, child_unit["status"])
        if not problem and tx == "CHECK_OUT" and child_unit["condition"] != "OK":
            problem = _("its condition is {0}").format(child_unit["condition"])
        if problem:
            return _("{0} inside: {1}").format(child, problem)
    return None


@frappe.whitelist()
def check_scan(code, transaction_type):
    """Check one scanned code against a movement type before it is added to the list."""
    if transaction_type not in UNIT_TYPES:
        frappe.throw(_("{0} movements do not use scanned units").format(transaction_type))
    name = resolve(code)
    if not name:
        return {"ok": False, "problem": _("No unit with serial {0}").format((code or "").strip()), "unit": None}
    frappe.has_permission("Serial No", "read", doc=name, throw=True)
    unit = load_unit(name)
    problem = scan_problem(transaction_type, unit)
    contents = get_box_contents(name) if unit["kind"] == "Box" else []
    return {"ok": problem is None, "problem": problem, "unit": {**unit, "contents": len(contents)}}


def checked_serials(transaction_type, codes):
    """Resolve and re-check every scanned code; boxes bring their contents along."""
    names = []
    for code in codes:
        name = resolve(code)
        if not name:
            frappe.throw(_("No unit with serial {0}").format(code))
        problem = scan_problem(transaction_type, load_unit(name))
        if problem:
            frappe.throw(_("{0}: {1}").format(code, problem))
        names.append(name)
    if len(set(names)) != len(names):
        frappe.throw(_("A unit appears more than once"))
    return names + [child for name in names for child in get_box_contents(name)]


def get_venue(transaction_type, to_location):
    venue = (to_location or "").strip()
    if transaction_type == "CHECK_OUT" and not venue:
        frappe.throw(_("Say where the equipment is going"))
    if transaction_type == "MAINTENANCE_OUT":
        return venue or REPAIR_SHOP
    return venue if transaction_type == "CHECK_OUT" else None


@frappe.whitelist()
def create_movement(transaction_type, units=None, bulk=None, to_location=None, issued_to=None, received_by=None, note=None):
    """Post a movement. Every unit is re-checked here, so the screen cannot bypass the rules."""
    frappe.has_permission(STOCK_ENTRY, "submit", throw=True)
    if transaction_type not in UNIT_TYPES:
        frappe.throw(_("Unknown movement type {0}").format(transaction_type))
    codes = frappe.parse_json(units) or []
    bulk = frappe.parse_json(bulk) or []
    if bulk and transaction_type not in BULK_TYPES:
        frappe.throw(_("Bulk items can only be checked out or in"))
    if not codes and not bulk:
        frappe.throw(_("Add at least one unit or bulk item"))
    venue = get_venue(transaction_type, to_location)
    return post_movement(
        transaction_type,
        serials=checked_serials(transaction_type, codes),
        bulk=[(row["item_code"], flt(row.get("qty"))) for row in bulk],
        venue=venue,
        issued_to=issued_to,
        received_by=received_by,
        remarks=note,
    )


def movement_filters(transaction_type):
    filters = [["docstatus", "=", 1], ["rental_movement_type", "is", "set"]]
    if transaction_type:
        filters.append(["rental_movement_type", "=", transaction_type])
    return filters


MOVEMENT_FIELDS = [
    "name",
    "rental_movement_type as transaction_type",
    "posting_date",
    "rental_venue",
    "rental_issued_to as issued_to",
    "rental_received_by as received_by",
    "remarks",
    "creation",
    "owner",
]


def row_summaries(names):
    """{movement: {units, bulk, from_location, to_location}} from the Stock Entry rows."""
    if not names:
        return {}
    rows = frappe.db.sql(
        """
        select detail.parent, detail.qty, detail.s_warehouse, detail.t_warehouse, item.has_serial_no
        from `tabStock Entry Detail` detail
        join `tabItem` item on item.name = detail.item_code
        where detail.parent in %(names)s
        """,
        {"names": names},
        as_dict=True,
    )
    summaries = {name: {"units": 0, "bulk": 0, "from": set(), "to": set()} for name in names}
    for row in rows:
        summary = summaries[row.parent]
        if row.has_serial_no:
            summary["units"] += int(row.qty)
        else:
            summary["bulk"] += 1
        summary["from"].add(row.s_warehouse)
        summary["to"].add(row.t_warehouse)
    return summaries


def describe_movement(movement, summary):
    places = lambda warehouses, venue=None: ", ".join(  # noqa: E731
        sorted({get_place(get_status(warehouse), venue) for warehouse in warehouses if warehouse})
    )
    return {
        **movement,
        "units": summary["units"],
        "bulk": summary["bulk"],
        "from_location": places(summary["from"]),
        "to_location": places(summary["to"], movement.rental_venue),
    }


@frappe.whitelist()
def list_movements(search=None, transaction_type=None, page=1, page_length=25):
    start, length = paging(page, page_length)
    filters = movement_filters(transaction_type)
    or_filters = None
    if search:
        pattern = like(search)
        or_filters = [
            ["name", "like", pattern],
            ["rental_venue", "like", pattern],
            ["rental_issued_to", "like", pattern],
            ["rental_received_by", "like", pattern],
        ]
    rows = frappe.get_list(
        STOCK_ENTRY,
        filters=filters,
        or_filters=or_filters,
        fields=MOVEMENT_FIELDS,
        order_by="posting_date desc, posting_time desc, creation desc",
        limit_start=start,
        limit_page_length=length,
    )
    total = len(frappe.get_list(STOCK_ENTRY, filters=filters, or_filters=or_filters, pluck="name", limit_page_length=0))
    summaries = row_summaries([row.name for row in rows])
    return {"rows": [describe_movement(row, summaries[row.name]) for row in rows], "total": total}


def recent_movements(limit=8):
    rows = frappe.get_list(
        STOCK_ENTRY,
        filters=movement_filters(None),
        fields=MOVEMENT_FIELDS,
        order_by="posting_date desc, posting_time desc, creation desc",
        limit_page_length=limit,
    )
    summaries = row_summaries([row.name for row in rows])
    return [describe_movement(row, summaries[row.name]) for row in rows]


def moved_serials(name):
    """{serial: warehouse it left} for the serials on a Stock Entry."""
    rows = frappe.db.sql(
        """
        select entry.serial_no, entry.type_of_transaction, entry.warehouse
        from `tabSerial and Batch Entry` entry
        join `tabSerial and Batch Bundle` bundle on bundle.name = entry.parent
        where bundle.voucher_type = 'Stock Entry' and bundle.voucher_no = %s and bundle.docstatus = 1
        """,
        name,
        as_dict=True,
    )
    serials = {}
    for row in rows:
        if row.type_of_transaction == "Outward" or row.serial_no not in serials:
            serials[row.serial_no] = row.warehouse if row.type_of_transaction == "Outward" else None
    return serials


@frappe.whitelist()
def get_movement(name):
    doc = frappe.get_doc(STOCK_ENTRY, name)
    doc.check_permission("read")
    if not doc.rental_movement_type:
        frappe.throw(_("{0} is not a rental movement").format(name))
    header = frappe._dict({field.split(" as ")[-1]: doc.get(field.split(" as ")[0]) for field in MOVEMENT_FIELDS})
    serials = moved_serials(name)
    units = describe_units(frappe.get_all("Serial No", filters={"name": ["in", list(serials) or ["-"]]}, fields=UNIT_FIELDS, order_by="name asc"))
    for unit in units:
        source = serials[unit["name"]]
        unit["previous"] = get_place(get_status(source)) if source else ""
    return {
        "movement": {**describe_movement(header, row_summaries([name])[name]), "docstatus": doc.docstatus},
        "note": doc.remarks,
        "units": units,
        "bulk": [
            {"item_code": row.item_code, "item_name": row.item_name, "qty": row.qty, "uom": row.uom}
            for row in doc.items
            if not frappe.db.get_value("Item", row.item_code, "has_serial_no")
        ],
    }
