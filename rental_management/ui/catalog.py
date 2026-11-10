"""Catalog: rental items on the native Item master, and how many of each are available."""

import frappe
from frappe import _
from frappe.model.naming import make_autoname
from frappe.utils import cint, flt

from rental_management.rental.item import get_serial_prefix
from rental_management.rental.setup.install import RENTAL_ITEM_GROUP
from rental_management.rental.stock import (
    STATUSES,
    get_bulk_quantities,
    get_cost_center,
    get_item_scope,
    get_place,
    get_settings,
    get_warehouse_statuses,
    post_movement,
)
from rental_management.ui.common import CONDITIONS, ITEM_FIELDS, describe_item, get_tracking, like, paging

KINDS = ("Unit", "Box", "Bulk")
MAX_UNITS_PER_BATCH = 50


def empty_counts():
    return {"total": 0, **dict.fromkeys(STATUSES, 0), "needs_attention": 0, "available": 0}


def serial_counts(item_codes):
    """{item_code: counts} for serialised items, in one query."""
    if not item_codes:
        return {}
    statuses = get_warehouse_statuses()
    rows = frappe.db.sql(
        """
        select item_code, warehouse, rental_condition, count(*) as total
        from `tabSerial No`
        where item_code in %(items)s and warehouse in %(warehouses)s
        group by item_code, warehouse, rental_condition
        """,
        {"items": list(item_codes), "warehouses": list(statuses)},
        as_dict=True,
    )
    counts = {}
    for row in rows:
        entry = counts.setdefault(row.item_code, empty_counts())
        status = statuses[row.warehouse]
        entry["total"] += row.total
        entry[status] += row.total
        if row.rental_condition != "OK":
            entry["needs_attention"] += row.total
        if status == "Warehouse" and row.rental_condition == "OK":
            entry["available"] += row.total
    return counts


def bulk_counts(item_codes):
    counts = {}
    for item_code, quantities in get_bulk_quantities(item_codes).items():
        counts[item_code] = {
            **empty_counts(),
            **quantities,
            "total": sum(quantities.values()),
            "available": quantities["Warehouse"],
        }
    return counts


def get_counts(items):
    serialised = [item.name for item in items if get_tracking(item) != "Bulk"]
    bulk = [item.name for item in items if get_tracking(item) == "Bulk"]
    return {**serial_counts(serialised), **bulk_counts(bulk)}


def with_counts(items):
    counts = get_counts(items)
    return [{**describe_item(item), "counts": counts.get(item.name) or empty_counts()} for item in items]


@frappe.whitelist()
def list_items(search=None, category=None, kind=None, page=1, page_length=24):
    start, length = paging(page, page_length)
    filters = {**get_item_scope(), "disabled": 0}
    if category:
        filters["item_group"] = category
    if kind:
        filters["rental_tracking"] = kind
    or_filters = None
    if search:
        pattern = like(search)
        or_filters = [["item_name", "like", pattern], ["rental_model", "like", pattern], ["name", "like", pattern]]
    rows = frappe.get_list(
        "Item",
        filters=filters,
        or_filters=or_filters,
        fields=ITEM_FIELDS,
        order_by="modified desc",
        limit_start=start,
        limit_page_length=length,
    )
    total = len(frappe.get_list("Item", filters=filters, or_filters=or_filters, pluck="name", limit_page_length=0))
    return {"rows": with_counts(rows), "total": total}


def get_categories():
    root = get_settings().get("item_group")
    if root:
        groups = frappe.get_all(
            "Item Group", filters={"name": ["descendants of (inclusive)", root], "is_group": 0}, pluck="name", order_by="name asc"
        )
        # Leave out groups that only hold services (decor design and the like).
        stocked = set(frappe.get_all("Item", filters={"item_group": ["in", groups], "is_stock_item": 1, "disabled": 0}, pluck="item_group"))
        unstocked = set(frappe.get_all("Item", filters={"item_group": ["in", groups], "disabled": 0}, pluck="item_group")) - stocked
        return [group for group in groups if group not in unstocked]
    return frappe.get_all("Item Group", filters={"parent_item_group": RENTAL_ITEM_GROUP}, pluck="name", order_by="name asc")


