import frappe
from frappe.model.document import Document
from frappe.utils import now
from rental_management.rental.doctype.rental_item_unit.rental_item_unit import sync_box_condition_to_children


class RentalMovement(Document):
    WAREHOUSE_ALIASES = {
        "warehouse",
        "main warehouse",
        "wearehouse",
        "waerhous",
        "warehous",
        "wearhouse",
    }

    def validate(self):
        self.normalize_and_validate_locations()

    def after_insert(self):
        # Server Script: Rental Movement Tracking (Math)
        self.update_template_tracking()

    def on_update(self):
        # Server Script: Rental Movement Save
        self.update_unit_master_records()

    def on_submit(self):
        # Server Script: Unit Log_Rental Movement
        self.create_unit_logs()

    def normalize_location(self, value):
        if not value:
            return value

        normalized = str(value).strip()
        if normalized.lower() in self.WAREHOUSE_ALIASES:
            return "Warehouse"
        return normalized

    def normalize_and_validate_locations(self):
        self.from_location = self.normalize_location(self.from_location)
        self.to_location = self.normalize_location(self.to_location)

        tx = self.transaction_type

        # Keep incoming warehouse moves consistent across docs.
        if tx in ["CHECK_IN", "MAINTENANCE_IN"]:
            self.to_location = "Warehouse"

        if tx == "CHECK_OUT" and not self.to_location:
            frappe.throw("To Location is required for CHECK_OUT.")

        if tx == "MAINTENANCE_OUT" and not self.to_location:
            self.to_location = "Repair Shop"

    def get_effective_unit_condition(self, unit_name, fallback_condition=None):
        # Prefer latest completed maintenance final condition as the current condition.
        final_condition = frappe.db.get_value(
            "Rental Item Maintenance",
            {
                "unit_serial_number": unit_name,
                "workflow_state": "Complete",
                "final_condition": ["is", "set"],
            },
            "final_condition",
            order_by="modified desc",
        )
        return final_condition or fallback_condition

    def update_template_tracking(self):
        units = self.get("rental_item_unit_child_table") or []
        for row in units:
            unit_name = row.get("unit_doc_id")
            if unit_name:
                unit = frappe.get_doc("Rental Item Unit", unit_name)
                template_name = unit.item_template
                if template_name:
                    total_units = frappe.db.count("Rental Item Unit", {"item_template": template_name})
                    template_doc = frappe.get_doc("Rental Item Template", template_name)
                    available_units = int(template_doc.available_quantity or total_units)
                    total_quantity = int(template_doc.total_quantity or total_units)

                    if self.transaction_type == "CHECK_OUT":
                        available_units -= 1
                    elif self.transaction_type == "CHECK_IN":
                        available_units += 1
                    elif self.transaction_type == "MAINTENANCE_OUT":
                        available_units -= 1
                    elif self.transaction_type == "MAINTENANCE_IN":
                        available_units += 1
                    elif self.transaction_type == "LOST":
                        total_quantity -= 1
                        available_units -= 1
                    elif self.transaction_type == "PURCHASE":
                        total_quantity += 1
                        available_units += 1
                    elif self.transaction_type == "DISPOSE":
                        total_quantity -= 1
                        available_units -= 1

                    available_units = max(0, min(available_units, total_quantity))
                    total_quantity = max(0, total_quantity)
                    frappe.db.set_value("Rental Item Template", template_name, {
                        "total_quantity": total_quantity,
                        "available_quantity": available_units
                    })

    def update_unit_master_records(self):
        tx = self.transaction_type
        for row in self.get("rental_item_unit_child_table"):
            if not row.unit_doc_id:
                continue

            master = frappe.get_doc("Rental Item Unit", row.unit_doc_id)
            current_condition = self.get_effective_unit_condition(master.name, master.unit_condition)
            if tx == 'CHECK_OUT' and (master.movement_status != 'Warehouse' or current_condition != 'OK'):
                frappe.throw(f"Validation Error for {master.unit_serial_number}: Item must be in Warehouse and OK.")

            new_status = master.movement_status
            new_location = master.unit_location

            if tx == 'CHECK_OUT':
                new_status = 'At Event'
                new_location = self.normalize_location(self.to_location)
            elif tx in ['CHECK_IN', 'MAINTENANCE_IN']:
                new_status = 'Warehouse'
                new_location = 'Warehouse'
            elif tx == 'MAINTENANCE_OUT':
                new_status = 'In Maintenance'
                new_location = self.normalize_location(self.to_location) or 'Repair Shop'
            elif tx == 'LOST':
                new_status = 'Missing'
                new_location = 'Unknown'

            new_unit_condition = row.unit_condition
            if tx == 'CHECK_OUT':
                new_unit_condition = current_condition

            frappe.db.set_value("Rental Item Unit", master.name, {
                "unit_location": new_location,
                "movement_status": new_status,
                "unit_condition": new_unit_condition
            })

            if master.unit_type == "Box" and new_unit_condition:
                sync_box_condition_to_children(master.name, new_unit_condition)

            frappe.db.set_value("Rental Item Unit Child Table", row.name, {
                "unit_location": new_location,
                "movement_status": new_status
            })

    def create_unit_logs(self):
        for item in self.get("rental_item_unit_child_table") or []: # Updated from item_unit_list based on scripts
            if not item.unit_serial_number: # Updated from serial_number based on child table schema
                continue
            
            new_log = frappe.get_doc({
                "doctype": "Rental Unit Log",
                "unit": item.unit_doc_id, # Link field
                "event_type": "Movement",
                "reference_doctype": self.doctype, 
                "reference_name": self.name,       
                "from_location": self.normalize_location(self.from_location),
                "to_location": self.normalize_location(self.to_location),
                "status": self.movement_status or self.transaction_type, # Safe fallback
                "date": now()
            })
            new_log.insert(ignore_permissions=True)
