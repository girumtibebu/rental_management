import frappe
from frappe import _
from frappe.model.document import Document

from rental_management.rental.item import set_condition


class RentalItemMaintenance(Document):
    """A repair ticket for one serial. The ticket owns the serial's condition while it is open."""

    def after_insert(self):
        if self.unit_condition:
            set_condition(self.serial_no, self.unit_condition)

    def before_submit(self):
        if not self.final_condition:
            frappe.throw(_("Choose the final condition before completing the repair"))

    def on_submit(self):
        set_condition(self.serial_no, self.final_condition)
