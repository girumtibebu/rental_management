import frappe
from frappe import _
from frappe.model.document import Document

from rental_management.rental.stock import WAREHOUSE_FIELDS


class RentalWorkspace(Document):
    """One company's rental setup: its four rental warehouses, working mode and quotation hold."""

    def validate(self):
        warehouses = [self.get(field) for field in WAREHOUSE_FIELDS.values()]
        if len(set(warehouses)) != len(warehouses):
            frappe.throw(_("Each rental status needs its own warehouse"))
        for warehouse in warehouses:
            if frappe.db.get_value("Warehouse", warehouse, "company") != self.company:
                frappe.throw(_("{0} does not belong to {1}").format(warehouse, self.company))
            owner = frappe.get_all(
                "Rental Workspace",
                filters={"name": ["!=", self.name]},
                or_filters={field: warehouse for field in WAREHOUSE_FIELDS.values()},
                pluck="name",
                limit=1,
            )
            if owner:
                frappe.throw(_("{0} is already used by workspace {1}").format(warehouse, owner[0]))
        if self.hold_days is not None and self.hold_days < 0:
            frappe.throw(_("Quotation hold cannot be negative"))
        if self.is_default:
            if not self.enabled:
                frappe.throw(_("The default workspace must be enabled"))
            frappe.db.set_value(
                "Rental Workspace", {"is_default": 1, "name": ["!=", self.name]}, "is_default", 0
            )
