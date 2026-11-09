"""The rental workspaces a user can switch between, and who may open which."""

import frappe
from frappe import _

from rental_management.rental.stock import WORKSPACE

# These roles can open every workspace, so managers can switch between companies.
MANAGER_ROLES = {"System Manager", "Stock Manager"}
FIELDS = ["name", "company", "mode", "hold_days", "is_default", "item_group"]


def allowed_workspaces(user=None):
    """Enabled workspaces this user may work in, default first.

    A workspace with no users listed is open to every rental user; one with
    users listed is open to those users only. Managers see them all.
    """
    user = user or frappe.session.user
    rows = frappe.get_all(WORKSPACE, filters={"enabled": 1}, fields=FIELDS, order_by="is_default desc, name asc")
    if user == "Administrator" or MANAGER_ROLES & set(frappe.get_roles(user)):
        return rows
    members = {}
    for link in frappe.get_all(
        "Rental Workspace User", filters={"parenttype": WORKSPACE}, fields=["parent", "user"]
    ):
        members.setdefault(link.parent, set()).add(link.user)
    return [row for row in rows if row.name not in members or user in members[row.name]]


def resolve_workspace(name=None, user=None):
    """The workspace to use for this user: the one asked for if allowed, else their first one."""
    allowed = [row.name for row in allowed_workspaces(user)]
    if name:
        if name not in allowed:
            frappe.throw(_("You cannot work in rental workspace {0}").format(name), frappe.PermissionError)
        return name
    if not allowed:
        frappe.throw(_("You have not been given a rental workspace"), frappe.PermissionError)
    return allowed[0]


@frappe.whitelist()
def list_workspaces():
    """The workspaces this user can switch between, default first."""
    return allowed_workspaces()
