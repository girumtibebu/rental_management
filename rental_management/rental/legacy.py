"""Import rental data kept in the pre-2.0.2 doctypes onto Item, Serial No and Stock Entry.

The old records can come from this site's own leftover tables (the v2.0.2
migration patch) or from a database backup of another site:

    bench --site <site> execute rental_management.rental.legacy.import_backup --kwargs "{'path': '/path/to/backup.sql.gz'}"

Rental Item Templates become Items and Rental Item Units become Serial Nos
with the same serial number. Units new to this site are received into the
rental store, the old movements are replayed for them as Stock Entries, and
each one gets a last Stock Entry if the replay did not leave it where its old
status says. Serials that already exist here are left alone, so running the
import again only adds what is missing.
"""

import gzip
import re

import frappe
from frappe.model.workflow import apply_workflow
from frappe.utils import (
	add_days,
	add_to_date,
	add_years,
	cint,
	flt,
	get_datetime,
	getdate,
	now_datetime,
	strip_html,
)

from rental_management.rental.item import get_serial_prefix
from rental_management.rental.setup.install import RENTAL_ITEM_GROUP, setup
from rental_management.rental.stock import get_warehouse, post_movement, set_series_counter

REPLAYED_TYPES = ("CHECK_OUT", "CHECK_IN", "MAINTENANCE_OUT", "MAINTENANCE_IN", "LOST")
STATUS_AFTER = {
	"CHECK_OUT": "At Event",
	"CHECK_IN": "Warehouse",
	"MAINTENANCE_OUT": "In Maintenance",
	"MAINTENANCE_IN": "Warehouse",
	"LOST": "Missing",
}
MOVE_TO = {
	"At Event": "CHECK_OUT",
	"In Maintenance": "MAINTENANCE_OUT",
	"Missing": "LOST",
	"Warehouse": "CHECK_IN",
}
NO_PLACE = ("", "none", "warehouse", "main warehouse", "unknown")
# {doctype: (name field, abbreviation field)} for the storage places a unit can sit in
PLACES = {
	"Zone": ("zone_name", "zone_abrivation"),
	"Aisle": ("aisle_name", "aisle_abrivation"),
	"Section": ("section_name", "section_abrivation"),
	"Level": ("level_name", "level_abrivation"),
	"Position": ("position_name", "position_abrivation"),
}
UNIT_PLACE_FIELDS = {
	"Zone": "zone",
	"Aisle": "aisle",
	"Section": "section",
	"Level": "level",
	"Position": "position",
}
TABLES = (
	"Rental Item Template",
	"Rental Item Unit",
	"Box Item Unit Child Table",
	"Rental Movement",
	"Rental Item Unit Child Table",
	"Rent Bulk Item Child Table",
	"Rent Bulk Item Child Table_2",
	"Bulk Item",
	"Rental Item Maintenance",
	"Rent Item Type",
	*PLACES,
)
# test records in the production backup of 2026-10-09
TEST_TEMPLATES = ("RNT-2026-00002", "RNT-2026-00003", "RNT-2026-00004", "RNT-2026-00256", "RNT-2026-00257")


class LegacyData:
	"""Rows of the old rental tables, keyed by doctype."""

	def __init__(self, tables):
		self.tables = {name: [frappe._dict(row) for row in rows] for name, rows in tables.items()}

	@classmethod
	def from_site(cls):
		return cls(
			{
				name: frappe.db.sql(f"select * from `tab{name}`", as_dict=True)
				for name in TABLES
				if frappe.db.table_exists(name)
			}
		)

	@classmethod
	def from_dump(cls, path):
		return cls(read_dump(path, {f"tab{name}" for name in TABLES}))

	def rows(self, doctype):
		return self.tables.get(doctype) or []

	def children(self, doctype, parent):
		if not hasattr(self, "_children"):
			self._children = {}
		if doctype not in self._children:
			index = {}
			for row in sorted(self.rows(doctype), key=lambda row: cint(row.idx)):
				index.setdefault(row.parent, []).append(row)
			self._children[doctype] = index
		return self._children[doctype].get(parent, [])


def import_backup(path, skip_templates=TEST_TEMPLATES):
	"""Import the rental records in a MariaDB backup (.sql or .sql.gz) of a site running the old app."""
	summary = import_legacy(LegacyData.from_dump(path), skip_templates)
	frappe.db.commit()  # nosemgrep: a bench execute run; the stock entries are already submitted
	print(summary)
	return summary


