frappe.ui.form.on("Rental Item Maintenance", {
	validate(frm) {
		frm.doc.color = normalize_color(frm.doc.color);
	},
});

function normalize_color(value) {
	var text = (value || "").toLowerCase();

	if (["meetings", "meeting", "red"].some(function (part) { return text.includes(part); })) {
		return "Meetings";
	}

	if (["maintenance", "purple", "tech ops"].some(function (part) { return text.includes(part); })) {
		return "Maintenance";
	}

	if (["lunch", "grey", "gray", "routine"].some(function (part) { return text.includes(part); })) {
		return "Lunch";
	}

	if (["logistics", "blue"].some(function (part) { return text.includes(part); })) {
		return "Logistics";
	}

	return value;
}