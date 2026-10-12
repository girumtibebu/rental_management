// Adds "Open in Rental app" to the rental forms. The app itself is a full-page Vue app at /rental.
(function () {
	const ROUTES = {
		"Rental Item Unit": (doc) => `/rental/units/${encodeURIComponent(doc.name)}`,
		"Rental Item Template": (doc) => `/rental/catalog/${encodeURIComponent(doc.name)}`,
		"Rental Movement": (doc) => `/rental/movements/${encodeURIComponent(doc.name)}`,
		"Rental Item Maintenance": () => `/rental/maintenance`,
	};

	Object.keys(ROUTES).forEach((doctype) => {
		frappe.ui.form.on(doctype, {
			refresh(frm) {
				if (frm.is_new()) return;
				frm.add_custom_button(__("Open in Rental app"), () => {
					window.open(ROUTES[doctype](frm.doc), "_blank");
				});
			},
		});
	});
})();
