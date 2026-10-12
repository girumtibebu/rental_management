"""Move the old rental doctypes onto Item, Serial No and Stock Entry.

Rental Item Templates become Items, Rental Item Units become Serial Nos with
the same serial number, and the old movements are replayed as Stock Entries
so the stock ledger carries the history. Each serial then gets one more
Stock Entry if the replay did not end in the warehouse its old status names.
The old tables are left in place and can be dropped later.
"""

import re

import frappe
from frappe.utils import cint, flt, now_datetime, strip_html

from rental_management.rental.item import get_serial_prefix
from rental_management.rental.setup.install import RENTAL_ITEM_GROUP, setup
from rental_management.rental.stock import post_movement, set_series_counter

REPLAYED_TYPES = ("CHECK_OUT", "CHECK_IN", "MAINTENANCE_OUT", "MAINTENANCE_IN", "LOST")
STATUS_AFTER = {
    "CHECK_OUT": "At Event",
    "CHECK_IN": "Warehouse",
    "MAINTENANCE_OUT": "In Maintenance",
    "MAINTENANCE_IN": "Warehouse",
    "LOST": "Missing",
}
MOVE_TO = {"At Event": "CHECK_OUT", "In Maintenance": "MAINTENANCE_OUT", "Missing": "LOST", "Warehouse": "CHECK_IN"}
NO_PLACE = ("", "none", "warehouse", "main warehouse", "unknown")


def execute():
    if not frappe.db.table_exists("Rental Item Template"):
        return
    setup()
    items = migrate_templates()
    units = migrate_units(items)
    if not frappe.db.exists("Stock Entry", {"rental_movement_type": "PURCHASE", "remarks": ["like", "Opening rental stock%"]}):
        statuses = receive_opening_stock(items, units)
        replay_movements(items, units, statuses)
        match_old_statuses(units, statuses)
    migrate_tickets(units)
    frappe.db.delete("Print Format", {"doc_type": "Rental Movement"})


def sql(query, *args):
    return frappe.db.sql(query, *args, as_dict=True)


def ensure(doctype, name, **values):
    if not frappe.db.exists(doctype, name):
        frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)
    return name


def migrate_templates():
    """{template name: item code}"""
    bulk_uoms = {row.bulk_item_link: row.uom for row in sql("select bulk_item_link, uom from `tabBulk Item`")}
    items = {}
    for template in sql("select * from `tabRental Item Template` order by creation"):
        kind = template.rental_item_type_box or "Unit"
        item_code = get_serial_prefix(template.item_model, template.item_brand, template.item_type, "Unit" if kind == "Unit" else "Box")
        if template.item_category:
            ensure("Item Group", template.item_category, item_group_name=template.item_category, parent_item_group=RENTAL_ITEM_GROUP)
        if template.item_brand:
            ensure("Brand", template.item_brand, brand=template.item_brand)
        if not frappe.db.exists("Item", item_code):
            frappe.get_doc(
                {
                    "doctype": "Item",
                    "item_code": item_code,
                    "item_name": template.item_name or template.item_model,
                    "item_group": template.item_category or RENTAL_ITEM_GROUP,
                    "brand": template.item_brand,
                    "stock_uom": template.uom or bulk_uoms.get(template.name) or "Nos",
                    "image": template.image,
                    "description": strip_html(template.text_editor_hdml or "") or template.item_name,
                    "is_rental_item": 1,
                    "rental_tracking": kind,
                    "rental_model": template.item_model,
                    "rental_item_type": template.item_type,
                    "rental_serial_digits": str(template.suffix or "3"),
                    "rental_size": template.size,
                }
            ).insert(ignore_permissions=True)
        items[template.name] = item_code
    return items


def migrate_units(items):
    """{unit name: {serial, item_code, status, place, parent}}"""
    units = {}
    rows = sql("select * from `tabRental Item Unit` where ifnull(item_template, '') != '' order by creation")
    for unit in rows:
        serial = (unit.unit_serial_number or unit.name).strip()
        units[unit.name] = frappe._dict(
            serial=serial,
            item_code=items[unit.item_template],
            status=unit.movement_status or "Warehouse",
            place=unit.unit_location,
            parent=unit.parent_box,
            disabled=cint(unit.disabled),
            creation=unit.creation,
        )
        if not frappe.db.exists("Serial No", serial):
            frappe.get_doc(
                {
                    "doctype": "Serial No",
                    "serial_no": serial,
                    "item_code": items[unit.item_template],
                    "rental_condition": unit.unit_condition or "OK",
                    "rental_zone": unit.zone,
                    "rental_section": unit.section,
                    "rental_level": unit.level,
                    "rental_position": unit.position,
                    "description": strip_html(unit.text_editor_phqg or "") or None,
                }
            ).insert(ignore_permissions=True)
    link_boxes(units)
    continue_series(units)
    return units


def link_boxes(units):
    """parent_box on the old unit, or the old box's contents table, becomes parent_box on the Serial No."""
    parents = {name: unit.parent for name, unit in units.items() if unit.parent and unit.parent in units}
    for row in sql("select parent, document_id from `tabBox Item Unit Child Table` where parenttype = 'Rental Item Unit'"):
        if row.document_id in units and row.parent in units:
            parents.setdefault(row.document_id, row.parent)
    for child, box in parents.items():
        frappe.db.set_value("Serial No", units[child].serial, "parent_box", units[box].serial, update_modified=False)


