// Adds "Open in Rental app" to rental records on the native forms. The app itself is a full-page Vue app at /rental.
(function () {
	const ROUTES = {
		Item: (doc) => doc.is_rental_item && `/rental/catalog/${encodeURIComponent(doc.name)}`,
		"Serial No": (doc) => `/rental/units/${encodeURIComponent(doc.name)}`,
		"Stock Entry": (doc) => doc.rental_movement_type && doc.docstatus === 1 && `/rental/movements/${encodeURIComponent(doc.name)}`,
		"Rental Item Maintenance": () => "/rental/maintenance",
	};

	Object.keys(ROUTES).forEach((doctype) => {
		frappe.ui.form.on(doctype, {
			refresh(frm) {
				const route = !frm.is_new() && ROUTES[doctype](frm.doc);
				if (!route) return;
				frm.add_custom_button(__("Open in Rental app"), () => window.open(route, "_blank"));
			},
		});
	});
})();
