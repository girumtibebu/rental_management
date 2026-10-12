from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from rental_management.ui import catalog, dashboard, maintenance, movements, units


def ensure(doctype, name, **values):
    key = {"Rent Item Category": "category", "Rent Item Type": "type", "Rent Item Brand": "brand"}[doctype]
    if not frappe.db.exists(doctype, name):
        frappe.get_doc({"doctype": doctype, f"{key}_name": name, f"{key}_code": name[:3].upper(), **values}).insert()
    return name


class TestRentalUI(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        # the app's "create units" helper commits; keep every test inside its own rollback
        self.enterContext(patch.object(frappe.db, "commit"))
        self.tag = frappe.generate_hash(length=5).upper()
        self.category = ensure("Rent Item Category", "UI Test Lighting")
        self.item_type = ensure("Rent Item Type", "UI Test Spot")
        self.brand = ensure("Rent Item Brand", "UI Test Robe")

    def make_template(self, model="LED Wall Panel", kind="Unit", activate=1):
        return catalog.create_template(f"{model} {self.tag}", self.category, self.item_type, self.brand, kind, activate=activate)

    def make_units(self, count=3, model="LED Wall Panel"):
        template = self.make_template(model)
        created = catalog.generate_units(template, count)["units_created"]
        return template, created

    # ------------------------------------------------------------ catalog
    def test_template_name_and_serial_pattern_follow_the_desk_rules(self):
        name = self.make_template("LED Wall Panel")
        doc = frappe.get_doc("Rental Item Template", name)
        self.assertEqual(doc.item_name, f"LED Wall Panel {self.tag} UI Test Robe UI Test Spot")
        self.assertEqual(doc.sku_naming_series, f"LEDWALLPANEL{self.tag}-UI-UI-###")
        self.assertEqual(doc.status, "Completed")
        self.assertEqual(catalog.sku_series("Box", "Flight Case 1", "x", "y", 2), "FLIGHTCASE1-##")
        self.assertEqual(catalog.sku_series("Bulk", "Chair", "x", "y", 3), "NONE")

    def test_units_need_an_active_template_and_a_sane_count(self):
        draft = self.make_template("Draft Item", activate=0)
        with self.assertRaises(frappe.ValidationError):
            catalog.generate_units(draft, 2)
        catalog.activate_template(draft)
        with self.assertRaises(frappe.ValidationError):
            catalog.generate_units(draft, 0)
        with self.assertRaises(frappe.ValidationError):
            catalog.generate_units(draft, catalog.MAX_UNITS_PER_BATCH + 1)
        bulk = self.make_template("Folding Chair", kind="Bulk")
        with self.assertRaises(frappe.ValidationError):
            catalog.generate_units(bulk, 2)

    def test_template_list_shows_live_availability(self):
        template, serials = self.make_units(4)
        movements.create_movement("CHECK_OUT", units=[serials[0]], to_location="Gala Dinner")
        maintenance.create_ticket(serials[1], "Damaged", "Cracked panel")
        row = next(r for r in catalog.list_templates(search=self.tag)["rows"] if r["name"] == template)
        counts = row["counts"]
        self.assertEqual((counts["total"], counts["At Event"], counts["available"], counts["needs_attention"]), (4, 1, 2, 1))
        self.assertIn(self.category, catalog.facets()["categories"])

    # -------------------------------------------------------------- units
    def test_unit_search_filters_and_scan_lookup(self):
        template, serials = self.make_units(3)
        movements.create_movement("CHECK_OUT", units=[serials[0]], to_location="Expo")
        result = units.list_units(search=serials[0])
        self.assertEqual([row["unit_serial_number"] for row in result["rows"]], [serials[0]])
        self.assertEqual(result["rows"][0]["location"], "Expo")
        stocked = units.list_units(template=template, status="Warehouse")
        self.assertEqual(stocked["total"], 2)
        by_category = units.list_units(category=self.category, template=template)
        self.assertEqual(by_category["total"], 3)
        found = units.find_unit(f"  {serials[1]} ")
        self.assertEqual(found["unit_serial_number"], serials[1])
        self.assertEqual(units.find_unit(found["name"])["name"], found["name"])
        self.assertIsNone(units.find_unit("NOPE-999"))

    def test_unit_detail_has_history_and_open_ticket(self):
        _template, serials = self.make_units(2)
        movements.create_movement("CHECK_OUT", units=[serials[0]], to_location="Expo")
        ticket = maintenance.create_ticket(serials[0], "Need Cleaning", "Dusty")
        detail = units.get_unit(units.resolve(serials[0]))
        self.assertEqual(detail["unit"]["movement_status"], "At Event")
        self.assertEqual(detail["open_ticket"]["name"], ticket)
        kinds = {event["kind"] for event in detail["history"]}
        self.assertTrue({"Movement", "Maintenance ticket"} <= kinds)
        self.assertTrue(detail["can"]["write"])

    # ---------------------------------------------------------- movements
    def test_scan_rules_match_the_desk_form(self):
        _template, serials = self.make_units(2)
        self.assertTrue(movements.check_scan(serials[0], "CHECK_OUT")["ok"])
        self.assertFalse(movements.check_scan(serials[0], "CHECK_IN")["ok"])  # already in the warehouse
        self.assertFalse(movements.check_scan(serials[0], "MAINTENANCE_IN")["ok"])
        missing = movements.check_scan("NOPE", "CHECK_OUT")
        self.assertEqual((missing["ok"], missing["unit"]), (False, None))
        movements.create_movement("CHECK_OUT", units=[serials[0]], to_location="Expo")
        self.assertFalse(movements.check_scan(serials[0], "CHECK_OUT")["ok"])
        self.assertTrue(movements.check_scan(serials[0], "CHECK_IN")["ok"])

    def test_check_out_and_back_in_updates_units_and_availability(self):
        template, serials = self.make_units(3)
        name = movements.create_movement("CHECK_OUT", units=serials[:2], to_location="Summit Hall", issued_to="Crew A")
        for serial in serials[:2]:
            unit = frappe.db.get_value("Rental Item Unit", {"unit_serial_number": serial}, ["movement_status", "unit_location"], as_dict=True)
            self.assertEqual((unit.movement_status, unit.unit_location), ("At Event", "Summit Hall"))
        detail = movements.get_movement(name)
        self.assertEqual([row["unit_serial_number"] for row in detail["units"]], serials[:2])
        self.assertEqual(frappe.db.get_value("Rental Item Template", template, "available_quantity"), "1")
        movements.create_movement("CHECK_IN", units=serials[:2])
        self.assertEqual(units.find_unit(serials[0])["movement_status"], "Warehouse")
        self.assertEqual(units.find_unit(serials[0])["location"], "Warehouse")
        listed = movements.list_movements(transaction_type="CHECK_OUT")["rows"]
        self.assertEqual(next(r for r in listed if r["name"] == name)["units"], 2)

    def test_movement_rejects_bad_requests(self):
        _template, serials = self.make_units(2)
        with self.assertRaises(frappe.ValidationError):
            movements.create_movement("CHECK_OUT", units=[serials[0]])  # no destination
        with self.assertRaises(frappe.ValidationError):
            movements.create_movement("CHECK_OUT", units=[serials[0], serials[0]], to_location="X")
        with self.assertRaises(frappe.ValidationError):
            movements.create_movement("CHECK_OUT", units=["NOPE"], to_location="X")
        with self.assertRaises(frappe.ValidationError):
            movements.create_movement("CHECK_OUT", to_location="X")  # nothing to move
        with self.assertRaises(frappe.ValidationError):
            movements.create_movement("TELEPORT", units=[serials[0]])
        movements.create_movement("CHECK_OUT", units=[serials[0]], to_location="X")
        with self.assertRaises(frappe.ValidationError):
            movements.create_movement("CHECK_OUT", units=[serials[0]], to_location="Y")  # already out

    def test_bulk_lines_are_stored_on_the_movement(self):
        chairs = self.make_template("Folding Chair", kind="Bulk")
        name = movements.create_movement("CHECK_OUT", bulk=[{"template": chairs, "qty": 40, "note": "banquet"}], to_location="Hall")
        bulk = movements.get_movement(name)["bulk"]
        self.assertEqual([(row["item_template"], row["qty"]) for row in bulk], [(chairs, 40)])

    # -------------------------------------------------------- maintenance
    def test_ticket_flows_from_attention_to_complete(self):
        _template, serials = self.make_units(2)
        name = maintenance.create_ticket(serials[0], "Damaged", "Dead pixels")
        board = maintenance.board()
        self.assertIn(name, [t["name"] for t in board["columns"]["Attention Required"]])
        self.assertEqual(units.find_unit(serials[0])["unit_condition"], "Damaged")
        with self.assertRaises(frappe.ValidationError):
            maintenance.create_ticket(serials[0], "Damaged", "again")  # one open ticket per unit
        with self.assertRaises(frappe.ValidationError):
            maintenance.complete(name, "OK")  # repair has not started
        ticket = maintenance.start_repair(name)
        self.assertEqual(ticket["ticket"]["workflow_state"], "In Repair")
        self.assertIn("Complete", ticket["actions"])
        done = maintenance.complete(name, "OK", "Replaced the panel")
        self.assertEqual((done["ticket"]["workflow_state"], done["ticket"]["docstatus"]), ("Complete", 1))
        self.assertEqual(units.find_unit(serials[0])["unit_condition"], "OK")
        self.assertIn(name, [t["name"] for t in maintenance.board()["columns"]["Complete"]])

    def test_scrapped_units_stay_out_of_circulation(self):
        _template, serials = self.make_units(1)
        name = maintenance.create_ticket(serials[0], "Damaged", "Burnt")
        maintenance.start_repair(name)
        maintenance.complete(name, "Scrapped", "Beyond repair")
        self.assertEqual(units.find_unit(serials[0])["unit_condition"], "Scrapped")
        self.assertFalse(movements.check_scan(serials[0], "CHECK_OUT")["ok"])

    # ---------------------------------------------------------- dashboard
    def test_dashboard_totals_add_up(self):
        template, serials = self.make_units(4)
        movements.create_movement("CHECK_OUT", units=serials[:3], to_location="Expo")
        maintenance.create_ticket(serials[3], "Need Cleaning", "Dusty")
        data = dashboard.get_dashboard()
        totals = data["totals"]
        self.assertEqual(sum(totals[status] for status in ("Warehouse", "At Event", "In Maintenance", "Missing")), totals["total"])
        self.assertGreaterEqual(totals["At Event"], 3)
        self.assertGreaterEqual(totals["needs_attention"], 1)
        tight = [row for row in data["tight"] if row["name"] == template]
        self.assertTrue(tight and tight[0]["tight"])
        self.assertTrue(any(row["location"] == "Expo" for row in data["locations"]))
        self.assertTrue(data["movements"] and data["tickets"])

    def test_users_without_access_are_refused(self):
        user = "rental.noaccess@example.com"
        if not frappe.db.exists("User", user):
            frappe.get_doc({"doctype": "User", "email": user, "first_name": "Plain", "send_welcome_email": 0, "roles": [{"role": "Sales User"}]}).insert()
        frappe.set_user(user)
        try:
            with self.assertRaises(frappe.PermissionError):
                dashboard.get_dashboard()
            with self.assertRaises(frappe.PermissionError):
                units.list_units()
            with self.assertRaises(frappe.PermissionError):
                movements.create_movement("CHECK_OUT", units=["X"], to_location="Y")
        finally:
            frappe.set_user("Administrator")