def continue_series(units):
    """New serials continue after the highest migrated number of each item."""
    highest = {}
    for unit in units.values():
        series = frappe.db.get_value("Item", unit.item_code, "serial_no_series")
        match = re.fullmatch(r"(.*)\.(#+)", series or "")
        number = unit.serial[len(match.group(1)) :] if match and unit.serial.startswith(match.group(1)) else ""
        if number.isdigit():
            highest[match.group(1)] = max(highest.get(match.group(1), 0), int(number))
    for prefix, value in highest.items():
        set_series_counter(prefix, value)


def opening_time(units):
    first = min([unit.creation for unit in units.values()] + [row.creation for row in sql("select creation from `tabBulk Item`")] or [now_datetime()])
    return str(first).split(".")[0]


def receive_opening_stock(items, units):
    """Receive every active unit and the bulk quantities into the rental store, dated when they were created."""
    serials = [unit.serial for unit in units.values() if not unit.disabled]
    bulk = [
        (items[row.bulk_item_link], flt(row.quantity))
        for row in sql("select bulk_item_link, quantity from `tabBulk Item` where status != 'Retired'")
        if row.bulk_item_link in items and flt(row.quantity) > 0
    ]
    if serials or bulk:
        post_movement("PURCHASE", serials=serials, bulk=bulk, remarks="Opening rental stock", posting_datetime=opening_time(units))
    return {unit.serial: "Warehouse" for unit in units.values() if not unit.disabled}


def movement_serials(movement, units, statuses):
    """The serials of an old movement that the replay can actually move, boxes with their contents."""
    target = STATUS_AFTER[movement.transaction_type]
    names = [row.unit_doc_id for row in sql("select unit_doc_id from `tabRental Item Unit Child Table` where parent = %s order by idx", movement.name)]
    names += [name for name, unit in units.items() if unit.parent in names]
    serials = []
    for name in dict.fromkeys(names):
        unit = units.get(name)
        if unit and unit.serial in statuses and statuses[unit.serial] != target and can_move(movement.transaction_type, statuses[unit.serial]):
            serials.append(unit.serial)
    return serials


def can_move(movement_type, status):
    if movement_type == "CHECK_OUT":
        return status == "Warehouse"
    if movement_type == "MAINTENANCE_IN":
        return status == "In Maintenance"
    return True


def movement_bulk(movement, items):
    rows = sql("select item_template, qty from `tabRent Bulk Item Child Table_2` where parent = %s", movement.name)
    rows += sql("select item_template, amount as qty from `tabRent Bulk Item Child Table` where parent = %s", movement.name)
    return [(items[row.item_template], flt(row.qty)) for row in rows if row.item_template in items and flt(row.qty) > 0]


def replay_movements(items, units, statuses):
    for movement in sql("select * from `tabRental Movement` where docstatus < 2 order by creation"):
        if movement.transaction_type not in REPLAYED_TYPES:
            continue
        serials = movement_serials(movement, units, statuses)
        bulk = movement_bulk(movement, items) if movement.transaction_type in ("CHECK_OUT", "CHECK_IN") else []
        if not serials and not bulk:
            continue
        post_movement(
            movement.transaction_type,
            serials=serials,
            bulk=bulk,
            venue=venue_for(movement.transaction_type, movement.to_location),
            issued_to=movement.issued_to,
            received_by=movement.recieved_by,
            remarks=f"Migrated from {movement.name}. {strip_html(movement.text_editor_fdyh or '')}".strip(),
            posting_datetime=str(movement.creation).split(".")[0],
        )
        for serial in serials:
            statuses[serial] = STATUS_AFTER[movement.transaction_type]


def venue_for(movement_type, place):
    if movement_type not in ("CHECK_OUT", "MAINTENANCE_OUT"):
        return None
    if (place or "").strip().lower() in NO_PLACE:
        return "Repair Shop" if movement_type == "MAINTENANCE_OUT" else "Unknown venue"
    return place.strip()


def match_old_statuses(units, statuses):
    """One Stock Entry per old status and place for the serials the replay left somewhere else."""
    groups = {}
    for unit in units.values():
        if unit.serial in statuses and statuses[unit.serial] != unit.status and unit.status in MOVE_TO:
            movement_type = MOVE_TO[unit.status]
            groups.setdefault((movement_type, venue_for(movement_type, unit.place)), []).append(unit.serial)
    for (movement_type, venue), serials in groups.items():
        post_movement(movement_type, serials=serials, venue=venue, remarks="Migrated: matches the status the old unit record had")


def migrate_tickets(units):
    """Tickets pointed at Rental Item Unit; they now point at the Serial No."""
    if not frappe.db.has_column("Rental Item Maintenance", "unit_serial_number"):
        return
    for ticket in sql("select name, unit_serial_number from `tabRental Item Maintenance` where ifnull(serial_no, '') = ''"):
        unit = units.get(ticket.unit_serial_number)
        if unit:
            item_name = frappe.db.get_value("Item", unit.item_code, "item_name")
            frappe.db.set_value("Rental Item Maintenance", ticket.name, {"serial_no": unit.serial, "item_name": item_name}, update_modified=False)
