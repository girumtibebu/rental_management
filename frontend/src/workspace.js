import { computed, ref } from 'vue'
import { call } from 'frappe-ui'

/** The rental workspace (company) the screens work in. Every rental API call sends it as a header. */
const KEY = `rental.workspace.${window.user || ''}`
export const workspaces = ref([])
export const current = ref(readStored())
export const loaded = ref(false)

export const currentWorkspace = computed(() => workspaces.value.find((w) => w.name === current.value) || null)
/** Alter-style workspace: quantities first, scanning optional. */
export const bulkFirst = computed(() => currentWorkspace.value?.mode === 'Bulk First')
/** True when the user has several workspaces and has not picked one yet: show the picker. */
export const needsChoice = computed(() => loaded.value && workspaces.value.length > 1 && !currentWorkspace.value)

function readStored() {
  try {
    return localStorage.getItem(KEY) || ''
  } catch {
    return ''
  }
}

export function workspaceHeaders() {
  return current.value ? { 'X-Rental-Workspace': current.value } : {}
}

export async function loadWorkspaces() {
  workspaces.value = (await call('rental_management.ui.workspaces.list_workspaces')) || []
  if (!workspaces.value.some((w) => w.name === current.value)) {
    // One workspace: go straight in. Several: wait for the picker.
    current.value = workspaces.value.length === 1 ? workspaces.value[0].name : ''
  }
  loaded.value = true
  return workspaces.value
}

export function chooseWorkspace(name) {
  current.value = name
  try {
    localStorage.setItem(KEY, name)
  } catch {
    // private window: the choice lasts until reload
  }
}
