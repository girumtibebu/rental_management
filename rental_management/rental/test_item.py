from frappe.tests import UnitTestCase

from rental_management.rental.item import get_serial_no_series, get_serial_prefix


class TestRentalSerialPrefix(UnitTestCase):
    def test_unit_prefix_matches_old_sku(self):
        self.assertEqual(get_serial_prefix("tbl 6ft", "Acme", "Furniture", "Unit"), "TBL6FT-AC-FU")

    def test_box_prefix_is_model_only(self):
        self.assertEqual(get_serial_prefix("Case-12", "Acme", "Furniture", "Box"), "CASE12")

    def test_missing_model(self):
        self.assertIsNone(get_serial_prefix("", "Acme", "Furniture"))

    def test_series(self):
        self.assertEqual(get_serial_no_series("TBL6FT-AC-FU", 3), "TBL6FT-AC-FU-.###")