def import_legacy(data, skip_templates=()):
	setup()
	summary = frappe._dict()
	templates = [
		row for row in data.rows("Rental Item Template") if row.name not in set(skip_templates or ())
	]
	import_masters(data, templates)
	items = import_templates(data, templates)
	units, created = import_units(data, items)
	pending = needs_stock(units)
	statuses = receive_opening_stock(data, items, units, pending)
	replayed = replay_movements(data, items, units, statuses)
	matched = match_old_statuses(units, statuses)
	tickets = import_tickets(data, units)
	summary.update(
		items=len(items),
		units=len(units),
		serials_created=created,
		received=len(statuses),
		movements_replayed=replayed,
		status_fixes=matched,
		tickets=tickets,
		skipped_templates=sorted(
			set(skip_templates or ()) & {row.name for row in data.rows("Rental Item Template")}
		),
	)
	return summary


def ensure(doctype, name, **values):
	if name and not frappe.db.exists(doctype, name):
		frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)
	return name


def import_masters(data, templates):
	"""Types, categories, brands and storage places the old records link to."""
	for row in data.rows("Rent Item Type"):
		if not frappe.db.exists("Rent Item Type", row.name):
			code = row.type_code or row.name
			if frappe.db.exists("Rent Item Type", {"type_code": code}):
				code = f"{code}{frappe.generate_hash(length=3).upper()}"
			ensure("Rent Item Type", row.name, type_name=row.type_name or row.name, type_code=code)
	for doctype, (name_field, abbreviation_field) in PLACES.items():
		for row in data.rows(doctype):
			ensure(
				doctype,
				row.name,
				**{
					name_field: row.get(name_field) or row.name,
					abbreviation_field: row.get(abbreviation_field),
				},
			)
	for template in templates:
		ensure(
			"Item Group",
			template.item_category,
			item_group_name=template.item_category,
			parent_item_group=RENTAL_ITEM_GROUP,
		)
		ensure("Brand", template.item_brand, brand=template.item_brand)
		if template.item_type and not frappe.db.exists("Rent Item Type", template.item_type):
			ensure(
				"Rent Item Type",
				template.item_type,
				type_name=template.item_type,
				type_code=f"T{frappe.generate_hash(length=4).upper()}",
			)


def import_templates(data, templates):
	"""{template name: item code}"""
	bulk_uoms = {row.bulk_item_link: row.uom for row in data.rows("Bulk Item")}
	items = {}
	for template in sorted(templates, key=lambda row: str(row.creation)):
		kind = template.rental_item_type_box or "Unit"
		item_code = get_serial_prefix(
			template.item_model, template.item_brand, template.item_type, "Unit" if kind == "Unit" else "Box"
		)
		if not item_code:
			continue
		uom = template.uom or bulk_uoms.get(template.name)
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": item_code,
					"item_name": template.item_name or template.item_model,
					"item_group": template.item_category or RENTAL_ITEM_GROUP,
					"brand": template.item_brand,
					"stock_uom": uom if uom and frappe.db.exists("UOM", uom) else "Nos",
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


def import_units(data, items):
	"""{unit name: {serial, item_code, status, place, parent}} and how many Serial Nos were created."""
	units, created = {}, 0
	for unit in sorted(data.rows("Rental Item Unit"), key=lambda row: str(row.creation)):
		if unit.item_template not in items:
			continue
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
			places = {
				f"rental_{field}": unit.get(field)
				for doctype, field in UNIT_PLACE_FIELDS.items()
				if frappe.db.exists(doctype, unit.get(field) or "")
			}
			frappe.get_doc(
				{
					"doctype": "Serial No",
					"serial_no": serial,
					"item_code": items[unit.item_template],
					"rental_condition": unit.unit_condition or "OK",
					"description": strip_html(unit.text_editor_phqg or "") or None,
					**places,
				}
			).insert(ignore_permissions=True)
			created += 1
	link_boxes(data, units)
	continue_series(units)
	return units, created


def link_boxes(data, units):
	"""parent_box on the old unit, or the old box's contents table, becomes parent_box on the Serial No."""
	parents = {name: unit.parent for name, unit in units.items() if unit.parent and unit.parent in units}
	for row in data.rows("Box Item Unit Child Table"):
		if row.parenttype == "Rental Item Unit" and row.document_id in units and row.parent in units:
			parents.setdefault(row.document_id, row.parent)
	for child, box in parents.items():
		if not frappe.db.get_value("Serial No", units[child].serial, "parent_box"):
			frappe.db.set_value(
				"Serial No", units[child].serial, "parent_box", units[box].serial, update_modified=False
			)


