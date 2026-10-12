from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from rental_management.rental.setup.install import RENTAL_ITEM_GROUP, setup
from rental_management.rental.stock import get_warehouse
from rental_management.ui import catalog, dashboard, maintenance, movements, units


def ensure(doctype, name, **values):
    if not frappe.db.exists(doctype, name):
        frappe.get_doc({"doctype": doctype, **values}).insert()
    return name


class TestRentalUI(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        setup()
        self.enterContext(patch.object(frappe.db, "commit"))
        self.tag = frappe.generate_hash(length=5).upper()
        self.category = ensure("Item Group", "UI Test Lighting", item_group_name="UI Test Lighting", parent_item_group=RENTAL_ITEM_GROUP)
        self.item_type = ensure("Rent Item Type", "UI Test Spot", type_name="UI Test Spot", type_code="UTS")
        self.brand = ensure("Brand", "UI Test Robe", brand="UI Test Robe")

    def make_item(self, model="LED Wall Panel", kind="Unit"):
        return catalog.create_item(f"{model} {self.tag}", self.category, self.item_type, self.brand, kind)

    def make_units(self, count=3, model="LED Wall Panel", kind="Unit"):
        item_code = self.make_item(model, kind)
        return item_code, catalog.generate_units(item_code, count)["units_created"]

    def status(self, serial):
        return units.find_unit(serial)["status"]

    # ------------------------------------------------------------ catalog
    def test_item_code_and_serials_follow_the_model(self):
        item_code, serials = self.make_units(2)
        self.assertEqual(item_code, f"LEDWALLPANEL{self.tag}-UI-UI")
        self.assertEqual(serials, [f"{item_code}-001", f"{item_code}-002"])
        item = frappe.get_doc("Item", item_code)
        self.assertEqual((item.has_serial_no, item.is_stock_item, item.serial_no_series), (1, 1, f"{item_code}-.###"))
        self.assertEqual(self.status(serials[0]), "Warehouse")
        self.assertEqual(catalog.get_item_code("Box", "Flight Case 1", "x", "y"), "FLIGHTCASE1")
        with self.assertRaises(frappe.ValidationError):
            self.make_item()  # same code twice

    def test_unit_counts_need_a_sane_batch_and_no_bulk(self):
        item_code = self.make_item()
        for count in (0, catalog.MAX_UNITS_PER_BATCH + 1):
            with self.assertRaises(frappe.ValidationError):
                catalog.generate_units(item_code, count)
        chairs = self.make_item("Folding Chair", kind="Bulk")
        with self.assertRaises(frappe.ValidationError):
            catalog.generate_units(chairs, 2)

    def test_item_list_shows_live_availability(self):
        item_code, serials = self.make_units(4)
        movements.create_movement("CHECK_OUT", units=[serials[0]], to_location="Gala Dinner")
        maintenance.create_ticket(serials[1], "Damaged", "Cracked panel")
        row = next(r for r in catalog.list_items(search=self.tag)["rows"] if r["name"] == item_code)
        counts = row["counts"]
        self.assertEqual((counts["total"], counts["At Event"], counts["available"], counts["needs_attention"]), (4, 1, 2, 1))
        self.assertIn(self.category, catalog.facets()["categories"])

    # -------------------------------------------------------------- units
    def test_unit_search_filters_and_scan_lookup(self):
        item_code, serials = self.make_units(3)
        movements.create_movement("CHECK_OUT", units=[serials[0]], to_location="Expo")
        result = units.list_units(search=serials[0])
        self.assertEqual([row["serial_no"] for row in result["rows"]], [serials[0]])
        self.assertEqual(result["rows"][0]["location"], "Expo")
        self.assertEqual(units.list_units(item_code=item_code, status="Warehouse")["total"], 2)
        self.assertEqual(units.list_units(category=self.category, item_code=item_code)["total"], 3)
        self.assertEqual(units.list_units(item_code=item_code, location="exp")["total"], 1)
        self.assertEqual(units.find_unit(f"  {serials[1]} ")["serial_no"], serials[1])
        self.assertIsNone(units.find_unit("NOPE-999"))

    def test_unit_detail_has_history_and_open_ticket(self):
        _item, serials = self.make_units(2)
        movements.create_movement("CHECK_OUT", units=[serials[0]], to_location="Expo")
        ticket = maintenance.create_ticket(serials[0], "Need Cleaning", "Dusty")
        detail = units.get_unit(serials[0])
        self.assertEqual(detail["unit"]["status"], "At Event")
        self.assertEqual(detail["open_ticket"]["name"], ticket)
        movement = next(event for event in detail["history"] if event["status"] == "CHECK_OUT")
        self.assertEqual((movement["from_location"], movement["to_location"]), ("Warehouse", "Expo"))
        self.assertIn("Maintenance ticket", {event["kind"] for event in detail["history"]})

    def test_storage_address_builds_the_location_code(self):
        _item, serials = self.make_units(1)
        for doctype, field in (("Zone", "zone_name"), ("Aisle", "aisle_name"), ("Level", "level_name")):
            ensure(doctype, "UIT", **{field: "UIT"})
        detail = units.update_storage(serials[0], rental_zone="UIT", rental_aisle="UIT", rental_level="UIT")
        self.assertEqual(detail["unit"]["storage"], "UIT-UIT-UIT")

    # -------------------------------------------------------------- boxes
    def test_a_box_moves_with_its_contents(self):
        _items, serials = self.make_units(2)
        _cases, (case,) = self.make_units(1, model="Flight Case", kind="Box")
        units.pack(case, serials)
        self.assertEqual(len(units.get_unit(case)["contents"]), 2)
        self.assertFalse(movements.check_scan(serials[0], "CHECK_OUT")["ok"])  # packed: scan the box
        self.assertEqual(movements.check_scan(case, "CHECK_OUT")["unit"]["contents"], 2)
        movements.create_movement("CHECK_OUT", units=[case], to_location="Arena")
        self.assertEqual({self.status(serial) for serial in (case, *serials)}, {"At Event"})
        self.assertEqual(units.find_unit(serials[1])["location"], "Arena")

    def test_box_condition_follows_its_contents(self):
        _items, serials = self.make_units(2)
        _cases, (case,) = self.make_units(1, model="Flight Case", kind="Box")
        units.pack(case, serials)
        maintenance.create_ticket(serials[0], "Damaged", "Bent")
        self.assertEqual(units.find_unit(case)["condition"], "Partially Ok")
        self.assertFalse(movements.check_scan(case, "CHECK_OUT")["ok"])

    # ---------------------------------------------------------- movements
    def test_scan_rules(self):
        _item, serials = self.make_units(2)
        self.assertTrue(movements.check_scan(serials[0], "CHECK_OUT")["ok"])
        self.assertFalse(movements.check_scan(serials[0], "CHECK_IN")["ok"])
        self.assertFalse(movements.check_scan(serials[0], "MAINTENANCE_IN")["ok"])
        missing = movements.check_scan("NOPE", "CHECK_OUT")
        self.assertEqual((missing["ok"], missing["unit"]), (False, None))
        movements.create_movement("CHECK_OUT", units=[serials[0]], to_location="Expo")
        self.assertFalse(movements.check_scan(serials[0], "CHECK_OUT")["ok"])
        self.assertTrue(movements.check_scan(serials[0], "CHECK_IN")["ok"])

    def test_check_out_and_in_post_stock_entries(self):
        _item, serials = self.make_units(3)
        name = movements.create_movement("CHECK_OUT", units=serials[:2], to_location="Summit Hall", issued_to="Crew A")
        entry = frappe.get_doc("Stock Entry", name)
        self.assertEqual((entry.docstatus, entry.purpose, entry.rental_movement_type, entry.rental_venue), (1, "Material Transfer", "CHECK_OUT", "Summit Hall"))
        for serial in serials[:2]:
            self.assertEqual(frappe.db.get_value("Serial No", serial, "warehouse"), get_warehouse("At Event"))
        detail = movements.get_movement(name)
        self.assertEqual([row["serial_no"] for row in detail["units"]], serials[:2])
        self.assertEqual(detail["movement"]["to_location"], "Summit Hall")
        movements.create_movement("CHECK_IN", units=serials[:2], received_by="Store")
        self.assertEqual(units.find_unit(serials[0])["location"], "Warehouse")
        listed = movements.list_movements(transaction_type="CHECK_OUT")["rows"]
        self.assertEqual(next(r for r in listed if r["name"] == name)["units"], 2)

    def test_movement_rejects_bad_requests(self):
        _item, serials = self.make_units(2)
        for kwargs in (
            {"units": [serials[0]]},  # no destination
            {"units": [serials[0], serials[0]], "to_location": "X"},
            {"units": ["NOPE"], "to_location": "X"},
            {"to_location": "X"},  # nothing to move
        ):
            with self.assertRaises(frappe.ValidationError):
                movements.create_movement("CHECK_OUT", **kwargs)
        with self.assertRaises(frappe.ValidationError):
            movements.create_movement("TELEPORT", units=[serials[0]])
        movements.create_movement("CHECK_OUT", units=[serials[0]], to_location="X")
        with self.assertRaises(frappe.ValidationError):
            movements.create_movement("CHECK_OUT", units=[serials[0]], to_location="Y")  # already out

    def test_bulk_stock_moves_by_quantity(self):
        chairs = self.make_item("Folding Chair", kind="Bulk")
        catalog.receive_stock(chairs, 50)
        name = movements.create_movement("CHECK_OUT", bulk=[{"item_code": chairs, "qty": 40}], to_location="Hall")
        self.assertEqual([(row["item_code"], row["qty"]) for row in movements.get_movement(name)["bulk"]], [(chairs, 40)])
        counts = catalog.get_item(chairs)["item"]["counts"]
        self.assertEqual((counts["total"], counts["available"], counts["At Event"]), (50, 10, 40))
        with self.assertRaises(frappe.ValidationError):
            movements.create_movement("CHECK_OUT", bulk=[{"item_code": chairs, "qty": 11}], to_location="Hall")

    # -------------------------------------------------------- maintenance
    def test_ticket_flows_from_attention_to_complete(self):
        _item, serials = self.make_units(2)
        name = maintenance.create_ticket(serials[0], "Damaged", "Dead pixels")
        self.assertIn(name, [t["name"] for t in maintenance.board()["columns"]["Attention Required"]])
        self.assertEqual(units.find_unit(serials[0])["condition"], "Damaged")
        with self.assertRaises(frappe.ValidationError):
            maintenance.create_ticket(serials[0], "Damaged", "again")
        with self.assertRaises(frappe.ValidationError):
            maintenance.complete(name, "OK")
        ticket = maintenance.start_repair(name)
        self.assertEqual(ticket["ticket"]["workflow_state"], "In Repair")
        done = maintenance.complete(name, "OK", "Replaced the panel")
        self.assertEqual((done["ticket"]["workflow_state"], done["ticket"]["docstatus"]), ("Complete", 1))
        self.assertEqual(units.find_unit(serials[0])["condition"], "OK")

    def test_scrapped_units_stay_out_of_circulation(self):
        _item, serials = self.make_units(1)
        name = maintenance.create_ticket(serials[0], "Damaged", "Burnt")
        maintenance.start_repair(name)
        maintenance.complete(name, "Scrapped", "Beyond repair")
        self.assertEqual(units.find_unit(serials[0])["condition"], "Scrapped")
        self.assertFalse(movements.check_scan(serials[0], "CHECK_OUT")["ok"])

    # ---------------------------------------------------------- dashboard
    def test_dashboard_totals_add_up(self):
        item_code, serials = self.make_units(4)
        movements.create_movement("CHECK_OUT", units=serials[:3], to_location="Expo")
        maintenance.create_ticket(serials[3], "Need Cleaning", "Dusty")
        data = dashboard.get_dashboard()
        totals = data["totals"]
        self.assertEqual(sum(totals[status] for status in ("Warehouse", "At Event", "In Maintenance", "Missing")), totals["total"])
        self.assertGreaterEqual(totals["At Event"], 3)
        self.assertGreaterEqual(totals["needs_attention"], 1)
        self.assertTrue(any(row["name"] == item_code and row["tight"] for row in data["tight"]))
        self.assertTrue(any(row["location"] == "Expo" for row in data["locations"]))
        self.assertTrue(data["movements"] and data["tickets"])

    def test_users_without_access_are_refused(self):
        user = "rental.noaccess@example.com"
        if not frappe.db.exists("User", user):
            frappe.get_doc({"doctype": "User", "email": user, "first_name": "Plain", "send_welcome_email": 0}).insert()
        frappe.set_user(user)
        try:
            for call in (dashboard.get_dashboard, units.list_units):
                with self.assertRaises(frappe.PermissionError):
                    call()
            with self.assertRaises(frappe.PermissionError):
                movements.create_movement("CHECK_OUT", units=["X"], to_location="Y")
        finally:
            frappe.set_user("Administrator")
