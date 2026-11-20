import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

LINE_KEYS = ("item", "qty", "unit", "note")
CLOSED = ("Returned", "Cancelled")
AFTER_ANSWER = ("Checked out", "Returned", "Cancelled")  # set by hand or by movements; the lists' answers no longer drive it


class ItemRequest(Document):
	"""Items another app (e.g. the project planner) asks the warehouse for, for one event.

	The requesting app sends one section (a list, e.g. Audio BOM) at a time with send_section;
	each send is a new version and puts that section back to Pending. The warehouse answers
	each section: accepting keeps a snapshot of its lines, and a later send marks what changed
	against it; rejecting needs a reason, and the requester may change the list and send again.
	The request's status follows its sections: Pending while one waits, then Accepted when at
	least one is accepted, else Rejected.
	"""

	def validate(self):
		for s in self.sections:
			s.status = s.status or "Pending"
			if s.status == "Rejected" and not (s.reject_reason or "").strip():
				frappe.throw(_("Say why {0} is rejected.").format(frappe.bold(s.title)))
		self.follow_sections()

	def follow_sections(self):
		self.needs_review = int(any(s.changed for s in self.sections if s.status == "Pending"))
		if self.status in AFTER_ANSWER or not self.sections:
			return
		states = {s.status for s in self.sections}
		self.status = "Pending" if "Pending" in states else ("Accepted" if "Accepted" in states else "Rejected")
		if self.status == "Accepted" and self.has_value_changed("status"):
			self.accepted_by, self.accepted_at = frappe.session.user, now_datetime()

	def section(self, source):
		row = next((s for s in self.sections if s.source == source), None)
		if not row:
			frappe.throw(_("This request has no list {0}.").format(source))
		return row

	def answer(self, source, status, reason=None):
		"""The warehouse's answer for one list."""
		if status not in ("Accepted", "Rejected"):
			frappe.throw(_("A list is accepted or rejected."))
		row = self.section(source)
		row.update({"status": status, "answered_by": frappe.session.user, "answered_at": now_datetime(), "reject_reason": (reason or "").strip() or None})
		if status == "Accepted":
			lines = [l for l in self.lines if l.section == source]
			row.accepted_lines = frappe.as_json({l.source: [l.get(k) for k in LINE_KEYS] for l in lines}, indent=None)
			row.reject_reason = None
			row.changed, row.lines_removed, row.removed = 0, 0, None
			for l in lines:
				l.changed = 0

	def add_version(self, section, summary, user):
		self.version = (self.version or 0) + 1
		self.append("versions", {"version": self.version, "section": section, "summary": summary, "sent_by": user, "sent_at": now_datetime()})


def open_request(reference_doctype, reference_name):
	return frappe.db.get_value(
		"Item Request", {"reference_doctype": reference_doctype, "reference_name": reference_name, "status": ["not in", CLOSED]}, order_by="creation desc"
	)


def send_section(reference_doctype, reference_name, header, section, lines, user=None):
	"""Called by the requesting app when someone sends a list: add or replace its section as a new version.

	header: title, customer, location, start_date, end_date. section: source (the app's id
	for the list), title, department, icon. lines: source, item, qty, unit, note.
	Runs as the sender, who may not be a warehouse user: permissions are the caller's to check.
	"""
	user = user or frappe.session.user
	name = open_request(reference_doctype, reference_name)
	doc = frappe.get_doc("Item Request", name) if name else frappe.new_doc("Item Request")
	if not name:
		doc.update({"reference_doctype": reference_doctype, "reference_name": reference_name, "requested_by": user})
	doc.update({k: header.get(k) for k in ("title", "customer", "location", "start_date", "end_date")})

	source = section["source"]
	before = [l for l in doc.lines if l.section == source]
	row = next((s for s in doc.sections if s.source == source), None)
	accepted = frappe.parse_json(row.accepted_lines) if row and row.accepted_lines else None
	new_lines = []
	for line in lines:
		values = [line.get(k) for k in LINE_KEYS]
		changed = accepted is not None and accepted.get(line["source"]) != values
		new_lines.append({**{k: line.get(k) for k in LINE_KEYS}, "source": line["source"], "section": source, "changed": int(changed)})
	sent = {l["source"] for l in lines}
	removed = [f"{v[0]} × {v[1]:g}" if v[1] is not None else v[0] for k, v in (accepted or {}).items() if k not in sent]

	doc.set("lines", [l for l in doc.lines if l.section != source] + [frappe._dict(l) for l in new_lines])
	row = row or doc.append("sections", {"source": source})
	row.update(
		{
			"title": section.get("title"),
			"department": section.get("department"),
			"icon": section.get("icon"),
			"status": "Pending",  # every send waits for the warehouse's answer again
			"reject_reason": None,
			"changed": int(any(l["changed"] for l in new_lines) or bool(removed)),
			"lines_removed": len(removed),
			"removed": "\n".join(removed) or None,
		}
	)
	doc.add_version(section.get("title"), summary(before, lines, first=not before and not name), user)
	doc.flags.ignore_permissions = True
	doc.save() if name else doc.insert()
	return doc


def withdraw_section(reference_doctype, reference_name, source, user=None):
	"""The requesting app took a list back (e.g. deleted it). No sections left: the request is cancelled."""
	name = open_request(reference_doctype, reference_name)
	if not name:
		return None
	doc = frappe.get_doc("Item Request", name)
	row = next((s for s in doc.sections if s.source == source), None)
	if not row:
		return doc
	doc.set("lines", [l for l in doc.lines if l.section != source])
	doc.set("sections", [s for s in doc.sections if s.source != source])
	doc.add_version(row.title, _("withdrawn"), user or frappe.session.user)
	if not doc.sections:
		doc.status = "Cancelled"
	doc.flags.ignore_permissions = True
	doc.save()
	return doc


def summary(before, lines, first=False):
	"""What this send changed in the section, against the version sent before it."""
	if first or not before:
		return _("{0} lines").format(len(lines)) if len(lines) != 1 else _("1 line")
	old = {l.source: [l.get(k) for k in LINE_KEYS] for l in before}
	new = {l["source"]: [l.get(k) for k in LINE_KEYS] for l in lines}
	added = len(set(new) - set(old))
	removed = len(set(old) - set(new))
	changed = sum(1 for k in set(new) & set(old) if new[k] != old[k])
	bits = [f"{n} {word}" for n, word in ((added, _("added")), (changed, _("changed")), (removed, _("removed"))) if n]
	return ", ".join(bits) or _("sent again, no changes")
