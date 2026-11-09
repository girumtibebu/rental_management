frappe.ui.form.on("Rental Workspace", {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.item_group) return;
		frm.add_custom_button(__("Apply company defaults to items"), () => {
			frappe.confirm(
				__("Give every item and category under {0} this workspace's company, store and cost center? Items that already have one for this company are skipped.", [frm.doc.item_group]),
				() =>
					frappe.call({
						method: "rental_management.ui.catalog.apply_workspace_defaults",
						args: { workspace: frm.doc.name },
						freeze: true,
						callback: (r) =>
							frappe.msgprint(__("{0} items and {1} categories updated", [r.message.items, r.message.groups])),
					})
			);
		});
	},
});
