"""Move the old rental doctypes onto Item, Serial No and Stock Entry.

The old tables are left in place and can be dropped later; see
rental_management.rental.legacy for what the import does.
"""

import frappe

from rental_management.rental.legacy import LegacyData, import_legacy


def execute():
	if not frappe.db.table_exists("Rental Item Template"):
		return
	import_legacy(LegacyData.from_site())
	frappe.db.delete("Print Format", {"doc_type": "Rental Movement"})
