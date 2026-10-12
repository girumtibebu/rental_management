import { call } from 'frappe-ui'

const P = 'rental_management.ui.'
const json = (value) => (value == null ? undefined : JSON.stringify(value))

export const api = {
  dashboard: () => call(P + 'dashboard.get_dashboard'),

  listUnits: (params) => call(P + 'units.list_units', params),
  findUnit: (code) => call(P + 'units.find_unit', { code }),
  getUnit: (name) => call(P + 'units.get_unit', { name }),
  updateStorage: (name, place) => call(P + 'units.update_storage', { name, ...place }),
  pack: (box, units) => call(P + 'units.pack', { box, units: json(units) }),

  facets: () => call(P + 'catalog.facets'),
  listItems: (params) => call(P + 'catalog.list_items', params),
  getItem: (name) => call(P + 'catalog.get_item', { name }),
  createItem: (values) => call(P + 'catalog.create_item', values),
  generateUnits: (itemCode, count) => call(P + 'catalog.generate_units', { item_code: itemCode, count }),
  receiveStock: (itemCode, qty) => call(P + 'catalog.receive_stock', { item_code: itemCode, qty }),

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

  quickCreate: (doctype, value) => call(P + 'links.quick_create', { doctype, value }),
  searchLink: (doctype, txt, filters) =>
    call('frappe.desk.search.search_link', { doctype, txt: txt || '', page_length: 10, filters: json(filters) }),
}

export function readError(err) {
  const raw = err?.messages?.[0] || err?.message || String(err)
  return String(raw).replace(/<[^>]+>/g, '').slice(0, 300)
}
