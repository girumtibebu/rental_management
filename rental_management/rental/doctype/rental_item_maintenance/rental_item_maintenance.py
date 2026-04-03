import frappe
from frappe.model.document import Document
from frappe import _

class RentalItemMaintenance(Document):
    def _resolve_final_condition(self):
        # If maintenance is completed and no final condition is provided,
        # default to OK to keep unit condition in sync with completion.
        return self.final_condition or "OK"

    def before_insert(self):
        # Server Script: Rental Item Maintenance (Before Insert)
        if self.unit_serial_number:
            unit = frappe.get_doc("Rental Item Unit", self.unit_serial_number)
            final_to_unit_map = {
                "OK": "Need Cleaning",
                "Scrapped": "Damaged"
            }
            if self.final_condition:
                mapped_condition = final_to_unit_map.get(self.final_condition)
                if mapped_condition:
                    unit.db_set("unit_condition", mapped_condition, update_modified=True)
            elif self.unit_condition:
                unit.db_set("unit_condition", self.unit_condition, update_modified=True)

    def before_save(self):
        # Server Script: Rental Item Maintenance(Condition Update)
        if self.unit_serial_number:
            unit = frappe.get_doc("Rental Item Unit", self.unit_serial_number)
            new_condition = unit.unit_condition
            if self.workflow_state == "Attention Required" and self.unit_condition:
                new_condition = self.unit_condition
            elif self.workflow_state == "Complete":
                new_condition = self._resolve_final_condition()

            if new_condition != unit.unit_condition:
                unit.db_set("unit_condition", new_condition, update_modified=True, notify=False)

    def on_update(self):
        # Server Script: Rental Item Maintenance Status ,Update
        if self.unit_serial_number and self.workflow_state:
            try:
                unit_doc = frappe.get_doc("Rental Item Unit", self.unit_serial_number)
                unit_doc.db_set("maintenance_status", self.workflow_state, update_modified=True)

                # Enforce final condition when maintenance is completed.
                if self.workflow_state == "Complete":
                    final_condition = self._resolve_final_condition()
                    unit_doc.db_set("unit_condition", final_condition, update_modified=True)
            except frappe.DoesNotExistError:
                pass # Or log error

    def before_submit(self):
        # Server Script: Maintenance(Save) - renamed and integrated
        if self.workflow_state == "Complete" and self.unit_serial_number:
            unit = frappe.get_doc("Rental Item Unit", self.unit_serial_number)
            final_condition = self._resolve_final_condition()
            if unit.unit_condition != final_condition:
                unit.db_set("unit_condition", final_condition, update_modified=True, notify=False)

@frappe.whitelist()
def send_to_maintenance(docname):
    doc = frappe.get_doc("Rental Item Maintenance", docname)
    if doc.docstatus != 0:
        frappe.throw(_("Document already processed"))

    for row in doc.rental_item_unit_child_table:
        unit = frappe.get_doc("Rental Item Unit", row.unit_serial_number)
        unit.movement_status = "In Maintenance"
        unit.unit_location = "Repair Shop"
        unit.save(ignore_permissions=True)

    doc.submit()
