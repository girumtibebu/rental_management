import frappe
from frappe.model.document import Document
from frappe import _


def sync_box_condition_to_children(box_name, box_condition=None):
    if not box_name:
        return

    box_state = frappe.db.get_value(
        "Rental Item Unit",
        box_name,
        ["unit_condition", "movement_status", "unit_location"],
        as_dict=True,
    ) or {}

    movement_status_value = box_state.get("movement_status")
    location_value = box_state.get("unit_location")

    child_rows = frappe.get_all(
        "Box Item Unit Child Table",
        filters={
            "parent": box_name,
            "parenttype": "Rental Item Unit",
            "parentfield": "item_unit_list",
        },
        fields=["name", "document_id"],
    )

    child_conditions = []

    for row in child_rows:
        child_name = row.get("document_id")
        child_condition = None
        if child_name:
            child_info = frappe.db.get_value(
                "Rental Item Unit",
                child_name,
                ["unit_condition"],
                as_dict=True,
            ) or {}
            child_condition = child_info.get("unit_condition")
            if child_condition:
                child_conditions.append(child_condition)

        frappe.db.set_value(
            "Box Item Unit Child Table",
            row.name,
            {
                "unit_condition": child_condition,
                "movement_status": movement_status_value,
                "current_location": location_value,
            },
            update_modified=False,
        )
        if child_name:
            frappe.db.set_value(
                "Rental Item Unit",
                child_name,
                {
                    "movement_status": movement_status_value,
                    "unit_location": location_value,
                },
                update_modified=False,
            )

    if child_conditions:
        derived_condition = child_conditions[0] if len(set(child_conditions)) == 1 else "Partially Ok"
        if derived_condition != box_state.get("unit_condition"):
            frappe.db.set_value(
                "Rental Item Unit",
                box_name,
                "unit_condition",
                derived_condition,
                update_modified=False,
            )

class RentalItemUnit(Document):
    def before_save(self):
        # Server Script: Rental item unit - update parent
        # This part was disabled in server scripts, but I'll integrate the logic for "Box" type
        if self.unit_type == "Box":
            self.sync_box_units_on_save()
            self.sync_child_states_with_box()

    def after_insert(self):
        # Server Script: Math for Total Count
        self.update_template_quantities()

    def on_update(self):
        # Server Script: Math for Total Count
        self.update_template_quantities()
        if self.unit_type == "Box":
            sync_box_condition_to_children(self.name)

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

    def sync_child_states_with_box(self):
        child_conditions = []

        for item in self.item_unit_list or []:
            child_name = item.get("document_id")
            if not child_name:
                continue

            child_info = frappe.db.get_value(
                "Rental Item Unit",
                child_name,
                ["unit_condition"],
                as_dict=True,
            ) or {}

            child_condition = child_info.get("unit_condition")
            if child_condition:
                child_conditions.append(child_condition)
            item.unit_condition = child_condition
            item.movement_status = self.movement_status
            item.current_location = self.unit_location

            frappe.db.set_value(
                "Rental Item Unit",
                child_name,
                {
                    "movement_status": self.movement_status,
                    "unit_location": self.unit_location,
                },
                update_modified=False,
            )

        if child_conditions:
            self.unit_condition = child_conditions[0] if len(set(child_conditions)) == 1 else "Partially Ok"

    def update_template_quantities(self):
        # Logic from "Math for Total Count"
        if self.item_template:
            total_units = frappe.db.count("Rental Item Unit", {"item_template": self.item_template})
            frappe.db.set_value("Rental Item Template", self.item_template, "total_quantity", total_units)