def continue_series(units):
	"""New serials continue after the highest imported number of each item."""
	highest = {}
	series_of = {}
	for unit in units.values():
		if unit.item_code not in series_of:
			series_of[unit.item_code] = frappe.db.get_value("Item", unit.item_code, "serial_no_series")
		match = re.fullmatch(r"(.*)\.(#+)", series_of[unit.item_code] or "")
		number = (
			unit.serial[len(match.group(1)) :] if match and unit.serial.startswith(match.group(1)) else ""
		)
		if number.isdigit():
			highest[match.group(1)] = max(highest.get(match.group(1), 0), int(number))
	for prefix, value in highest.items():
		set_series_counter(prefix, value)


def needs_stock(units):
	"""Serials that have never been in stock here: these get the opening receipt and the replay."""
	serials = [unit.serial for unit in units.values() if not unit.disabled]
	if not serials:
		return set()
	stocked = set(
		frappe.get_all(
			"Serial No", filters={"name": ["in", serials], "warehouse": ["is", "set"]}, pluck="name"
		)
	) | set(
		frappe.db.sql_list(
			"select distinct sbe.serial_no from `tabSerial and Batch Entry` sbe where sbe.serial_no in %(serials)s",
			{"serials": serials},
		)
	)
	return set(serials) - stocked


def opening_time(data, units):
	stamps = [unit.creation for unit in units.values()] + [row.creation for row in data.rows("Bulk Item")]
	first = min((get_datetime(stamp) for stamp in stamps if stamp), default=now_datetime())
	return str(first).split(".")[0]


def receive_opening_stock(data, items, units, pending):
	"""Receive the new units, one Stock Entry per item, and bulk quantities into the rental store."""
	posting = opening_time(data, units)
	if pending:
		ensure_fiscal_years(posting)
	by_item = {}
	for unit in units.values():
		if unit.serial in pending:
			by_item.setdefault(unit.item_code, []).append(unit.serial)
	for serials in by_item.values():
		post_movement("PURCHASE", serials=serials, remarks="Opening rental stock", posting_datetime=posting)
	stocked_items = set(
		frappe.db.sql_list("select distinct item_code from `tabStock Ledger Entry` where is_cancelled = 0")
	)
	bulk = [
		(items[row.bulk_item_link], flt(row.quantity))
		for row in data.rows("Bulk Item")
		if row.status != "Retired"
		and row.bulk_item_link in items
		and flt(row.quantity) > 0
		and items[row.bulk_item_link] not in stocked_items
	]
	if bulk:
		post_movement("PURCHASE", bulk=bulk, remarks="Opening rental stock", posting_datetime=posting)
	return {serial: "Warehouse" for serial in pending}


def ensure_fiscal_years(posting):
	"""Add fiscal years, shaped like the earliest one, back to the date old stock is posted on."""
	date = getdate(posting)
	years = frappe.get_all(
		"Fiscal Year",
		filters={"disabled": 0},
		fields=["name", "year_start_date"],
		order_by="year_start_date asc",
	)
	if not years or years[0].year_start_date <= date:
		return
	companies = frappe.get_all("Fiscal Year Company", filters={"parent": years[0].name}, pluck="company")
	start = years[0].year_start_date
	while start > date:
		end, start = add_days(start, -1), add_years(start, -1)
		name = f"{start.year}-{end.year}" if start.year != end.year else str(start.year)
		if frappe.db.exists("Fiscal Year", name):
			name = f"{name} ({start})"
		frappe.get_doc(
			{
				"doctype": "Fiscal Year",
				"year": name,
				"year_start_date": start,
				"year_end_date": end,
				"companies": [{"company": row} for row in companies],
			}
		).insert(ignore_permissions=True)


def movement_serials(data, movement, units, statuses):
	"""The serials of an old movement that the replay can actually move, boxes with their contents."""
	target = STATUS_AFTER[movement.transaction_type]
	names = [row.unit_doc_id for row in data.children("Rental Item Unit Child Table", movement.name)]
	names += [name for name, unit in units.items() if unit.parent in names]
	serials = []
	for name in dict.fromkeys(names):
		unit = units.get(name)
		if (
			unit
			and unit.serial in statuses
			and statuses[unit.serial] != target
			and can_move(movement.transaction_type, statuses[unit.serial])
		):
			serials.append(unit.serial)
	return serials


def can_move(movement_type, status):
	if movement_type == "CHECK_OUT":
		return status == "Warehouse"
	if movement_type == "MAINTENANCE_IN":
		return status == "In Maintenance"
	return True


