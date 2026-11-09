<template>
  <div v-if="!loaded" class="flex h-full items-center justify-center text-ink-gray-5">
    <span v-if="loadError" class="text-ink-red-6">{{ loadError }}</span>
    <span v-else>Loading…</span>
  </div>
  <WorkspacePicker v-else-if="needsChoice" :workspaces="workspaces" @choose="choose" />
  <AppShell v-else :key="current">
    <RouterView :key="route.path" />
  </AppShell>
  <ToastProvider />
</template>

<script setup>
import { provide, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ToastProvider } from 'frappe-ui'
import AppShell from './components/AppShell.vue'
import WorkspacePicker from './components/WorkspacePicker.vue'
import { api, readError } from './api'
import { chooseWorkspace, current, loaded, loadWorkspaces, needsChoice, workspaces } from './workspace'

const route = useRoute()
const router = useRouter()
const summary = ref(null)
const loadError = ref('')

/** Warehouse totals shown in the sidebar and on the dashboard; refresh after anything that moves stock. */
async function refreshSummary() {
  try {
    summary.value = await api.dashboard()
  } catch (err) {
    console.error(err)
  }
  return summary.value
}

/** Switch company: everything on screen belongs to the old workspace, so start again from the dashboard. */
function choose(name) {
  chooseWorkspace(name)
  summary.value = null
  router.push('/')
  refreshSummary()
}

provide('rental', { summary, refreshSummary, chooseWorkspace: choose })

loadWorkspaces()
  .then((list) => {
    if (!list.length) loadError.value = 'You have not been given a rental workspace yet. Ask a manager to add you to one.'
    if (current.value) refreshSummary()
  })
  .catch((err) => {
    loadError.value = readError(err)
    loaded.value = false
  })
</script>
