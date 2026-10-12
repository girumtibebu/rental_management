import frappe

from rental_management.rental.setup.custom_fields import setup_custom_fields
from rental_management.rental.stock import SETTINGS, WAREHOUSE_FIELDS

APP = "rental_management"
RENTAL_ITEM_GROUP = "Rental"
# Desk pages the app shipped before v2.0.2; they point at doctypes that no longer exist
LEGACY_WORKSPACES = ("Rental", "Rental Home", "Rental Management")
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
    # rental units are serial numbers, which ERPNext only accepts with this switched on
    frappe.db.set_single_value("Stock Settings", "enable_serial_and_batch_no_for_item", 1)
    setup_desktop_icon()


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


def setup_desktop_icon():
    """Make the Desk icon open the /rental app and drop the old rental workspaces it used to open."""
    workspaces = set(LEGACY_WORKSPACES) | set(frappe.get_all("Workspace", filters={"module": "Rental"}, pluck="name"))
    for name in workspaces:
        frappe.delete_doc("Workspace", name, ignore_permissions=True, force=True, ignore_missing=True)
    if frappe.db.table_exists("Workspace Sidebar"):
        for name in LEGACY_WORKSPACES:
            frappe.delete_doc("Workspace Sidebar", name, ignore_permissions=True, force=True, ignore_missing=True)

    if not frappe.db.table_exists("Desktop Icon"):
        return
    label = frappe.get_hooks("app_title", app_name=APP)[0]
    screen = frappe.get_hooks("add_to_apps_screen", app_name=APP)[0]
    # icons for the deleted workspaces (removed directly: the per-icon trash hook clears caches each time)
    frappe.db.delete("Desktop Icon", {"name": ["!=", label], "app": APP})
    frappe.db.delete("Desktop Icon", {"name": ["!=", label], "link_to": ["in", list(workspaces)]})
    values = {
        "icon_type": "App",
        "app": APP,
        "link_type": "External",
        "link": screen["route"],
        "link_to": None,
        "logo_url": screen["logo"],
        "parent_icon": None,
        "hidden": 0,
    }
    if frappe.db.exists("Desktop Icon", label):
        frappe.db.set_value("Desktop Icon", label, values)
    else:
        frappe.get_doc({"doctype": "Desktop Icon", "label": label, **values}).insert(
            ignore_permissions=True, ignore_links=True
        )

    from frappe.desk.doctype.desktop_icon import desktop_icon

    if hasattr(desktop_icon, "clear_every_users_desktop_icons"):
        desktop_icon.clear_every_users_desktop_icons()
