import frappe
from frappe.model.document import Document
from frappe import _

class RentalItemUnit(Document):
    def before_save(self):
        # Server Script: Rental item unit - update parent
        # This part was disabled in server scripts, but I'll integrate the logic for "Box" type
        if self.unit_type == "Box":
            self.sync_box_units_on_save()
            self.sync_child_conditions_with_box()

    def after_insert(self):
        # Server Script: Math for Total Count
        self.update_template_quantities()

    def on_update(self):
        # Server Script: Math for Total Count
        self.update_template_quantities()

    def sync_box_units_on_save(self):
        # Logic from "Rental Item Unit - Update parent box"
        current_units = [row.get("document_id") for row in self.get("item_unit_list") if row.get("document_id")]
        
        for current_serial in current_units:
            unit_info = frappe.db.get_value("Rental Item Unit", current_serial, ["unit_serial_number", "parent_box"], as_dict=True)
            if not unit_info:
                continue

            raw_parent = unit_info.parent_box
            if raw_parent != self.name:
                # Cleanup old parent if needed
                actual_parent = None if not raw_parent or str(raw_parent).strip().lower() == "none" else raw_parent
                if actual_parent and actual_parent != self.name:
                    try:
                        old_box = frappe.get_doc("Rental Item Unit", actual_parent)
                        old_box.set("item_unit_list", [row for row in old_box.get("item_unit_list") if row.get("document_id") != current_serial])
                        old_box.save(ignore_permissions=True)
                    except frappe.DoesNotExistError:
                        pass
                
                frappe.db.set_value("Rental Item Unit", current_serial, "parent_box", self.name)

        # Handle REMOVALS
        if not self.is_new():
            old_doc = self.get_doc_before_save()
            if old_doc:
                old_units = set([r.get("document_id") for r in old_doc.get("item_unit_list") if r.get("document_id")])
                removed_units = old_units - set(current_units)
                for u in removed_units:
                    if frappe.db.get_value("Rental Item Unit", u, "parent_box") == self.name:
                        frappe.db.set_value("Rental Item Unit", u, "parent_box", None)

    def sync_child_conditions_with_box(self):
        # Box condition is authoritative for every child unit.
        if not self.unit_condition:
            return

        for item in self.item_unit_list or []:
            if item.unit_condition != self.unit_condition:
                item.unit_condition = self.unit_condition

            child_name = item.get("document_id")
            if child_name:
                frappe.db.set_value(
                    "Rental Item Unit",
                    child_name,
                    "unit_condition",
                    self.unit_condition,
                    update_modified=False,
                )

    def update_template_quantities(self):
        # Logic from "Math for Total Count"
        if self.item_template:
            total_units = frappe.db.count("Rental Item Unit", {"item_template": self.item_template})
            frappe.db.set_value("Rental Item Template", self.item_template, "total_quantity", total_units)
