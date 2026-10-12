"""Units: the physical, serial-numbered equipment."""

import frappe
from frappe import _

from rental_management.ui.common import (
    MAINTENANCE,
    UNIT,
    UNIT_LOG,
    like,
    location_label,
    paging,
    storage_path,
    template_index,
)

LIST_FIELDS = [
    "name",
    "unit_serial_number",
    "unit_name",
    "item_template",
    "movement_status",
    "unit_location",
    "unit_condition",
    "maintenance_status",
    "unit_type",
    "parent_box",
    "zone",
    "section",
    "level",
    "position",
    "modified",
]


def describe(unit, templates):
    template = templates.get(unit.item_template) or {}
    return {
        **unit,
        "location": location_label(unit),
        "storage": storage_path(unit),
        "category": template.get("item_category"),
        "kind": template.get("rental_item_type_box") or unit.get("unit_type"),
        "image": template.get("image"),
    }


def build_filters(status, condition, template, unit_type, location, boxed):
    filters = [["disabled", "=", 0]]
    for field, value in (
        ("movement_status", status),
        ("unit_condition", condition),
        ("item_template", template),
        ("unit_type", unit_type),
    ):
        if value:
            filters.append([field, "=", value])
    if location:
        filters.append(["unit_location", "like", like(location)])
    if boxed == "boxed":
        filters.append(["parent_box", "not in", ["", "None"]])
    return filters


def categories_to_templates(category):
    return frappe.get_all("Rental Item Template", {"item_category": category}, pluck="name")


@frappe.whitelist()
def list_units(
    search=None,
    status=None,
    condition=None,
    template=None,
    category=None,
    unit_type=None,
    location=None,
    boxed=None,
    page=1,
    page_length=25,
):
    start, length = paging(page, page_length)
    filters = build_filters(status, condition, template, unit_type, location, boxed)
    if category:
        filters.append(["item_template", "in", categories_to_templates(category) or ["-"]])
    or_filters = None
    if search:
        pattern = like(search)
        or_filters = [
            ["unit_serial_number", "like", pattern],
            ["unit_name", "like", pattern],
            ["name", "like", pattern],
            ["unit_location", "like", pattern],
        ]
    rows = frappe.get_list(
        UNIT,
        filters=filters,
        or_filters=or_filters,
        fields=LIST_FIELDS,
        order_by="modified desc",
        limit_start=start,
        limit_page_length=length,
    )
    total = len(frappe.get_list(UNIT, filters=filters, or_filters=or_filters, pluck="name", limit_page_length=0))
    templates = template_index([row.item_template for row in rows])
    return {"rows": [describe(row, templates) for row in rows], "total": total}


def resolve(code):
    """The unit document name for a scanned serial number or document name."""
    code = (code or "").strip()
    if not code:
        return None
    return frappe.db.get_value(UNIT, {"unit_serial_number": code}, "name") or (
        code if frappe.db.exists(UNIT, code) else None
    )


@frappe.whitelist()
def find_unit(code):
    """Look a scanned code up; returns None (not an error) when nothing matches."""
    name = resolve(code)
    if not name:
        return None
    frappe.has_permission(UNIT, "read", doc=name, throw=True)
    unit = frappe.db.get_value(UNIT, name, LIST_FIELDS, as_dict=True)
    return describe(unit, template_index([unit.item_template]))


def box_contents(name):
    rows = frappe.get_all(
        "Box Item Unit Child Table",
        filters={"parent": name, "parenttype": UNIT},
        fields=["document_id", "unit_serial_number", "unit_name", "unit_condition", "movement_status"],
        order_by="idx asc",
    )
    return [row for row in rows if row.document_id]


def movement_events(name):
    """Every movement this unit took part in (from the movement rows, which are always written)."""
    rows = frappe.db.sql(
        """
        select m.name, m.transaction_type, m.from_location, m.to_location, m.creation, m.owner
        from `tabRental Item Unit Child Table` c
        join `tabRental Movement` m on m.name = c.parent
        where c.unit_doc_id = %s
        order by m.creation desc
        limit 60
        """,
        name,
        as_dict=True,
    )
    return [
        {
            "name": row.name,
            "kind": "Movement",
            "reference_doctype": "Rental Movement",
            "reference_name": row.name,
            "status": row.transaction_type,
            "from_location": row.from_location,
            "to_location": row.to_location,
            "when": str(row.creation),
            "owner": row.owner,
        }
        for row in rows
    ]


def history(name):
    """Movements and maintenance for a unit, newest first."""
    events = movement_events(name)
    seen = {event["reference_name"] for event in events}
    for log in frappe.get_all(
        UNIT_LOG,
        filters={"unit": name},
        fields=["name", "event_type", "reference_doctype", "reference_name", "from_location", "to_location", "status", "date"],
        order_by="date desc",
        limit=60,
    ):
        if log.reference_name not in seen:
            events.append({**log, "when": str(log.date), "kind": log.event_type})
    for ticket in frappe.get_all(
        MAINTENANCE,
        filters={"unit_serial_number": name},
        fields=["name", "workflow_state", "unit_condition", "final_condition", "issue_description", "creation", "owner"],
        order_by="creation desc",
        limit=30,
    ):
        events.append(
            {
                "name": ticket.name,
                "kind": "Maintenance ticket",
                "reference_doctype": MAINTENANCE,
                "reference_name": ticket.name,
                "status": ticket.workflow_state,
                "detail": ticket.issue_description,
                "when": str(ticket.creation),
                "owner": ticket.owner,
            }
        )
    events.sort(key=lambda event: event["when"], reverse=True)
    return events[:80]


@frappe.whitelist()
def get_unit(name):
    doc = frappe.get_doc(UNIT, name)
    doc.check_permission("read")
    unit = doc.as_dict(no_default_fields=False)
    template = template_index([doc.item_template]).get(doc.item_template) or {}
    open_ticket = frappe.db.get_value(
        MAINTENANCE,
        {"unit_serial_number": name, "docstatus": ["<", 2], "workflow_state": ["!=", "Complete"]},
        ["name", "workflow_state"],
        as_dict=True,
    )
    parent = doc.parent_box if doc.parent_box and str(doc.parent_box).lower() != "none" else None
    return {
        "unit": {k: unit.get(k) for k in LIST_FIELDS + ["creation", "owner", "image", "unit_model", "unit_brand"]},
        "location": location_label(unit),
        "storage": storage_path(unit),
        "template": template,
        "parent_box": parent,
        "contents": box_contents(name) if doc.unit_type == "Box" else [],
        "open_ticket": open_ticket,
        "history": history(name),
        "can": {
            "write": bool(frappe.has_permission(UNIT, "write", doc=doc)),
            "move": bool(frappe.has_permission("Rental Movement", "create")),
            "maintain": bool(frappe.has_permission(MAINTENANCE, "create")),
        },
    }


@frappe.whitelist()
def update_storage(name, zone=None, section=None, level=None, position=None):
    """Set where a stocked unit lives in the warehouse."""
    doc = frappe.get_doc(UNIT, name)
    doc.check_permission("write")
    if doc.movement_status != "Warehouse":
        frappe.throw(_("Only units in the warehouse can be given a storage address"))
    doc.zone, doc.section, doc.level, doc.position = zone or None, section or None, level or None, position or None
    doc.save()
    return get_unit(name)
