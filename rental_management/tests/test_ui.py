from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from rental_management.rental.setup.install import RENTAL_ITEM_GROUP, setup
from rental_management.rental.stock import WORKSPACE, get_bulk_quantities, get_settings, get_warehouse
from rental_management.ui import catalog, dashboard, links, maintenance, movements, units, workspaces


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

    # ---------------------------------------------------------- workspaces
    def test_default_workspace_is_created_and_listed(self):
        default = get_settings()
        self.assertTrue(default.is_default)
        self.assertIn(default.name, [row.name for row in workspaces.list_workspaces()])

    def test_unknown_workspace_is_refused(self):
        frappe.flags.rental_workspace = "No Such Workspace"
        self.addCleanup(frappe.flags.pop, "rental_workspace", None)
        with self.assertRaises(frappe.DoesNotExistError):
            get_settings()

    def test_workspace_access_follows_the_users_list(self):
        default = get_settings().name
        user = "workspace-user@example.com"
        if not frappe.db.exists("User", user):
            frappe.get_doc({"doctype": "User", "email": user, "first_name": "Workspace", "roles": [{"role": "Stock User"}]}).insert(ignore_permissions=True)
        self.assertIn(default, [row.name for row in workspaces.allowed_workspaces(user)])  # no users listed: open
        workspace = frappe.get_doc(WORKSPACE, default)
        workspace.append("users", {"user": "Administrator"})
        workspace.save()
        self.assertNotIn(default, [row.name for row in workspaces.allowed_workspaces(user)])
        with self.assertRaises(frappe.PermissionError):
            workspaces.resolve_workspace(default, user)
        self.assertIn(default, [row.name for row in workspaces.allowed_workspaces("Administrator")])

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
    def test_bulk_first_dashboard_counts_pieces(self):
        chairs = self.make_item("Dashboard Chair", kind="Bulk")
        catalog.receive_stock(chairs, 30)
        movements.create_movement("CHECK_OUT", bulk=[{"item_code": chairs, "qty": 10}], to_location="Hall")
        name = get_settings().name
        before = frappe.db.get_value(WORKSPACE, name, "mode")
        frappe.db.set_value(WORKSPACE, name, "mode", "Bulk First")
        frappe.clear_document_cache(WORKSPACE, name)
        self.addCleanup(frappe.clear_document_cache, WORKSPACE, name)
        self.addCleanup(frappe.db.set_value, WORKSPACE, name, "mode", before)
        data = dashboard.get_dashboard()
        self.assertEqual(data["mode"], "Bulk First")
        row = next(row for row in data["stock"] if row["name"] == chairs)
        self.assertEqual((row["Warehouse"], row["At Event"], row["total"]), (20, 10, 30))
        self.assertGreaterEqual(data["totals"]["total"], 30)

    def test_workspace_item_group_scopes_the_catalog(self):
        item_code = self.make_item("Scoped Chair", kind="Bulk")
        other = ensure("Item Group", "UI Test Other", item_group_name="UI Test Other", parent_item_group=RENTAL_ITEM_GROUP)
        name = get_settings().name
        self.addCleanup(frappe.clear_document_cache, WORKSPACE, name)
        self.addCleanup(frappe.db.set_value, WORKSPACE, name, "item_group", None)

        def listed():
            frappe.clear_document_cache(WORKSPACE, name)
            return [row["item_code"] for row in catalog.list_items(search=item_code)["rows"]]

        frappe.db.set_value(WORKSPACE, name, "item_group", self.category)
        self.assertIn(item_code, listed())
        self.assertEqual(catalog.get_categories(), [self.category])
        frappe.db.set_value(WORKSPACE, name, "item_group", other)
        self.assertNotIn(item_code, listed())

    def test_decor_item_follows_the_workspace_company_and_cost_center(self):
        name = get_settings().name
        cost_center = frappe.db.get_value("Company", get_settings().company, "cost_center")
        self.addCleanup(frappe.clear_document_cache, WORKSPACE, name)
        item_code = catalog.create_decor_item(f"Decor Vase {self.tag}", self.category)
        item = frappe.get_doc("Item", item_code)
        self.assertEqual((item.is_stock_item, item.has_serial_no), (1, 0))
        default = item.item_defaults[0]
        self.assertEqual(default.company, get_settings().company)
        self.assertEqual(default.default_warehouse, get_settings().store_warehouse)
        self.assertEqual(default.buying_cost_center, cost_center)
        entry = frappe.get_doc("Stock Entry", catalog.receive_stock(item_code, 5))
        self.assertEqual(entry.items[0].cost_center, cost_center)

    def test_services_and_main_store(self):
        name = get_settings().name
        self.addCleanup(frappe.clear_document_cache, WORKSPACE, name)
        self.addCleanup(frappe.db.set_value, WORKSPACE, name, "item_group", None)
        self.addCleanup(frappe.db.set_value, WORKSPACE, name, "main_store_warehouse", None)
        group = ensure("Item Group", "UI Test Services", item_group_name="UI Test Services", parent_item_group=RENTAL_ITEM_GROUP)
        service = frappe.get_doc({"doctype": "Item", "item_code": f"UI-SVC-{self.tag}", "item_name": f"Design {self.tag}", "item_group": group, "stock_uom": "Nos", "is_stock_item": 0}).insert()
        stocked = self.make_item("Scoped Lamp", kind="Bulk")
        frappe.db.set_value(WORKSPACE, name, "item_group", RENTAL_ITEM_GROUP)
        frappe.clear_document_cache(WORKSPACE, name)
        listed = [row["item_code"] for row in catalog.list_items(search=self.tag)["rows"]]
        self.assertIn(stocked, listed)
        self.assertNotIn(service.name, listed)
        self.assertNotIn(group, catalog.get_categories())

        # With a main store, adding stock to the rental store is a transfer from it.
        company = get_settings().company
        main = frappe.get_doc({"doctype": "Warehouse", "warehouse_name": f"UI Main Store {self.tag}", "company": company}).insert().name
        frappe.db.set_value(WORKSPACE, name, "main_store_warehouse", main)
        frappe.clear_document_cache(WORKSPACE, name)
        with self.assertRaises(frappe.ValidationError):
            catalog.receive_stock(stocked, 5)  # nothing in the main store yet
        frappe.get_doc(
            {
                "doctype": "Stock Entry",
                "company": company,
                "stock_entry_type": "Material Receipt",
                "purpose": "Material Receipt",
                "items": [{"item_code": stocked, "qty": 20, "t_warehouse": main, "allow_zero_valuation_rate": 1}],
            }
        ).insert().submit()
        entry = frappe.get_doc("Stock Entry", catalog.receive_stock(stocked, 5))
        self.assertEqual((entry.purpose, entry.items[0].s_warehouse), ("Material Transfer", main))
        self.assertEqual(get_bulk_quantities([stocked])[stocked]["Warehouse"], 5)

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

    # ------------------------------------------------------------ quick create
    def test_missing_link_records_are_created_from_the_app(self):
        category = links.quick_create("Item Group", f"UI Test Rigging {self.tag}")
        self.assertEqual(frappe.db.get_value("Item Group", category, "parent_item_group"), RENTAL_ITEM_GROUP)
        self.assertIn(category, catalog.get_categories())

        first = links.quick_create("Rent Item Type", f"Truss {self.tag}")
        second = links.quick_create("Rent Item Type", f"Truss Clamp {self.tag}")
        codes = {frappe.db.get_value("Rent Item Type", name, "type_code") for name in (first, second)}
        self.assertEqual(len(codes), 2)

        zone = links.quick_create("Zone", f"Z{self.tag}")
        self.assertEqual(links.quick_create("Zone", f"Z{self.tag}"), zone)
        with self.assertRaises(frappe.ValidationError):
            links.quick_create("User", "someone")

    def test_desk_icon_opens_the_rental_app(self):
        if not frappe.db.table_exists("Desktop Icon"):
            return
        icon = frappe.db.get_value("Desktop Icon", "Rental Management", ["icon_type", "link_type", "link", "hidden"], as_dict=True)
        self.assertEqual((icon.icon_type, icon.link_type, icon.link, icon.hidden), ("App", "External", "/rental", 0))
        self.assertFalse(frappe.db.exists("Workspace", {"module": "Rental"}))
