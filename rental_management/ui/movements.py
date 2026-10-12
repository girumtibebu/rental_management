"""Movements: check-out, check-in, maintenance moves and write-offs, scan first."""

import frappe
from frappe import _

from rental_management.api import _get_effective_unit_condition
from rental_management.ui.common import MOVEMENT, UNIT, like, location_label, paging
from rental_management.ui.units import resolve

TYPES = ("CHECK_OUT", "CHECK_IN", "MAINTENANCE_OUT", "MAINTENANCE_IN", "LOST", "PURCHASE", "DISPOSE")
UNIT_TYPES = ("CHECK_OUT", "CHECK_IN", "MAINTENANCE_OUT", "MAINTENANCE_IN", "LOST")
WAREHOUSE = "Warehouse"
UNIT_FIELDS = ["name", "unit_serial_number", "unit_name", "item_template", "movement_status", "unit_location", "unit_condition", "unit_type"]


def scan_problem(tx, unit):
    """Why this unit cannot take part in `tx` (None when it can). Mirrors the Desk form's rules."""
    status, condition = unit.movement_status, unit.unit_condition
    if tx == "CHECK_OUT":
        if status != WAREHOUSE:
            return _("It is {0}, not in the warehouse").format(status)
        if condition != "OK":
            return _("Its condition is {0}; only OK units can go out").format(condition)
    elif tx == "CHECK_IN" and status == WAREHOUSE:
        return _("It is already in the warehouse")
    elif tx == "MAINTENANCE_IN" and status != "In Maintenance":
        return _("It is not in maintenance")
    elif tx == "MAINTENANCE_OUT" and status == "In Maintenance":
        return _("It is already in maintenance")
    elif tx == "LOST" and status == "Missing":
        return _("It is already marked missing")
    return None


def load_unit(name):
    unit = frappe.db.get_value(UNIT, name, UNIT_FIELDS, as_dict=True)
    unit.unit_condition = _get_effective_unit_condition(name, unit.unit_condition)
    return unit


@frappe.whitelist()
def check_scan(code, transaction_type):
    """Check one scanned code against a movement type before it is added to the list."""
    if transaction_type not in UNIT_TYPES:
        frappe.throw(_("{0} movements do not use scanned units").format(transaction_type))
    name = resolve(code)
    if not name:
        return {"ok": False, "problem": _("No unit with serial {0}").format((code or "").strip()), "unit": None}
    unit = load_unit(name)
    problem = scan_problem(transaction_type, unit)
    return {"ok": problem is None, "problem": problem, "unit": {**unit, "location": location_label(unit)}}


def unit_row(name):
    unit = load_unit(name)
    return {
        "unit_doc_id": unit.name,
        "unit_serial_number": unit.unit_serial_number,
        "unit_name": unit.unit_name,
        "unit_condition": unit.unit_condition,
        "prev_location": unit.unit_location,
        "prev_movement_status": unit.movement_status,
    }


def default_locations(tx, from_location, to_location):
    if tx in ("CHECK_OUT", "MAINTENANCE_OUT", "LOST"):
        return from_location or "Main Warehouse", to_location
    if tx in ("CHECK_IN", "MAINTENANCE_IN"):
        return from_location, "Main Warehouse"
    return from_location, to_location


@frappe.whitelist()
def create_movement(
    transaction_type,
    units=None,
    bulk=None,
    from_location=None,
    to_location=None,
    issued_to=None,
    received_by=None,
    note=None,
):
    """Create a movement. Every unit is re-checked here, so the screen cannot bypass the rules."""
    frappe.has_permission(MOVEMENT, "create", throw=True)
    units = frappe.parse_json(units) or []
    bulk = frappe.parse_json(bulk) or []
    if transaction_type not in TYPES:
        frappe.throw(_("Unknown movement type {0}").format(transaction_type))
    if not units and not bulk:
        frappe.throw(_("Add at least one unit or bulk item"))
    if transaction_type == "CHECK_OUT" and not (to_location or "").strip():
        frappe.throw(_("Say where the equipment is going"))
    names = []
    for code in units:
        name = resolve(code)
        if not name:
            frappe.throw(_("No unit with serial {0}").format(code))
        problem = scan_problem(transaction_type, load_unit(name))
        if problem:
            frappe.throw(_("{0}: {1}").format(code, problem))
        names.append(name)
    if len(set(names)) != len(names):
        frappe.throw(_("A unit appears more than once"))
    source, target = default_locations(transaction_type, from_location, to_location)
    doc = frappe.get_doc(
        {
            "doctype": MOVEMENT,
            "transaction_type": transaction_type,
            "posting_date": frappe.utils.today(),
            "from_location": source,
            "to_location": target,
            "issued_to": issued_to,
            "recieved_by": received_by,
            "text_editor_fdyh": note,
            "rental_item_unit_child_table": [unit_row(name) for name in names],
            "table_qnvp": [
                {"item_template": row["template"], "qty": int(row.get("qty") or 0), "note": row.get("note")} for row in bulk
            ],
        }
    )
    doc.insert()
    return doc.name


@frappe.whitelist()
def list_movements(search=None, transaction_type=None, page=1, page_length=25):
    start, length = paging(page, page_length)
    filters = [["transaction_type", "=", transaction_type]] if transaction_type else []
    or_filters = None
    if search:
        pattern = like(search)
        or_filters = [["name", "like", pattern], ["to_location", "like", pattern], ["from_location", "like", pattern], ["issued_to", "like", pattern]]
    fields = ["name", "transaction_type", "posting_date", "from_location", "to_location", "issued_to", "recieved_by", "creation", "owner"]
    rows = frappe.get_list(MOVEMENT, filters=filters, or_filters=or_filters, fields=fields, order_by="creation desc", limit_start=start, limit_page_length=length)
    total = len(frappe.get_list(MOVEMENT, filters=filters, or_filters=or_filters, pluck="name", limit_page_length=0))
    counts = unit_counts_for([row.name for row in rows])
    return {"rows": [{**row, **counts.get(row.name, {"units": 0, "bulk": 0})} for row in rows], "total": total}


def unit_counts_for(names):
    if not names:
        return {}
    result = {name: {"units": 0, "bulk": 0} for name in names}
    for table, key in (("Rental Item Unit Child Table", "units"), ("Rent Bulk Item Child Table_2", "bulk")):
        for row in frappe.db.sql(
            f"select parent, count(*) as n from `tab{table}` where parent in %(names)s group by parent",
            {"names": names},
            as_dict=True,
        ):
            result[row.parent][key] = row.n
    return result


@frappe.whitelist()
def get_movement(name):
    doc = frappe.get_doc(MOVEMENT, name)
    doc.check_permission("read")
    return {
        "movement": {
            field: doc.get(field)
            for field in ("name", "transaction_type", "posting_date", "from_location", "to_location", "issued_to", "recieved_by", "approved_by", "creation", "owner", "docstatus")
        },
        "note": doc.get("text_editor_fdyh"),
        "units": [row.as_dict() for row in doc.get("rental_item_unit_child_table") or []],
        "bulk": [row.as_dict() for row in doc.get("table_qnvp") or []],
    }
