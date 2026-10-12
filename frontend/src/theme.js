/** Status colours and labels, shared by every screen so a status always looks the same. */

export const STATUS_THEME = {
  Warehouse: 'green',
  'At Event': 'blue',
  'In Maintenance': 'orange',
  Missing: 'red',
}

export const CONDITION_THEME = {
  OK: 'green',
  'Need Cleaning': 'orange',
  Damaged: 'red',
  'Partially Ok': 'orange',
  Scrapped: 'gray',
}

export const TICKET_THEME = {
  'Attention Required': 'red',
  'In Repair': 'blue',
  Complete: 'green',
}

export const MOVEMENT_TYPES = {
  CHECK_OUT: { label: 'Check out', hint: 'Equipment leaving for an event', theme: 'blue', icon: 'out' },
  CHECK_IN: { label: 'Check in', hint: 'Equipment coming back to the warehouse', theme: 'green', icon: 'in' },
  MAINTENANCE_OUT: { label: 'Send to repair', hint: 'Equipment going to the repair shop', theme: 'orange', icon: 'wrench' },
  MAINTENANCE_IN: { label: 'Back from repair', hint: 'Repaired equipment returning', theme: 'green', icon: 'check' },
  LOST: { label: 'Mark lost', hint: 'Equipment that cannot be found', theme: 'red', icon: 'alert' },
  PURCHASE: { label: 'Purchase', theme: 'gray', icon: 'plus' },
  DISPOSE: { label: 'Dispose', theme: 'gray', icon: 'close' },
}

/** Movement types the scan screen offers. */
export const SCAN_TYPES = ['CHECK_OUT', 'CHECK_IN', 'MAINTENANCE_OUT', 'MAINTENANCE_IN', 'LOST']

export const movementLabel = (type) => MOVEMENT_TYPES[type]?.label || type
export const movementTheme = (type) => MOVEMENT_TYPES[type]?.theme || 'gray'