def movement_bulk(data, movement, items, received_bulk):
	rows = [
		(row.item_template, row.qty) for row in data.children("Rent Bulk Item Child Table_2", movement.name)
	]
	rows += [
		(row.item_template, row.amount) for row in data.children("Rent Bulk Item Child Table", movement.name)
	]
	return [
		(items[template], flt(qty))
		for template, qty in rows
		if items.get(template) in received_bulk and flt(qty) > 0
	]


def replay_movements(data, items, units, statuses):
	received_bulk = {
		item_code
		for item_code in items.values()
		if frappe.db.get_value("Item", item_code, "rental_tracking") == "Bulk"
	}
	last = None
	replayed = 0
	for movement in sorted(data.rows("Rental Movement"), key=lambda row: str(row.creation)):
		if cint(movement.docstatus) == 2 or movement.transaction_type not in REPLAYED_TYPES:
			continue
		serials = movement_serials(data, movement, units, statuses)
		bulk = (
			movement_bulk(data, movement, items, received_bulk)
			if movement.transaction_type in ("CHECK_OUT", "CHECK_IN")
			else []
		)
		if not serials and not bulk:
			continue
		# one second apart at least: ERPNext orders a serial's moves by posting time
		posting = get_datetime(str(movement.creation).split(".")[0])
		if last and posting <= last:
			posting = add_to_date(last, seconds=1)
		last = posting
		try:
			post_movement(
				movement.transaction_type,
				serials=serials,
				bulk=bulk,
				venue=venue_for(movement.transaction_type, movement.to_location),
				issued_to=movement.issued_to,
				received_by=movement.recieved_by,
				remarks=f"Migrated from {movement.name}. {strip_html(movement.text_editor_fdyh or '')}".strip(),
				posting_datetime=str(posting),
				sources=sources_of(serials, statuses),
			)
		except Exception:
			print(
				f"Replaying {movement.name} ({movement.transaction_type} at {posting}) failed for {serials} {bulk}"
			)
			print_ledger(serials)
			raise
		replayed += 1
		if replayed % 25 == 0:
			print(f"Replayed {replayed} movements, up to {movement.name} at {posting}")
		for serial in serials:
			statuses[serial] = STATUS_AFTER[movement.transaction_type]
		check_ledger(movement, serials, statuses)
	return replayed


def check_ledger(movement, serials, statuses):
	"""Stop at the first movement after which the stock ledger disagrees with where the import has the units."""
	items = {
		row.name: row.item_code
		for row in frappe.get_all(
			"Serial No", filters={"name": ["in", serials]}, fields=["name", "item_code"]
		)
	}
	for item_code in set(items.values()):
		item_serials = frappe.get_all("Serial No", filters={"item_code": item_code}, pluck="name")
		expected = {}
		for serial in item_serials:
			if serial in statuses:
				warehouse = get_warehouse(statuses[serial])
				expected[warehouse] = expected.get(warehouse, 0) + 1
		for warehouse, count in expected.items():
			actual = frappe.db.sql(
				"""select qty_after_transaction from `tabStock Ledger Entry`
				where item_code = %s and warehouse = %s and is_cancelled = 0
				order by posting_datetime desc, creation desc limit 1""",
				(item_code, warehouse),
			)
			actual = flt(actual[0][0]) if actual else 0
			if actual != count:
				print(
					f"After {movement.name}: {item_code} in {warehouse} is {actual} in the ledger, {count} expected"
				)
				print_ledger(list(item_serials))
				frappe.throw(f"Stock ledger out of step with the import after {movement.name}")


def print_ledger(serials):
	"""What the stock ledger and the Serial Nos say about these serials' items, to explain a failed replay."""
	items = sorted(set(frappe.get_all("Serial No", filters={"name": ["in", serials]}, pluck="item_code")))
	print("repost entries", frappe.db.count("Repost Item Valuation", {"docstatus": 1}))
	for row in frappe.db.sql(
		"""select sle.item_code, sle.warehouse, sle.posting_datetime, sle.posting_date, sle.posting_time,
			sle.actual_qty, sle.qty_after_transaction, sle.voucher_no, sle.is_cancelled, sle.creation, se.remarks
		from `tabStock Ledger Entry` sle left join `tabStock Entry` se on se.name = sle.voucher_no
		where sle.item_code in %(items)s order by sle.posting_datetime, sle.creation""",
		{"items": items or [""]},
		as_dict=True,
	):
		print("sle", *row.values())


