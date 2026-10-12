import frappe
from frappe import _

no_cache = 1


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw(_("Please log in to open Rental Management"), frappe.PermissionError)
    if not frappe.has_permission("Rental Item Unit", "read"):
        frappe.throw(_("You do not have access to Rental Management"), frappe.PermissionError)
    frappe.db.commit()
    context.boot = frappe._dict(
        {
            "csrf_token": frappe.sessions.get_csrf_token(),
            "site_name": frappe.local.site,
            "user": frappe.session.user,
            "user_fullname": frappe.utils.get_fullname(),
        }
    )
    return context
