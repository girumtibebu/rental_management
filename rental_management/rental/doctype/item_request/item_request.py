import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class ItemRequest(Document):
	"""Items another app (e.g. the project planner) asks the warehouse for, for one event.

	The requesting app owns the sections and lines and rewrites them when they change; the
	warehouse owns the status. Lines changed after the warehouse accepted or rejected are
	flagged, and accepting again clears the flags.
	"""

	def validate(self):
		before = self.get_doc_before_save()
		if self.status == "Accepted" and (not before or before.status != "Accepted" or before.needs_review):
			self.accepted_by, self.accepted_at = frappe.session.user, now_datetime()
			self.clear_changes()
		if self.status == "Rejected" and not (self.reject_reason or "").strip():
			frappe.throw(_("Say why the request is rejected."))

	def clear_changes(self):
		self.needs_review = 0
		for row in [*self.sections, *self.lines]:
			row.changed = 0
		for row in self.sections:
			row.lines_removed = 0
