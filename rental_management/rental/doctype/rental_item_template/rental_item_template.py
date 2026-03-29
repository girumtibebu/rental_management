import frappe
from frappe.model.document import Document

class RentalItemTemplate(Document):
    def validate(self):
        # Server Script: Bulk Item Option (Hiding fields and Creating Button)
        if self.rental_item_type_box == "Bulk":
            if not self.suffix:
                self.suffix = "NONE"
            if not self.sku_naming_series:
                self.sku_naming_series = "NONE"
            if not self.sku_character_count:
                self.sku_character_count = 0
            
            self.flags.ignore_mandatory = True
