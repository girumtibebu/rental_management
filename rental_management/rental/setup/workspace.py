"""Create an extra Rental Workspace (for example one per company) with its own rental warehouses.

Run it from a bench, once per workspace:

    bench --site <site> execute rental_management.rental.setup.workspace.create_workspace \\
        --kwargs "{'workspace_name': '<name>', 'company': '<company>', \\
        'item_group': '<item group>', 'main_store': '<store>'}"

It is safe to run again: an existing workspace is left as it is.
"""

import frappe

from rental_management.rental.setup.install import WAREHOUSE_NAMES, get_or_create_warehouse, get_rental_warehouse_group
from rental_management.rental.stock import WORKSPACE


def create_workspace(
    workspace_name,
    company,
    mode="Bulk First",
    item_group=None,
    main_store=None,
    cost_center=None,
    item_code_series=None,
    hold_days=14,
    apply_defaults=False,
):
    """Create the workspace and four new rental warehouses under the company's "Rental" group."""
    if frappe.db.exists(WORKSPACE, workspace_name):
        return workspace_name
    parent = get_rental_warehouse_group(company)
    warehouses = {}
    for field, label in WAREHOUSE_NAMES.items():
        warehouse = get_or_create_warehouse(label, company, parent)
        if frappe.db.exists(WORKSPACE, {field: warehouse}):
            # another workspace of this company already uses that name: make a dedicated one
            warehouse = get_or_create_warehouse(f"{workspace_name} {label}", company, parent)
        warehouses[field] = warehouse
    doc = frappe.get_doc(
        {
            "doctype": WORKSPACE,
            "workspace_name": workspace_name,
            "company": company,
            "mode": mode,
            "enabled": 1,
            "is_default": 0,
            "hold_days": hold_days,
            "item_group": item_group,
            "main_store_warehouse": main_store,
            "cost_center": cost_center,
            "item_code_series": item_code_series,
            **warehouses,
        }
    ).insert(ignore_permissions=True)
    if apply_defaults:
        from rental_management.ui.catalog import apply_workspace_defaults

        frappe.logger().info(apply_workspace_defaults(doc.name))
    frappe.db.commit()
    return doc.name
