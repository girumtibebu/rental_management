"""The rental workspaces a user can switch between."""

import frappe

from rental_management.rental.stock import WORKSPACE


@frappe.whitelist()
def list_workspaces():
    """Enabled workspaces, default first, for the switcher."""
    return frappe.get_list(
        WORKSPACE,
        filters={"enabled": 1},
        fields=["name", "company", "mode", "hold_days", "is_default"],
        order_by="is_default desc, name asc",
    )