@frappe.whitelist()
def facets():
    """Option lists for filters and the new-item form."""
    return {
        "categories": get_categories(),
        "types": frappe.get_all("Rent Item Type", pluck="name", order_by="name asc"),
        "brands": frappe.get_all("Brand", pluck="name", order_by="name asc"),
        "kinds": list(KINDS),
        "conditions": list(CONDITIONS),
    }


@frappe.whitelist()
def get_item(name):
    doc = frappe.get_doc("Item", name)
    doc.check_permission("read")
    if not frappe.db.exists("Item", {"name": name, **get_item_scope()}):
        frappe.throw(_("{0} is not in this workspace").format(name))
    item = with_counts([frappe._dict({field: doc.get(field) for field in ITEM_FIELDS})])[0]
    can_stock = bool(frappe.has_permission("Stock Entry", "submit"))
    return {
        "item": item,
        "stock": [
            {"status": status, "place": get_place(status), "qty": item["counts"][status]} for status in STATUSES
        ],
        "can": {
            "write": bool(frappe.has_permission("Item", "write", doc=doc)),
            "generate": get_tracking(item) != "Bulk" and can_stock and bool(frappe.has_permission("Serial No", "create")),
            "receive": get_tracking(item) == "Bulk" and can_stock,
        },
    }


def get_item_code(kind, model, brand, item_type):
    """Unit items use the serial prefix (MODEL-BR-TY); boxes and bulk items use the model code."""
    item_code = get_serial_prefix(model, brand, item_type, "Unit" if kind == "Unit" else "Box")
    if not item_code:
        frappe.throw(_("A model name is required"))
    return item_code


@frappe.whitelist()
def create_item(rental_model, item_group, rental_item_type, brand, rental_tracking, stock_uom=None, rental_serial_digits="3", rental_size=None):
    """Create a rental Item. Its code is the serial prefix, so labels and item codes read the same."""
    if rental_tracking not in KINDS:
        frappe.throw(_("Choose Unit, Box or Bulk"))
    if str(rental_serial_digits or "3") not in ("1", "2", "3", "4"):
        frappe.throw(_("The serial digits must be 1 to 4"))
    model = (rental_model or "").strip()
    item_code = get_item_code(rental_tracking, model, brand, rental_item_type)
    if frappe.db.exists("Item", item_code):
        frappe.throw(_("A rental item {0} already exists").format(frappe.bold(item_code)))
    doc = frappe.get_doc(
        {
            "doctype": "Item",
            "item_code": item_code,
            "item_name": " ".join(part for part in (model, brand, rental_item_type) if part),
            "item_group": item_group,
            "brand": brand,
            "stock_uom": stock_uom or "Nos",
            "is_rental_item": 1,
            "rental_tracking": rental_tracking,
            "rental_model": model,
            "rental_item_type": rental_item_type,
            "rental_serial_digits": str(rental_serial_digits or "3"),
            "rental_size": rental_size,
            "item_defaults": [item_defaults(get_settings())],
        }
    )
    doc.insert()
    return doc.name


def next_serials(series, count):
    """`count` new serial numbers from the item's series, skipping any already in use."""
    serials = []
    while len(serials) < count:
        name = make_autoname(series, "Serial No")
        if not frappe.db.exists("Serial No", name):
            serials.append(name)
    return serials


