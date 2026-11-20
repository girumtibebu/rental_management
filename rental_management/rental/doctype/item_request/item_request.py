import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

LINE_KEYS = ("item", "qty", "unit", "note")
CLOSED = ("Returned", "Cancelled")


class ItemRequest(Document):
	"""Items another app (e.g. the project planner) asks the warehouse for, for one event.

	The requesting app sends one section (a list, e.g. Audio BOM) at a time with send_section;
	each send is a new version. The warehouse only answers: accepting keeps a snapshot, and
	what is sent after that is marked against it until the warehouse accepts again.
	"""

	def validate(self):
		before = self.get_doc_before_save()
		if self.status == "Accepted" and (not before or before.status != "Accepted" or before.needs_review):
			self.accepted_by, self.accepted_at = frappe.session.user, now_datetime()
			self.accepted_snapshot = frappe.as_json(self.snapshot(), indent=None)
			self.clear_changes()
		if self.status == "Rejected" and not (self.reject_reason or "").strip():
			frappe.throw(_("Say why the request is rejected."))

	def snapshot(self):
		return {"sections": [s.source for s in self.sections], "lines": {l.source: [l.section, *(l.get(k) for k in LINE_KEYS)] for l in self.lines}}

	def accepted(self):
		return frappe.parse_json(self.accepted_snapshot) if self.accepted_snapshot else None

	def clear_changes(self):
		self.needs_review = 0
		for row in [*self.sections, *self.lines]:
			row.changed = 0
		for row in self.sections:
			row.lines_removed, row.removed = 0, None

	def add_version(self, section, summary, user):
		self.version = (self.version or 0) + 1
		self.append("versions", {"version": self.version, "section": section, "summary": summary, "sent_by": user, "sent_at": now_datetime()})

	def reopen(self):
		"""A change after the warehouse answered: it needs their look again."""
		self.needs_review = int(any(s.changed for s in self.sections) or bool(self.flags.withdrawn_accepted))
		if self.needs_review and self.status in ("Accepted", "Rejected"):
			self.status = "Pending"


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
	accepted = doc.accepted()
	acc_lines = (accepted or {}).get("lines", {})
	new_lines = []
	for line in lines:
		was = acc_lines.get(line["source"])
		changed = bool(accepted) and (not was or was[0] != source or [was[1], *was[2:]] != [line.get(k) for k in LINE_KEYS])
		new_lines.append({**{k: line.get(k) for k in LINE_KEYS}, "source": line["source"], "section": source, "changed": int(changed)})
	sent = {l["source"] for l in lines}
	removed = [f"{v[1]} × {v[2]:g}" if v[2] is not None else v[1] for k, v in acc_lines.items() if v[0] == source and k not in sent]

	doc.set("lines", [l for l in doc.lines if l.section != source] + [frappe._dict(l) for l in new_lines])
	row = next((s for s in doc.sections if s.source == source), None) or doc.append("sections", {"source": source})
	is_new_section = bool(accepted) and source not in accepted.get("sections", [])
	row.update(
		{
			"title": section.get("title"),
			"department": section.get("department"),
			"icon": section.get("icon"),
			"changed": int(is_new_section or any(l["changed"] for l in new_lines) or bool(removed)),
			"lines_removed": len(removed),
			"removed": "\n".join(removed) or None,
		}
	)
	doc.add_version(section.get("title"), summary(before, lines, first=not before and not name), user)
	if accepted or doc.status == "Rejected":
		doc.reopen()
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
	accepted = doc.accepted()
	doc.flags.withdrawn_accepted = bool(accepted) and source in accepted.get("sections", [])
	doc.set("lines", [l for l in doc.lines if l.section != source])
	doc.set("sections", [s for s in doc.sections if s.source != source])
	doc.add_version(row.title, _("withdrawn"), user or frappe.session.user)
	if not doc.sections:
		doc.status = "Cancelled"
	elif accepted or doc.status == "Rejected":
		doc.reopen()
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
	return ", ".join(bits) or _("no changes")
