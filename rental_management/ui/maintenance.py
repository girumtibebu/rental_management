"""Maintenance: a board of repair tickets that follows the existing workflow."""

import frappe
from frappe import _
from frappe.model.workflow import apply_workflow, get_transitions

from rental_management.ui.common import MAINTENANCE
from rental_management.ui.units import history, load_unit, open_ticket, resolve

STATES = ("Attention Required", "In Repair", "Complete")
TICKET_FIELDS = [
    "name",
    "serial_no",
    "item_name",
    "workflow_state",
    "unit_condition",
    "final_condition",
    "issue_description",
    "maintenance_result",
    "maintained_by",
    "docstatus",
    "creation",
    "modified",
    "owner",
]
FINAL_CONDITIONS = ("OK", "Scrapped")
OPEN_CONDITIONS = ("Damaged", "Need Cleaning")
RECENT_COMPLETE = 20


@frappe.whitelist()
def board():
    """Tickets grouped by workflow state; finished work shows the most recent few."""
    columns = {}
    for state in STATES:
        limit = RECENT_COMPLETE if state == "Complete" else 200
        columns[state] = frappe.get_list(
            MAINTENANCE,
            filters={"workflow_state": state, "docstatus": ["<", 2]},
            fields=TICKET_FIELDS,
            order_by="modified desc",
            limit_page_length=limit,
        )
    return {
        "states": list(STATES),
        "columns": columns,
        "can": {"create": bool(frappe.has_permission(MAINTENANCE, "create"))},
    }


@frappe.whitelist()
def create_ticket(code, unit_condition, issue_description=None):
    """Flag a unit for maintenance. The ticket sets the unit's condition."""
    name = resolve(code)
    if not name:
        frappe.throw(_("No unit with serial {0}").format((code or "").strip()))
    if unit_condition not in OPEN_CONDITIONS:
        frappe.throw(_("Choose Damaged or Need Cleaning"))
    existing = open_ticket(name)
    if existing:
        frappe.throw(_("{0} already has an open ticket: {1}").format(code, existing.name))
    doc = frappe.get_doc(
        {
            "doctype": MAINTENANCE,
            "serial_no": name,
            "unit_condition": unit_condition,
            "issue_description": issue_description,
        }
    )
    doc.insert()
    return doc.name


@frappe.whitelist()
def get_ticket(name):
    doc = frappe.get_doc(MAINTENANCE, name)
    doc.check_permission("read")
    return {
        "ticket": {field: doc.get(field) for field in TICKET_FIELDS},
        "unit": load_unit(doc.serial_no),
        "history": history(doc.serial_no),
        "actions": [transition.action for transition in get_transitions(doc)],
        "can": {"write": bool(frappe.has_permission(MAINTENANCE, "write", doc=doc))},
    }


@frappe.whitelist()
def start_repair(name):
    doc = frappe.get_doc(MAINTENANCE, name)
    if doc.workflow_state != "Attention Required":
        frappe.throw(_("Only tickets that need attention can be sent to repair"))
    apply_workflow(doc, "Send To Maintenance")
    return get_ticket(name)


@frappe.whitelist()
def complete(name, final_condition="OK", maintenance_result=None, maintained_by=None):
    doc = frappe.get_doc(MAINTENANCE, name)
    if doc.workflow_state != "In Repair":
        frappe.throw(_("Start the repair before completing it"))
    if final_condition not in FINAL_CONDITIONS:
        frappe.throw(_("The final condition must be OK or Scrapped"))
    doc.final_condition = final_condition
    doc.maintenance_result = maintenance_result
    doc.maintained_by = maintained_by or frappe.session.user
    doc.save()
    apply_workflow(frappe.get_doc(MAINTENANCE, name), "Complete")
    return get_ticket(name)