@frappe.whitelist()
def generate_units(item_code, count=1):
    """Create serial numbers for an item and receive them into the rental store."""
    count = cint(count)
    if not 1 <= count <= MAX_UNITS_PER_BATCH:
        frappe.throw(_("Create between 1 and {0} units at a time").format(MAX_UNITS_PER_BATCH))
    item = frappe.get_doc("Item", item_code)
    item.check_permission("read")
    if get_tracking(item) == "Bulk" or not item.has_serial_no:
        frappe.throw(_("Bulk items are counted, not serialised"))
    frappe.has_permission("Serial No", "create", throw=True)
    serials = next_serials(item.serial_no_series, count)
    for name in serials:
        frappe.get_doc({"doctype": "Serial No", "serial_no": name, "item_code": item_code}).insert()
    movement = post_movement("PURCHASE", serials=serials, remarks=_("New rental units"))
    return {"units_created": serials, "movement": movement}


@frappe.whitelist()
def receive_stock(item_code, qty):
    """Add bulk quantity to the rental store."""
    item = frappe.db.get_value("Item", item_code, ["rental_tracking", "has_serial_no"], as_dict=True)
    if not item or get_tracking(item) != "Bulk":
        frappe.throw(_("Only bulk items are received by quantity"))
    if flt(qty) <= 0:
        frappe.throw(_("Enter a quantity above zero"))
    return post_movement("PURCHASE", bulk=[(item_code, flt(qty))], remarks=_("Bulk stock received"))


def item_defaults(workspace):
    """The Item Default row that files an item under the workspace's company, store and cost center."""
    cost_center = get_cost_center(workspace.name)
    return {
        "company": workspace.company,
        "default_warehouse": workspace.store_warehouse,
        "buying_cost_center": cost_center,
        "selling_cost_center": cost_center,
    }


@frappe.whitelist()
def create_decor_item(item_name, item_group, stock_uom=None, image=None):
    """Add a plain counted item (a chair, a vase) to this workspace, under its company and cost center."""
    workspace = get_settings()
    name = (item_name or "").strip()
    if not name:
        frappe.throw(_("Give the item a name"))
    # Any category under the workspace's group is fine, including one that holds only services so far.
    scope = (
        frappe.get_all("Item Group", filters={"name": ["descendants of (inclusive)", workspace.item_group], "is_group": 0}, pluck="name")
        if workspace.item_group
        else []
    )
    if scope and item_group not in scope:
        frappe.throw(_("Choose a category under {0}").format(workspace.item_group))
    doc = frappe.get_doc(
        {
            "doctype": "Item",
            "item_name": name,
            "item_group": item_group,
            "stock_uom": stock_uom or "Nos",
            "is_stock_item": 1,
            "is_sales_item": 1,
            "has_serial_no": 0,
            "is_rental_item": 1,
            "rental_tracking": "Bulk",
            "image": image,
            "item_defaults": [item_defaults(workspace)],
        }
    )
    if workspace.item_code_series:
        doc.item_code = make_autoname(workspace.item_code_series, "Item")
    else:
        doc.item_code = name
    doc.insert()
    return doc.name


@frappe.whitelist()
def apply_workspace_defaults(workspace=None):
    """Give every item in the workspace's item group its company, store and cost center, and the groups too.

    Existing rows for other companies are kept. Items that already have a row for this company are left alone.
    """
    frappe.only_for(("System Manager", "Stock Manager"))
    workspace = get_settings(workspace)
    if not workspace.item_group:
        frappe.throw(_("Set an Item Group on the workspace first"))
    row = item_defaults(workspace)
    updated = {"items": 0, "groups": 0}
    for group in frappe.get_all("Item Group", filters={"name": ["descendants of (inclusive)", workspace.item_group]}, pluck="name"):
        doc = frappe.get_doc("Item Group", group)
        if not any(entry.company == workspace.company for entry in doc.get("item_group_defaults")):
            doc.append("item_group_defaults", row)
            doc.save()
            updated["groups"] += 1
    for name in frappe.get_all("Item", filters=get_item_scope(workspace.name), pluck="name"):
        doc = frappe.get_doc("Item", name)
        if not any(entry.company == workspace.company for entry in doc.get("item_defaults")):
            doc.append("item_defaults", row)
            doc.save()
            updated["items"] += 1
    return updated
