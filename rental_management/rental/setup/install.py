import frappe

from rental_management.rental.setup.custom_fields import setup_custom_fields
from rental_management.rental.stock import SETTINGS, WAREHOUSE_FIELDS

RENTAL_ITEM_GROUP = "Rental"
WAREHOUSE_NAMES = {
    "store_warehouse": "Rental Store",
    "event_warehouse": "Rental At Event",
    "repair_warehouse": "Rental Repair",
    "missing_warehouse": "Rental Missing",
}


def after_install():
    setup()


def after_migrate():
    setup()


def setup():
    setup_custom_fields()
    setup_item_group()
    setup_settings()


def setup_item_group():
    """Rental categories are Item Groups under one "Rental" group."""
    if not frappe.db.exists("Item Group", RENTAL_ITEM_GROUP):
        frappe.get_doc(
            {"doctype": "Item Group", "item_group_name": RENTAL_ITEM_GROUP, "parent_item_group": get_root_item_group(), "is_group": 1}
        ).insert(ignore_permissions=True)
    elif not frappe.db.get_value("Item Group", RENTAL_ITEM_GROUP, "is_group"):
        frappe.db.set_value("Item Group", RENTAL_ITEM_GROUP, "is_group", 1)


def get_root_item_group():
    return frappe.db.get_value("Item Group", {"is_group": 1, "parent_item_group": ["is", "not set"]}, "name")


def setup_settings():
    """Fill the empty Rental Settings fields: the default company and its four rental warehouses."""
    settings = frappe.get_single(SETTINGS)
    settings.company = settings.company or frappe.defaults.get_global_default("company")
    if not settings.company:
        return
    parent = get_rental_warehouse_group(settings.company)
    for field in WAREHOUSE_FIELDS.values():
        if not settings.get(field):
            settings.set(field, get_or_create_warehouse(WAREHOUSE_NAMES[field], settings.company, parent))
    settings.flags.ignore_permissions = True
    settings.save()


def get_rental_warehouse_group(company):
    root = frappe.db.get_value("Warehouse", {"company": company, "is_group": 1, "parent_warehouse": ["is", "not set"]}, "name")
    return get_or_create_warehouse("Rental", company, root, is_group=1)


def get_or_create_warehouse(warehouse_name, company, parent, is_group=0):
    existing = frappe.db.get_value("Warehouse", {"warehouse_name": warehouse_name, "company": company}, "name")
    if existing:
        return existing
    warehouse = frappe.get_doc(
        {"doctype": "Warehouse", "warehouse_name": warehouse_name, "company": company, "parent_warehouse": parent, "is_group": is_group}
    )
    warehouse.insert(ignore_permissions=True)
    return warehouse.name