def sources_of(serials, statuses):
	"""Take each serial from the warehouse the import has it in, not from Serial No.warehouse.

	ERPNext can be behind on Serial No.warehouse while backdated entries are reposted.
	"""
	return {serial: get_warehouse(statuses[serial]) for serial in serials}


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
		post_movement(
			movement_type,
			serials=serials,
			venue=venue,
			remarks="Migrated: matches the status the old unit record had",
			sources=sources_of(serials, statuses),
		)
	return len(groups)


def import_tickets(data, units):
	"""Old repair tickets pointed at a Rental Item Unit; the imported ones point at its Serial No."""
	by_serial = {unit.serial: unit for unit in units.values()}
	count = 0
	for ticket in sorted(data.rows("Rental Item Maintenance"), key=lambda row: str(row.creation)):
		if cint(ticket.docstatus) == 2:
			continue
		unit = (
			units.get(ticket.unit_serial_number)
			or by_serial.get(ticket.serial_number)
			or by_serial.get(ticket.unit_serial_number)
		)
		if not unit:
			continue
		if ticket.get("serial_no") == unit.serial and frappe.db.exists(
			"Rental Item Maintenance", ticket.name
		):
			continue  # this site's own ticket, already pointing at the serial
		if frappe.db.exists(
			"Rental Item Maintenance",
			{
				"serial_no": unit.serial,
				"issue_description": ticket.issue_description,
				"unit_condition": ticket.unit_condition,
			},
		):
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Rental Item Maintenance",
				"serial_no": unit.serial,
				"item_name": frappe.db.get_value("Item", unit.item_code, "item_name"),
				"unit_condition": ticket.unit_condition,
				"issue_description": ticket.issue_description,
				"maintenance_result": ticket.maintenance_result,
				"submited_by": ticket.submited_by,
				"maintained_by": ticket.maintained_by,
			}
		)
		doc.insert(ignore_permissions=True)
		if ticket.workflow_state in ("In Repair", "Complete"):
			apply_workflow(doc, "Send To Maintenance")
		if ticket.workflow_state == "Complete":
			doc = frappe.get_doc("Rental Item Maintenance", doc.name)
			doc.final_condition = (
				ticket.final_condition if ticket.final_condition in ("OK", "Scrapped") else "OK"
			)
			doc.save(ignore_permissions=True)
			apply_workflow(frappe.get_doc("Rental Item Maintenance", doc.name), "Complete")
		count += 1
	return count


def read_dump(path, wanted):
	"""{table: [row dict]} for the `wanted` tables of a mysqldump/mariadb-dump file."""
	opener = gzip.open if str(path).endswith(".gz") else open
	columns, rows, current = {}, {}, None
	with opener(path, "rt", encoding="utf8", errors="replace") as dump:
		for line in dump:
			match = re.match(r"CREATE TABLE `([^`]*)`", line)
			if match:
				current = match.group(1)
				columns[current] = []
				continue
			if current and line.startswith("  `"):
				columns[current].append(line.split("`")[1])
				continue
			match = re.match(r"INSERT INTO `([^`]*)` (?:\(([^)]*)\) )?VALUES", line)
			if not match or match.group(1) not in wanted:
				continue
			table = match.group(1)
			statement = [line[match.end() :]]
			while not statement[-1].rstrip().endswith(";"):
				statement.append(next(dump))
			names = (
				[name.strip(" `") for name in match.group(2).split(",")] if match.group(2) else columns[table]
			)
			for values in parse_values("".join(statement)):
				rows.setdefault(table, []).append(dict(zip(names, values, strict=True)))
	return {table[3:]: table_rows for table, table_rows in rows.items()}


ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", "Z": "\x1a"}


def parse_values(text):
	"""Rows of an INSERT ... VALUES (...),(...); body, as lists of str or None."""
	rows, i, n = [], 0, len(text)
	while i < n:
		while i < n and text[i] in " ,\r\n":
			i += 1
		if i >= n or text[i] == ";":
			break
		i += 1  # (
		row = []
		while True:
			if text[i] == "'":
				i += 1
				chunk = []
				while True:
					char = text[i]
					if char == "\\":
						chunk.append(ESCAPES.get(text[i + 1], text[i + 1]))
						i += 2
					elif char == "'" and text[i + 1] == "'":
						chunk.append("'")
						i += 2
					elif char == "'":
						i += 1
						break
					else:
						chunk.append(char)
						i += 1
				row.append("".join(chunk))
			else:
				j = i
				while text[j] not in ",)":
					j += 1
				token = text[i:j].strip()
				row.append(None if token == "NULL" else token)
				i = j
			if text[i] == ",":
				i += 1
				continue
			i += 1  # )
			break
		rows.append(row)
	return rows
