"""Plain constants for the company switcher (no Frappe import, so hooks.py can use them)."""

# Doctypes that get the list filter. Kept explicit (rather than a "*" hook) so it
# works on every Frappe v16 release and only touches company-owned records.
SCOPED_DOCTYPES = (
	# selling
	"Quotation",
	"Sales Order",
	"Sales Invoice",
	"Delivery Note",
	"POS Invoice",
	# buying
	"Material Request",
	"Request for Quotation",
	"Supplier Quotation",
	"Purchase Order",
	"Purchase Receipt",
	"Purchase Invoice",
	# accounts
	"Payment Entry",
	"Payment Request",
	"Journal Entry",
	"Account",
	"Cost Center",
	"Bank Account",
	"Budget",
	# stock
	"Warehouse",
	"Stock Entry",
	"Stock Reconciliation",
	"Pick List",
	"Serial No",
	"Batch",
	# crm / projects
	"Lead",
	"Opportunity",
	"Project",
	"Task",
	"Timesheet",
	"Contract",
	# assets / hr
	"Asset",
	"Employee",
	"Department",
	"Designation",
	"Expense Claim",
	"Employee Advance",
	"Leave Application",
	"Attendance",
	"Salary Slip",
	# rental
	"Rental Workspace",
	"Rental Item Maintenance",
)


PRINT_FORMAT_DOCTYPES = {
	"Quotation": "rental_quotation_print_format",
	"Sales Order": "rental_sales_order_print_format",
	"Sales Invoice": "rental_sales_invoice_print_format",
	"Delivery Note": "rental_delivery_note_print_format",
	"Purchase Order": "rental_purchase_order_print_format",
}
