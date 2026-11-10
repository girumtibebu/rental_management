"""Company switcher: let a user narrow Desk lists to some of the companies they may see.

Two layers decide which company's records a user sees:

1. Access (set by an admin): the user's Company User Permissions. A user with one
   company only ever sees that company. A user with none sees every company.
2. Scope (picked by the user in the switcher at the top of Desk): a subset of the
   companies they have access to. Ticking every company shows everything; ticking
   one narrows lists, link searches and reports built on lists to that company.

The scope is stored as a user default, so it follows the user across devices and
sessions. The first company in the scope also becomes the user's default company,
so new documents start in it.
"""

import json

import frappe
from frappe import _

from rental_management.group.constants import PRINT_FORMAT_DOCTYPES

SCOPE_KEY = "rental_company_scope"


def get_company_options():
	"""Every trading (non-group) company, in tree order."""
	return frappe.get_all(
		"Company",
		filters={"is_group": 0},
		fields=["name", "abbr", "company_logo"],
		order_by="lft asc",
		ignore_permissions=True,
	)


def get_allowed_companies(user=None):
	"""Companies the user may see: their Company User Permissions, or every company when they have none."""
	from frappe.permissions import get_user_permissions

	user = user or frappe.session.user
	options = [row.name for row in get_company_options()]
	permissions = get_user_permissions(user).get("Company")
	if not permissions:
		return options
	permitted = {row.get("doc") for row in permissions}
	return [name for name in options if name in permitted]


def get_scope(user=None):
	"""Companies the user chose to see; all allowed companies when they never chose."""
	user = user or frappe.session.user
	allowed = get_allowed_companies(user)
	saved = frappe.defaults.get_user_default(SCOPE_KEY, user)
	try:
		chosen = json.loads(saved) if saved else []
	except (TypeError, ValueError):
		chosen = []
	scope = [name for name in allowed if name in (chosen or [])]
	return scope or allowed


@frappe.whitelist()
def get_switcher():
	allowed = get_allowed_companies()
	options = {row.name: row for row in get_company_options()}
	return {
		"companies": [
			{"name": name, "abbr": options[name].abbr, "logo": options[name].company_logo} for name in allowed
		],
		"scope": get_scope(),
	}


@frappe.whitelist()
def set_scope(companies):
	"""Save the switcher choice. Companies the user has no access to are refused."""
	if isinstance(companies, str):
		companies = json.loads(companies)
	allowed = get_allowed_companies()
	companies = [name for name in allowed if name in set(companies or [])]
	if not companies:
		frappe.throw(_("Pick at least one company."))
	user = frappe.session.user
	frappe.defaults.set_user_default(SCOPE_KEY, json.dumps(companies), user)
	if frappe.defaults.get_user_default("Company") not in companies:
		frappe.defaults.set_user_default("company", companies[0], user)
	frappe.clear_cache(user=user)
	return get_switcher()


def get_permission_query_conditions(user=None, doctype=None):
	"""List filter for the switcher. Nothing is added while the user sees all their companies."""
	if not doctype or frappe.flags.ignore_company_scope:
		return ""
	user = user or frappe.session.user
	if user == "Guest":
		return ""
	field = frappe.get_meta(doctype).get_field("company")
	if not field or field.fieldtype != "Link" or field.options != "Company":
		return ""
	allowed = get_allowed_companies(user)
	scope = get_scope(user)
	if set(scope) >= set(allowed):
		return ""
	values = ", ".join(frappe.db.escape(name) for name in scope)
	return f"(ifnull(`tab{doctype}`.`company`, '') = '' or `tab{doctype}`.`company` in ({values}))"




def get_company_print_formats():
	"""{company: {doctype: print format}} from the Print Formats section on each Company."""
	meta = frappe.get_meta("Company")
	fields = ["name", *(field for field in PRINT_FORMAT_DOCTYPES.values() if meta.has_field(field))]
	formats = {}
	for row in frappe.get_all("Company", fields=fields, ignore_permissions=True):
		chosen = {doctype: row.get(field) for doctype, field in PRINT_FORMAT_DOCTYPES.items() if row.get(field)}
		if chosen:
			formats[row.name] = chosen
	return formats


def boot_session(bootinfo):
	if frappe.session.user == "Guest":
		return
	bootinfo.company_switcher = get_switcher()
	bootinfo.company_print_formats = get_company_print_formats()
