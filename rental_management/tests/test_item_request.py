"""Item requests: sections sent as versions, marks against the accepted snapshot, and links to movements.

Run: bench --site <site> run-tests --module rental_management.tests.test_item_request
"""

import frappe
from frappe.tests import IntegrationTestCase

from rental_management.rental.doctype.item_request.item_request import open_request, send_section, withdraw_section
from rental_management.ui import movements, requests

HEADER = {"title": "_Item request test", "location": "Hall A", "start_date": "2099-01-10"}


class TestItemRequest(IntegrationTestCase):
	def setUp(self):
		# any document can ask: a ToDo is enough here
		todo = frappe.db.get_value("ToDo", {"description": "_item request test"}) or frappe.get_doc({"doctype": "ToDo", "description": "_item request test"}).insert().name
		self.ref = ("ToDo", todo)
		frappe.db.delete("Item Request", {"reference_name": todo})

	def send(self, source, lines, title=None):
		section = {"source": source, "title": title or source.title(), "department": source.title()}
		return send_section(*self.ref, HEADER, section, [{"source": f"{source}-{i}", **line} for i, line in enumerate(lines)])

	def answer(self, status, reason=None):
		doc = frappe.get_doc("Item Request", open_request(*self.ref))
		doc.status, doc.reject_reason = status, reason
		doc.save()
		return doc

	def test_versions_and_marks(self):
		doc = self.send("audio", [{"item": "Mic", "qty": 6, "unit": "pcs"}])
		self.assertEqual((doc.version, doc.status, doc.title, doc.location), (1, "Pending", "_Item request test", "Hall A"))
		doc = self.send("video", [{"item": "LED", "qty": 30, "unit": "sqm"}])
		self.assertEqual((doc.version, [s.source for s in doc.sections]), (2, ["audio", "video"]))
		self.assertFalse(doc.needs_review)  # nothing accepted yet: nothing to mark

		self.answer("Accepted")
		doc = self.send("audio", [{"item": "Mic", "qty": 8, "unit": "pcs"}, {"item": "Stand", "qty": 6, "unit": "pcs"}])
		self.assertEqual((doc.status, doc.needs_review), ("Pending", 1))
		self.assertEqual({l.item: l.changed for l in doc.lines}, {"Mic": 1, "Stand": 1, "LED": 0})
		self.assertEqual([v.summary for v in doc.versions][-1], "1 added, 1 changed")

		self.answer("Accepted")
		doc = self.send("audio", [{"item": "Mic", "qty": 8, "unit": "pcs"}])
		audio = doc.sections[0]
		self.assertEqual((audio.changed, audio.lines_removed, audio.removed), (1, 1, "Stand × 6"))

		doc = withdraw_section(*self.ref, "video")
		self.assertEqual(([s.source for s in doc.sections], doc.needs_review, doc.versions[-1].summary), (["audio"], 1, "withdrawn"))
		doc = withdraw_section(*self.ref, "audio")
		self.assertEqual(doc.status, "Cancelled")
		self.assertIsNone(open_request(*self.ref))

	def test_reject_needs_a_reason(self):
		self.send("audio", [{"item": "Mic", "qty": 6, "unit": "pcs"}])
		self.assertRaises(frappe.ValidationError, self.answer, "Rejected")
		self.assertEqual(self.answer("Rejected", "Booked that week").status, "Rejected")

	def test_movement_link_rules(self):
		name = self.send("audio", [{"item": "Mic", "qty": 6, "unit": "pcs"}]).name
		self.assertRaises(frappe.ValidationError, movements.linked_request, name, "CHECK_OUT")  # not accepted yet
		self.answer("Accepted")
		self.assertEqual(movements.linked_request(name, "CHECK_OUT").name, name)
		self.assertRaises(frappe.ValidationError, movements.linked_request, name, "CHECK_IN")  # nothing went out yet
		self.assertRaises(frappe.ValidationError, movements.linked_request, name, "LOST")
		self.assertIn(name, [r.name for r in requests.requests_for_movement("CHECK_OUT")])
		self.assertNotIn(name, [r.name for r in requests.requests_for_movement("CHECK_IN")])
