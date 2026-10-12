"""Catalog: item templates and how many of each are available."""

import re

import frappe
from frappe import _

from rental_management.api import create_rental_item_units
from rental_management.ui.common import BULK_ITEM, TEMPLATE, UNIT, like, paging

KINDS = ("Unit", "Box", "Bulk")
MAX_UNITS_PER_BATCH = 50


def unit_counts(template_names=None):
    """{template: {total, Warehouse, At Event, In Maintenance, Missing, needs_attention}} in one query."""
    frappe.has_permission(UNIT, "read", throw=True)
    rows = frappe.db.sql(
        """
        select item_template, movement_status, unit_condition, count(*) as total
        from `tabRental Item Unit`
        where disabled = 0 and ifnull(item_template, '') != ''
        group by item_template, movement_status, unit_condition
        """,
        as_dict=True,
    )
    wanted = set(template_names) if template_names is not None else None
    counts = {}
    for row in rows:
        if wanted is not None and row.item_template not in wanted:
            continue
        entry = counts.setdefault(
            row.item_template,
            {"total": 0, "Warehouse": 0, "At Event": 0, "In Maintenance": 0, "Missing": 0, "needs_attention": 0, "available": 0},
        )
        entry["total"] += row.total
        if row.movement_status in entry:
            entry[row.movement_status] += row.total
        if row.unit_condition != "OK":
            entry["needs_attention"] += row.total
        if row.movement_status == "Warehouse" and row.unit_condition == "OK":
            entry["available"] += row.total
    return counts


def describe(template, counts):
    return {
        **template,
        "kind": template.rental_item_type_box,
        "counts": counts.get(template.name) or {"total": 0, "Warehouse": 0, "At Event": 0, "In Maintenance": 0, "Missing": 0, "needs_attention": 0, "available": 0},
    }


TEMPLATE_FIELDS = [
    "name",
    "item_name",
    "item_model",
    "item_category",
    "item_type",
    "item_brand",
    "rental_item_type_box",
    "status",
    "uom",
    "image",
    "sku_naming_series",
    "modified",
]


@frappe.whitelist()
def list_templates(search=None, category=None, kind=None, page=1, page_length=24):
    start, length = paging(page, page_length)
    filters = []
    if category:
        filters.append(["item_category", "=", category])
    if kind:
        filters.append(["rental_item_type_box", "=", kind])
    or_filters = None
    if search:
        pattern = like(search)
        or_filters = [["item_name", "like", pattern], ["item_model", "like", pattern], ["name", "like", pattern]]
    rows = frappe.get_list(
        TEMPLATE,
        filters=filters,
        or_filters=or_filters,
        fields=TEMPLATE_FIELDS,
        order_by="modified desc",
        limit_start=start,
        limit_page_length=length,
    )
    total = len(frappe.get_list(TEMPLATE, filters=filters, or_filters=or_filters, pluck="name", limit_page_length=0))
    counts = unit_counts([row.name for row in rows])
    return {"rows": [describe(row, counts) for row in rows], "total": total}


@frappe.whitelist()
def facets():
    """Option lists for filters and the new-template form."""
    names = lambda doctype: frappe.get_all(doctype, pluck="name", order_by="name asc")  # noqa: E731
    return {
        "categories": names("Rent Item Category"),
        "types": names("Rent Item Type"),
        "brands": names("Rent Item Brand"),
        "kinds": list(KINDS),
        "conditions": names("Rental Item Condition"),
    }


@frappe.whitelist()
def get_template(name):
    doc = frappe.get_doc(TEMPLATE, name)
    doc.check_permission("read")
    data = {field: doc.get(field) for field in TEMPLATE_FIELDS + ["item_model_long", "suffix", "total_quantity", "available_quantity"]}
    kind = doc.rental_item_type_box
    bulk = frappe.get_all(
        BULK_ITEM,
        filters={"bulk_item_link": name},
        fields=["name", "name1", "uom", "size", "bulk_type", "quantity", "total_availability", "status"],
    )
    return {
        "template": describe(frappe._dict(data), unit_counts([name])),
        "bulk": bulk,
        "can": {
            "write": bool(frappe.has_permission(TEMPLATE, "write", doc=doc)),
            "generate": doc.status == "Completed" and kind != "Bulk" and bool(frappe.has_permission(UNIT, "create")),
            "activate": doc.status == "Draft" and bool(frappe.has_permission(TEMPLATE, "write", doc=doc)),
        },
    }


def code(value):
    return re.sub(r"[^a-zA-Z0-9]", "", value or "").upper()


def sku_series(kind, model, brand, item_type, suffix):
    """The serial pattern the Desk form builds, e.g. LEDWALL-RO-LE-###."""
    if kind == "Bulk" or not suffix:
        return "NONE"
    prefix = code(model) if kind == "Box" else f"{code(model)}-{code(brand)[:2]}-{code(item_type)[:2]}"
    return f"{prefix}-{'#' * int(suffix)}"


@frappe.whitelist()
def create_template(item_model, item_category, item_type, item_brand, rental_item_type_box, uom=None, suffix="3", size=None, activate=1):
    """Create an item template the same way the Desk form does (name and serial pattern included)."""
    if rental_item_type_box not in KINDS:
        frappe.throw(_("Choose Unit, Box or Bulk"))
    if str(suffix or "3") not in ("1", "2", "3", "4"):
        frappe.throw(_("The serial digits must be 1 to 4"))
    model = (item_model or "").strip()
    if not model:
        frappe.throw(_("A model name is required"))
    doc = frappe.get_doc(
        {
            "doctype": TEMPLATE,
            "item_model": model,
            "item_model_long": model,
            "item_category": item_category,
            "item_type": item_type,
            "item_brand": item_brand,
            "item_name": " ".join(part for part in (model, item_brand, item_type) if part),
            "rental_item_type_box": rental_item_type_box,
            "uom": uom or None,
            "size": size,
            "suffix": suffix or "3",
            "sku_naming_series": sku_series(rental_item_type_box, model, item_brand, item_type, suffix),
            "status": "Draft",
        }
    )
    doc.insert()
    if int(activate or 0):
        doc.status = "Completed"
        doc.save()
    return doc.name


@frappe.whitelist()
def activate_template(name):
    doc = frappe.get_doc(TEMPLATE, name)
    doc.check_permission("write")
    doc.status = "Completed"
    doc.save()
    return get_template(name)


@frappe.whitelist()
def generate_units(template, count=1):
    """Create serial-numbered units for a template (existing numbering rules apply)."""
    count = int(count)
    if not 1 <= count <= MAX_UNITS_PER_BATCH:
        frappe.throw(_("Create between 1 and {0} units at a time").format(MAX_UNITS_PER_BATCH))
    doc = frappe.get_doc(TEMPLATE, template)
    doc.check_permission("write")
    if doc.status != "Completed":
        frappe.throw(_("Activate the template before creating units"))
    if doc.rental_item_type_box == "Bulk":
        frappe.throw(_("Bulk items are counted, not serialised"))
    return create_rental_item_units(template, count)
