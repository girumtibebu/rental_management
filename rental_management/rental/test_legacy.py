from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from rental_management.rental.legacy import LegacyData, import_legacy, parse_values
from rental_management.ui import units


class TestLegacyImport(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.enterContext(patch.object(frappe.db, "commit"))
		self.tag = frappe.generate_hash(length=5).upper()

	def legacy(self):
		tag = self.tag
		unit = {
			"item_template": "T1",
			"movement_status": "Warehouse",
			"unit_condition": "OK",
			"disabled": "0",
		}
		return LegacyData(
			{
				"Rent Item Type": [
					{"name": f"Spot {tag}", "type_name": f"Spot {tag}", "type_code": f"S{tag}"}
				],
				"Zone": [{"name": f"Z{tag}", "zone_name": f"Z{tag}"}],
				"Rental Item Template": [
					{
						"name": "T1",
						"creation": "2026-01-01 10:00:00",
						"item_model": f"Beam {tag}",
						"item_category": f"Legacy Lights {tag}",
						"item_brand": f"Robe {tag}",
						"item_type": f"Spot {tag}",
						"item_name": f"Beam {tag}",
						"rental_item_type_box": "Unit",
						"suffix": "3",
					}
				],
				"Rental Item Unit": [
					{
						**unit,
						"name": "U1",
						"creation": "2026-01-01 10:00:01",
						"movement_status": "At Event",
						"unit_location": "Expo",
						"unit_serial_number": f"BEAM{tag}-RO-SP-001",
						"zone": f"Z{tag}",
					},
					{
						**unit,
						"name": "U2",
						"creation": "2026-01-01 10:00:02",
						"unit_serial_number": f"BEAM{tag}-RO-SP-002",
						"movement_status": "At Event",
						"unit_location": "Hall",
					},
				],
				"Rental Movement": [
					{
						"name": "M1",
						"creation": "2026-02-01 09:00:00",
						"docstatus": "0",
						"transaction_type": "CHECK_OUT",
						"to_location": "Expo",
					},
				],
				"Rental Item Unit Child Table": [{"parent": "M1", "idx": "1", "unit_doc_id": "U1"}],
				"Rental Item Maintenance": [
					{
						"name": "RIM-X",
						"creation": "2026-02-02 09:00:00",
						"docstatus": "0",
						"unit_serial_number": "U2",
						"workflow_state": "Attention Required",
						"unit_condition": "Damaged",
						"issue_description": f"cracked {tag}",
					},
				],
			}
		)

	def test_old_records_become_items_serials_and_stock(self):
		summary = import_legacy(self.legacy())
		first, second = f"BEAM{self.tag}-RO-SP-001", f"BEAM{self.tag}-RO-SP-002"
		self.assertEqual(frappe.db.get_value("Serial No", first, "item_code"), f"BEAM{self.tag}-RO-SP")
		self.assertEqual(frappe.db.get_value("Serial No", first, "rental_zone"), f"Z{self.tag}")
		# U1 by the replayed check-out, U2 by matching the status its old record had
		self.assertEqual(units.find_unit(first)["status"], "At Event")
		self.assertEqual(units.find_unit(second)["status"], "At Event")
		self.assertEqual(frappe.db.get_value("Serial No", second, "rental_condition"), "Damaged")
		self.assertEqual(
			(summary.serials_created, summary.movements_replayed, summary.status_fixes, summary.tickets),
			(2, 1, 1, 1),
		)

		again = import_legacy(self.legacy())
		self.assertEqual(
			(again.serials_created, again.received, again.movements_replayed, again.tickets), (0, 0, 0, 0)
		)

	def test_dump_values_parse(self):
		self.assertEqual(
			parse_values("('a\\'b',NULL,3),('it''s','x\\ny',4);"),
			[["a'b", None, "3"], ["it's", "x\ny", "4"]],
		)
