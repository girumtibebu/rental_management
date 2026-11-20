"""Item requests: lists sent as versions, answered one by one, marks against each list's accepted lines, movement links.

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

	def name(self):
		return open_request(*self.ref)

	def answer(self, source, status, reason=None):
		requests.answer(self.name(), source, status, reason)
		return frappe.get_doc("Item Request", self.name())

	def test_each_list_is_answered(self):
		self.send("audio", [{"item": "Mic", "qty": 6, "unit": "pcs"}])
		doc = self.send("video", [{"item": "LED", "qty": 30, "unit": "sqm"}])
		self.assertEqual((doc.version, doc.status, [s.status for s in doc.sections]), (2, "Pending", ["Pending", "Pending"]))

		doc = self.answer("audio", "Accepted")
		self.assertEqual((doc.status, [s.status for s in doc.sections]), ("Pending", ["Accepted", "Pending"]))  # video still waits
		self.assertRaises(frappe.ValidationError, self.answer, "video", "Rejected")  # a reason is needed
		doc = self.answer("video", "Rejected", "LED wall is booked")
		self.assertEqual((doc.status, doc.sections[1].reject_reason), ("Accepted", "LED wall is booked"))  # partly accepted

		doc = self.send("video", [{"item": "LED", "qty": 20, "unit": "sqm"}])  # changed and sent again after the rejection
		self.assertEqual((doc.status, doc.sections[1].status, doc.sections[1].reject_reason), ("Pending", "Pending", None))
		self.assertFalse(doc.sections[1].changed)  # never accepted: nothing to mark against

		requests.accept_all(self.name())
		doc = frappe.get_doc("Item Request", self.name())
		self.assertEqual((doc.status, {s.status for s in doc.sections}), ("Accepted", {"Accepted"}))
		self.assertRaises(frappe.ValidationError, requests.accept_all, self.name())  # nothing waiting

	def test_marks_against_the_accepted_list(self):
		self.send("audio", [{"item": "Mic", "qty": 6, "unit": "pcs"}, {"item": "Stand", "qty": 6, "unit": "pcs"}])
		self.send("video", [{"item": "LED", "qty": 30, "unit": "sqm"}])
		requests.accept_all(self.name())

		doc = self.send("audio", [{"item": "Mic", "qty": 8, "unit": "pcs"}])
		audio, video = doc.sections
		self.assertEqual((audio.status, audio.changed, audio.lines_removed, audio.removed), ("Pending", 1, 1, "Stand × 6"))
		self.assertEqual((video.status, video.changed, doc.needs_review), ("Accepted", 0, 1))
		self.assertEqual({l.item: l.changed for l in doc.lines}, {"Mic": 1, "LED": 0})
		self.assertEqual(doc.versions[-1].summary, "1 changed, 1 removed")

		doc = self.answer("audio", "Accepted")
		self.assertFalse(doc.needs_review or doc.sections[0].changed or doc.sections[0].removed)

		doc = withdraw_section(*self.ref, "video")
		self.assertEqual(([s.source for s in doc.sections], doc.versions[-1].summary), (["audio"], "withdrawn"))
		doc = withdraw_section(*self.ref, "audio")
		self.assertEqual(doc.status, "Cancelled")
		self.assertIsNone(self.name())

	def test_movement_link_rules(self):
		name = self.send("audio", [{"item": "Mic", "qty": 6, "unit": "pcs"}]).name
		self.assertRaises(frappe.ValidationError, movements.linked_request, name, "CHECK_OUT")  # not accepted yet
		self.answer("audio", "Accepted")
		self.assertEqual(movements.linked_request(name, "CHECK_OUT").name, name)
		self.assertRaises(frappe.ValidationError, movements.linked_request, name, "CHECK_IN")  # nothing went out yet
		self.assertRaises(frappe.ValidationError, movements.linked_request, name, "LOST")
		self.assertIn(name, [r.name for r in requests.requests_for_movement("CHECK_OUT")])
		self.assertNotIn(name, [r.name for r in requests.requests_for_movement("CHECK_IN")])
