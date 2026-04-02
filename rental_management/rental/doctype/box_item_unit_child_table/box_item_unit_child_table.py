# Copyright (c) 2026, emc and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BoxItemUnitChildTable(Document):
    @property
    def document_id(self):
        return self.get("document_id")

    @document_id.setter
    def document_id(self, value):
        self.set("document_id", value)

    @property
    def serial_number(self):
        return self.get("unit_serial_number")

    @serial_number.setter
    def serial_number(self, value):
        self.set("unit_serial_number", value)
