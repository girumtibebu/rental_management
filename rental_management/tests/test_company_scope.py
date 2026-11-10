from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from rental_management.group import company_scope

USER = "company-scope@example.com"


def ensure_company(name, abbr):
	if not frappe.db.exists("Company", name):
		frappe.get_doc(
			{"doctype": "Company", "company_name": name, "abbr": abbr, "default_currency": "ETB", "country": "Ethiopia"}
		).insert()
	return name


class TestCompanyScope(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.enterContext(patch.object(frappe.db, "commit"))
		self.first = ensure_company("Scope Test One", "STO")
		self.second = ensure_company("Scope Test Two", "STT")
		if not frappe.db.exists("User", USER):
			frappe.get_doc(
				{"doctype": "User", "email": USER, "first_name": "Scope", "roles": [{"role": "Stock User"}]}
			).insert(ignore_permissions=True)
		frappe.db.delete("User Permission", {"user": USER})
		frappe.defaults.clear_user_default(company_scope.SCOPE_KEY, USER)
		frappe.clear_cache(user=USER)
		self.addCleanup(frappe.set_user, "Administrator")

	def permit(self, company):
		frappe.get_doc(
			{"doctype": "User Permission", "user": USER, "allow": "Company", "for_value": company, "apply_to_all_doctypes": 1}
		).insert(ignore_permissions=True)
		frappe.clear_cache(user=USER)

	def test_user_without_company_permissions_sees_every_company(self):
		allowed = company_scope.get_allowed_companies(USER)
		self.assertIn(self.first, allowed)
		self.assertIn(self.second, allowed)
		self.assertEqual(company_scope.get_scope(USER), allowed)
		self.assertFalse(company_scope.get_permission_query_conditions(USER, "Warehouse"))

	def test_group_companies_are_not_offered(self):
		group = frappe.db.get_value("Company", {"is_group": 1})
		if group:
			self.assertNotIn(group, company_scope.get_allowed_companies(USER))

	def test_user_with_one_company_only_gets_that_one(self):
		self.permit(self.first)
		self.assertEqual(company_scope.get_allowed_companies(USER), [self.first])
		frappe.set_user(USER)
		company_scope.set_scope([self.first, self.second])  # the other company is ignored
		self.assertEqual(company_scope.get_scope(USER), [self.first])

	def test_narrowing_the_scope_filters_lists(self):
		frappe.set_user(USER)
		company_scope.set_scope([self.first])
		self.assertEqual(company_scope.get_scope(USER), [self.first])
		condition = company_scope.get_permission_query_conditions(USER, "Warehouse")
		self.assertIn(self.first, condition)
		self.assertNotIn(self.second, condition)
		self.assertEqual(frappe.defaults.get_user_default("Company", USER), self.first)
		names = frappe.get_list("Warehouse", filters={"company": ["in", [self.first, self.second]]}, pluck="company")
		self.assertTrue(names)
		self.assertEqual(set(names), {self.first})

	def test_ticking_every_company_removes_the_filter(self):
		frappe.set_user(USER)
		company_scope.set_scope(company_scope.get_allowed_companies(USER))
		self.assertFalse(company_scope.get_permission_query_conditions(USER, "Warehouse"))

	def test_empty_choice_is_refused(self):
		frappe.set_user(USER)
		with self.assertRaises(frappe.ValidationError):
			company_scope.set_scope([])

	def test_doctypes_without_company_are_left_alone(self):
		frappe.set_user(USER)
		company_scope.set_scope([self.first])
		self.assertFalse(company_scope.get_permission_query_conditions(USER, "Item"))

	def test_company_print_formats_are_in_boot(self):
		from rental_management.rental.setup.custom_fields import setup_custom_fields

		setup_custom_fields()
		frappe.db.set_value("Company", self.first, "rental_sales_order_print_format", "Standard")
		formats = company_scope.get_company_print_formats()
		self.assertEqual(formats[self.first]["Sales Order"], "Standard")
