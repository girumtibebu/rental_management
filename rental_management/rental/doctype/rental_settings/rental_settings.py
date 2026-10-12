import frappe
from frappe import _
from frappe.model.document import Document

from rental_management.rental.stock import WAREHOUSE_FIELDS


class RentalSettings(Document):
    def validate(self):
        warehouses = [self.get(field) for field in WAREHOUSE_FIELDS.values()]
        if len(set(warehouses)) != len(warehouses):
            frappe.throw(_("Each rental status needs its own warehouse"))
        for warehouse in warehouses:
            if frappe.db.get_value("Warehouse", warehouse, "company") != self.company:
                frappe.throw(_("{0} does not belong to {1}").format(warehouse, self.company))
