"""Item requests: what other teams (e.g. the planner's tech BOMs) ask the warehouse for, one per event."""

import frappe
from frappe import _

from rental_management.ui.common import like, paging

REQUEST = "Item Request"
FIELDS = ["name", "title", "status", "needs_review", "version", "reference_doctype", "reference_name", "customer", "location", "start_date", "end_date", "modified"]
# the request statuses the warehouse sets by hand; lists are answered one by one (answer, accept_all)
WAREHOUSE_STATUSES = ("Checked out", "Returned")


@frappe.whitelist()
def list_requests(status=None, search=None, page=1, page_length=25):
	"""status: 'todo' (pending, new or changed), a status, or empty for all. Soonest event first."""
	start, length = paging(page, page_length)
	filters = {"status": "Pending"} if status == "todo" else ({"status": status} if status else {})
	or_filters = None
	if search:
		pattern = like(search)
		or_filters = [["title", "like", pattern], ["customer", "like", pattern], ["location", "like", pattern], ["name", "like", pattern]]
	# shortcut: requests are not split by rental workspace; filter by company when a second workspace takes requests
	rows = frappe.get_list(
		REQUEST, filters=filters, or_filters=or_filters, fields=FIELDS, order_by="start_date asc, modified desc", limit_start=start, limit_page_length=length
	)
	total = len(frappe.get_list(REQUEST, filters=filters, or_filters=or_filters, pluck="name", limit_page_length=0))
	counts = line_counts([r.name for r in rows])
	for row in rows:
		row.update(counts.get(row.name, {"sections": 0, "lines": 0, "changed": 0}))
	return {"rows": rows, "total": total, "todo": frappe.db.count(REQUEST, {"status": "Pending"})}


def line_counts(names):
	if not names:
		return {}
	out = {}
	for parent, sections in frappe.db.sql("select parent, count(*) from `tabItem Request Section` where parent in %s group by parent", [names]):
		out[parent] = {"sections": sections, "lines": 0, "changed": 0}
	for parent, lines, changed in frappe.db.sql("select parent, count(*), sum(changed) from `tabItem Request Line` where parent in %s group by parent", [names]):
		out.setdefault(parent, {"sections": 0}).update(lines=lines, changed=int(changed or 0))
	return out


@frappe.whitelist()
def get_request(name):
	doc = frappe.get_doc(REQUEST, name)
	doc.check_permission("read")
	lines = {}
	for line in doc.lines:
		lines.setdefault(line.section, []).append({k: line.get(k) for k in ("name", "item", "item_code", "qty", "unit", "note", "changed")})
	return {
		"request": {**{k: doc.get(k) for k in FIELDS}, "accepted_by": doc.accepted_by, "accepted_at": doc.accepted_at, "reject_reason": doc.reject_reason, "warehouse_note": doc.warehouse_note, "requested_by": doc.requested_by},
		"sections": [
			{k: s.get(k) for k in ("source", "title", "department", "icon", "status", "reject_reason", "answered_by", "answered_at", "changed", "lines_removed")}
			| {"removed": [r for r in (s.removed or "").split("\n") if r], "lines": lines.get(s.source, [])}
			for s in doc.sections
		],
		"versions": [{k: v.get(k) for k in ("version", "section", "summary", "sent_by", "sent_at")} for v in reversed(doc.versions)],
		"movements": frappe.get_all(
			"Stock Entry",
			filters={"rental_item_request": name, "docstatus": 1},
			fields=["name", "rental_movement_type as transaction_type", "posting_date", "rental_venue as venue", "rental_issued_to as issued_to", "rental_received_by as received_by"],
			order_by="posting_date desc, posting_time desc",
		),
		"can_write": doc.has_permission("write"),
	}


@frappe.whitelist()
def requests_for_movement(transaction_type):
	"""The requests a check-out (accepted ones) or a check-in (checked-out ones) can be linked to, soonest event first."""
	from rental_management.ui.movements import REQUEST_STATUSES

	statuses = REQUEST_STATUSES.get(transaction_type)
	if not statuses:
		return []
	return frappe.get_list(REQUEST, filters={"status": ["in", statuses]}, fields=["name", "title", "status", "start_date", "location"], order_by="start_date asc", limit_page_length=100)


@frappe.whitelist(methods=["POST"])
def answer(name, section, status, reason=None):
	"""Accept or reject one list of the request."""
	doc = frappe.get_doc(REQUEST, name)
	doc.check_permission("write")
	doc.answer(section, status, reason)
	doc.save()
	return get_request(name)


@frappe.whitelist(methods=["POST"])
def accept_all(name):
	"""Accept every list still waiting for an answer."""
	doc = frappe.get_doc(REQUEST, name)
	doc.check_permission("write")
	waiting = [s.source for s in doc.sections if s.status == "Pending"]
	if not waiting:
		frappe.throw(_("No list is waiting for an answer."))
	for source in waiting:
		doc.answer(source, "Accepted")
	doc.save()
	return get_request(name)


@frappe.whitelist(methods=["POST"])
def set_status(name, status, note=None):
	"""The steps after the answers: Checked out, Returned."""
	if status not in WAREHOUSE_STATUSES:
		frappe.throw(_("{0} is not a status the warehouse sets.").format(status))
	doc = frappe.get_doc(REQUEST, name)
	doc.check_permission("write")
	doc.status = status
	if note is not None:
		doc.warehouse_note = note
	doc.save()
	return get_request(name)
