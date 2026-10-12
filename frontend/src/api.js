import { call } from 'frappe-ui'

const P = 'rental_management.ui.'
const json = (value) => (value == null ? undefined : JSON.stringify(value))

export const api = {
  dashboard: () => call(P + 'dashboard.get_dashboard'),

  listUnits: (params) => call(P + 'units.list_units', params),
  findUnit: (code) => call(P + 'units.find_unit', { code }),
  getUnit: (name) => call(P + 'units.get_unit', { name }),
  updateStorage: (name, place) => call(P + 'units.update_storage', { name, ...place }),

  facets: () => call(P + 'catalog.facets'),
  listTemplates: (params) => call(P + 'catalog.list_templates', params),
  getTemplate: (name) => call(P + 'catalog.get_template', { name }),
  createTemplate: (values) => call(P + 'catalog.create_template', values),
  activateTemplate: (name) => call(P + 'catalog.activate_template', { name }),
  generateUnits: (template, count) => call(P + 'catalog.generate_units', { template, count }),

  checkScan: (code, transactionType) => call(P + 'movements.check_scan', { code, transaction_type: transactionType }),
  createMovement: (values) =>
    call(P + 'movements.create_movement', { ...values, units: json(values.units), bulk: json(values.bulk) }),
  listMovements: (params) => call(P + 'movements.list_movements', params),
  getMovement: (name) => call(P + 'movements.get_movement', { name }),

  board: () => call(P + 'maintenance.board'),
  createTicket: (values) => call(P + 'maintenance.create_ticket', values),
  getTicket: (name) => call(P + 'maintenance.get_ticket', { name }),
  startRepair: (name) => call(P + 'maintenance.start_repair', { name }),
  completeTicket: (values) => call(P + 'maintenance.complete', values),

  searchLink: (doctype, txt) =>
    call('frappe.desk.search.search_link', { doctype, txt: txt || '', page_length: 10 }),
}

export function readError(err) {
  const raw = err?.messages?.[0] || err?.message || String(err)
  return String(raw).replace(/<[^>]+>/g, '').slice(0, 300)
}
