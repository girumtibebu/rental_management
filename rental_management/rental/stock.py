"""Rental stock on native ERPNext stock.

A serial's warehouse is the single source of truth for where it is. Every
movement is a submitted Stock Entry, so the stock ledger is the history.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt

SETTINGS = "Rental Settings"
NOT_IN_STOCK = "Not In Stock"

WAREHOUSE_FIELDS = {
    "Warehouse": "store_warehouse",
    "At Event": "event_warehouse",
    "In Maintenance": "repair_warehouse",
    "Missing": "missing_warehouse",
}
STATUSES = tuple(WAREHOUSE_FIELDS)

TARGET_STATUS = {
    "CHECK_OUT": "At Event",
    "CHECK_IN": "Warehouse",
    "MAINTENANCE_OUT": "In Maintenance",
    "MAINTENANCE_IN": "Warehouse",
    "LOST": "Missing",
    "PURCHASE": "Warehouse",
    "DISPOSE": None,
}
MOVEMENT_TYPES = tuple(TARGET_STATUS)
BULK_SOURCE_STATUS = {"CHECK_OUT": "Warehouse", "CHECK_IN": "At Event", "DISPOSE": "Warehouse"}

PLACE_LABELS = {"Warehouse": "Warehouse", "At Event": "At event", "In Maintenance": "Repair Shop", "Missing": "Missing"}


def get_settings():
    settings = frappe.get_cached_doc(SETTINGS)
    missing = [field for field in ("company", *WAREHOUSE_FIELDS.values()) if not settings.get(field)]
    if missing:
        frappe.throw(_("Complete Rental Settings first: {0} is not set").format(", ".join(missing)))
    return settings


def get_warehouse(status):
    return get_settings().get(WAREHOUSE_FIELDS[status])


def get_warehouse_statuses():
    """{warehouse: rental status} for the four rental warehouses."""
    settings = get_settings()
    return {settings.get(field): status for status, field in WAREHOUSE_FIELDS.items()}


def get_status(warehouse):
    return get_warehouse_statuses().get(warehouse) or NOT_IN_STOCK


def get_venues(serials):
    """{serial: venue} from the Stock Entry that moved each serial into its current warehouse."""
    serials = list({serial for serial in serials if serial})
    if not serials:
        return {}
    rows = frappe.db.sql(
        """
        select entry.serial_no, stock_entry.rental_venue
        from `tabSerial and Batch Entry` entry
        join `tabSerial and Batch Bundle` bundle on bundle.name = entry.parent
        join `tabSerial No` serial on serial.name = entry.serial_no and serial.warehouse = bundle.warehouse
        join `tabStock Entry` stock_entry on stock_entry.name = bundle.voucher_no
        where entry.serial_no in %(serials)s
            and bundle.docstatus = 1 and bundle.is_cancelled = 0
            and bundle.voucher_type = 'Stock Entry' and bundle.type_of_transaction = 'Inward'
        order by stock_entry.posting_date desc, stock_entry.posting_time desc, stock_entry.name desc
        """,
        {"serials": serials},
        as_dict=True,
    )
    venues = {}
    for row in rows:
        venues.setdefault(row.serial_no, row.rental_venue)
    return venues


def get_place(status, venue=None):
    """A readable place: the venue for equipment that is out, the warehouse status otherwise."""
    if status in ("At Event", "In Maintenance") and venue:
        return venue
    return PLACE_LABELS.get(status, "")


def get_bulk_quantities(item_codes=None):
    """{item_code: {status: qty}} from the bins of the rental warehouses."""
    statuses = get_warehouse_statuses()
    filters = {"warehouse": ["in", list(statuses)], "actual_qty": ["!=", 0]}
    if item_codes is not None:
        if not item_codes:
            return {}
        filters["item_code"] = ["in", list(item_codes)]
    quantities = {}
    for bin_row in frappe.get_all("Bin", filters=filters, fields=["item_code", "warehouse", "actual_qty"]):
        entry = quantities.setdefault(bin_row.item_code, dict.fromkeys(STATUSES, 0))
        entry[statuses[bin_row.warehouse]] += flt(bin_row.actual_qty)
    return quantities


def get_purpose(movement_type):
    return {"PURCHASE": "Material Receipt", "DISPOSE": "Material Issue"}.get(movement_type, "Material Transfer")


def build_serial_rows(movement_type, serials):
    """One Stock Entry row per item and source warehouse, carrying its serial numbers."""
    target = TARGET_STATUS[movement_type]
    groups = {}
    for serial in frappe.get_all("Serial No", filters={"name": ["in", serials]}, fields=["name", "item_code", "warehouse"]):
        source = None if movement_type == "PURCHASE" else serial.warehouse
        groups.setdefault((serial.item_code, source), []).append(serial.name)
    rows = []
    for (item_code, source), names in groups.items():
        rows.append(
            {
                "item_code": item_code,
                "qty": len(names),
                "s_warehouse": source,
                "t_warehouse": get_warehouse(target) if target else None,
                "use_serial_batch_fields": 1,
                "serial_no": "\n".join(sorted(names)),
                "allow_zero_valuation_rate": 1,
            }
        )
    return rows


def build_bulk_rows(movement_type, bulk):
    source_status = BULK_SOURCE_STATUS.get(movement_type)
    target = TARGET_STATUS[movement_type]
    if movement_type != "PURCHASE" and not source_status:
        frappe.throw(_("{0} movements cannot carry bulk items").format(movement_type))
    source = get_warehouse(source_status) if source_status else None
    on_hand = get_bulk_quantities([item_code for item_code, _qty in bulk])
    rows = []
    for item_code, qty in bulk:
        if source_status and flt(qty) > on_hand.get(item_code, {}).get(source_status, 0):
            frappe.throw(
                _("Only {0} of {1} are {2}").format(
                    flt(on_hand.get(item_code, {}).get(source_status, 0)), item_code, PLACE_LABELS[source_status].lower()
                )
            )
        rows.append(
            {
                "item_code": item_code,
                "qty": flt(qty),
                "s_warehouse": source,
                "t_warehouse": get_warehouse(target) if target else None,
                "allow_zero_valuation_rate": 1,
            }
        )
    return rows


def post_movement(movement_type, serials=(), bulk=(), venue=None, issued_to=None, received_by=None, remarks=None, posting_datetime=None):
    """Submit one Stock Entry for a rental movement and return its name."""
    if movement_type not in MOVEMENT_TYPES:
        frappe.throw(_("Unknown movement type {0}").format(movement_type))
    rows = build_serial_rows(movement_type, list(serials)) if serials else []
    rows += build_bulk_rows(movement_type, list(bulk)) if bulk else []
    if not rows:
        frappe.throw(_("Add at least one unit or bulk item"))
    purpose = get_purpose(movement_type)
    stock_entry = frappe.get_doc(
        {
            "doctype": "Stock Entry",
            "company": get_settings().company,
            "stock_entry_type": purpose,
            "purpose": purpose,
            "rental_movement_type": movement_type,
            "rental_venue": venue,
            "rental_issued_to": issued_to,
            "rental_received_by": received_by,
            "remarks": remarks,
            "items": rows,
        }
    )
    if posting_datetime:
        stock_entry.set_posting_time = 1
        stock_entry.posting_date, stock_entry.posting_time = str(posting_datetime).split(" ")
    stock_entry.insert()
    stock_entry.submit()
    return stock_entry.name


def set_series_counter(prefix, value):
    """Move a naming series forward so new serials continue after existing ones."""
    current = frappe.db.sql("select current from `tabSeries` where name = %s", prefix)
    if not current:
        frappe.db.sql("insert into `tabSeries` (name, current) values (%s, %s)", (prefix, value))
    elif cint(current[0][0]) < value:
        frappe.db.sql("update `tabSeries` set current = %s where name = %s", (value, prefix))
