frappe.ui.form.on('Rental Item Template', {
    onload: function (frm) {
        // Client Script: client script for SKU
        frm.toggle_display('item_name', true);
        frm.set_df_property('item_name', 'read_only', 1);
        if (!frm.doc.item_name) {
            frm.set_value('item_name', '-');
        }

        frm.toggle_display('sku_naming_series', true);
        frm.set_df_property('sku_naming_series', 'read_only', 1);
        if (!frm.doc.sku_naming_series) {
            frm.set_value('sku_naming_series', '-');
        }

        // Client Script: Rental Template Status
        frm.set_df_property('status', 'hidden', 1);
    },

    refresh: function (frm) {
        // Client Script: Bulk Item Option
        toggle_rental_item_type_fields(frm);

        // Client Script: Rental Template Status
        frm.clear_custom_buttons();
        const is_bulk = frm.doc.rental_item_type_box === 'Bulk';

        if (frm.is_new()) {
            frm.enable_save();
            return;
        }

        if (frm.doc.status === 'Draft') {
            frm.disable_save();
            frm.add_custom_button(__('Complete'), function () {
                frm.set_value('status', 'Completed');
                frm.save();
            });
        }

        if (frm.doc.status === 'Completed') {
            frm.disable_save();
            frm.set_read_only();

            if (!is_bulk) {
                frm.add_custom_button(__('Create Units'), function () {
                    create_units_dialog(frm);
                });
            }
        }
    },

    item_model: function (frm) {
        setItemModelLong(frm);
        generate_sku(frm);
    },

    item_model_long: function (frm) {
        setItemName(frm);
    },

    item_type: function (frm) {
        setItemName(frm);
        generate_sku(frm);
    },

    item_brand: function (frm) {
        setItemName(frm);
        generate_sku(frm);
    },

    rental_item_type_box: function (frm) {
        generate_sku(frm);
        toggle_rental_item_type_fields(frm);
    },

    suffix: function (frm) {
        generate_sku(frm);
    },

    sku_naming_series: function (frm) {
        // Client Script: SKU Character Count code
        const sku = frm.doc.sku_naming_series || "";
        const length = sku.length;
        frm.set_value('sku_character_count', length);

        if (frm.doc.item_type === "Unit" && length > 15) {
            frappe.msgprint({
                title: __("SKU Too Long"),
                message: __("SKU length exceeds 15 characters for Unit type."),
                indicator: "red"
            });
        }

        if (frm.doc.item_type === "Box" && length > 8) {
            frappe.msgprint({
                title: __("SKU Too Long"),
                message: __("SKU length exceeds 8 characters for Box type."),
                indicator: "red"
            });
        }
    },

    after_save: function (frm) {
        if (!frm.doc.status) {
            frm.set_value('status', 'Draft');
            frm.disable_save();
        }
    }
});

function setItemModelLong(frm) {
    let name = frm.doc.item_model || '-';
    frm.set_value('item_model_long', name.trim());
}

function setItemName(frm) {
    let parts = [];
    if (frm.doc.item_model_long) parts.push(frm.doc.item_model_long);
    if (frm.doc.item_brand) parts.push(frm.doc.item_brand);
    if (frm.doc.item_type) parts.push(frm.doc.item_type);
    frm.set_value('item_name', parts.join(' ').trim());
}

function generate_sku(frm) {
    const full_code = (val) => (val || "").replace(/[^a-zA-Z0-9]/g, "").toUpperCase();
    const short_code = (val) => full_code(val).substring(0, 2);

    let model_full = full_code(frm.doc.item_model);
    let brand_short = short_code(frm.doc.item_brand);
    let type_short = short_code(frm.doc.item_type);
    let item_kind = frm.doc.rental_item_type_box;
    let suffix_digits = parseInt(frm.doc.suffix);

    if (!model_full || !suffix_digits) {
        frm.set_value('sku_naming_series', '-');
        return;
    }

    let prefix = item_kind === "Box" ? model_full : `${model_full}-${brand_short}-${type_short}`;
    let sequence_mask = '#'.repeat(suffix_digits);
    frm.set_value('sku_naming_series', `${prefix}-${sequence_mask}`);
}

function toggle_rental_item_type_fields(frm) {
    const is_bulk = frm.doc.rental_item_type_box === "Bulk";
    const sku_fields = ["suffix", "sku_naming_series", "sku_character_count"];

    sku_fields.forEach(field => {
        frm.set_df_property(field, "hidden", is_bulk);
        frm.set_df_property(field, "reqd", !is_bulk);
        frm.set_df_property(field, "read_only", is_bulk);
    });

    if (is_bulk) {
        if (!frm.doc.suffix) frm.set_value("suffix", "NONE");
        if (!frm.doc.sku_naming_series) frm.set_value("sku_naming_series", "NONE");
        if (!frm.doc.sku_character_count) frm.set_value("sku_character_count", 0);
    }
}

function create_units_dialog(frm) {
    const d = new frappe.ui.Dialog({
        title: __('Create Rental Item Units'),
        fields: [
            {
                label: __('Number of Units'),
                fieldname: 'total_units',
                fieldtype: 'Int',
                default: 1,
                reqd: 1,
                description: __('Enter a number between 1 and 20')
            }
        ],
        primary_action_label: __('Create'),
        primary_action(values) {
            if (values.total_units < 1 || values.total_units > 20) {
                frappe.msgprint(__('Please enter a number between 1 and 20'));
                return;
            }
            d.hide();
            frappe.call({
                method: "rental_management.api.create_rental_item_units",
                args: {
                    template_name: frm.doc.name,
                    total_units: values.total_units
                },
                callback(r) {
                    if (r.message && r.message.units_created) {
                        const count = r.message.units_created.length;
                        const list_view_url = `/app/rental-item-unit?filters=${encodeURIComponent(JSON.stringify([["item_template", "=", frm.doc.name]]))}`;
                        frappe.show_alert({
                            message: __("{0} Rental Item Units created. <a href='{1}' target='_blank'>View Units</a>", [count, list_view_url]),
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    }
                }
            });
        }
    });
    d.show();
}
