import frappe


def execute():
	"""Item request lists get their own answer: those of requests answered before take the request's."""
	frappe.db.sql(
		"""update `tabItem Request Section` s join `tabItem Request` r on r.name = s.parent
		set s.status = if(r.status = 'Rejected', 'Rejected', 'Accepted'), s.reject_reason = if(r.status = 'Rejected', r.reject_reason, null)
		where r.status in ('Accepted', 'Rejected', 'Checked out', 'Returned')"""
	)
