<template>
  <AppShell>
    <RouterView :key="route.path" />
  </AppShell>
  <ToastProvider />
</template>

<script setup>
import { onMounted, provide, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ToastProvider } from 'frappe-ui'
import AppShell from './components/AppShell.vue'
import { api } from './api'

const route = useRoute()
const summary = ref(null)

/** Warehouse totals shown in the sidebar and on the dashboard; refresh after anything that moves stock. */
async function refreshSummary() {
  try {
    summary.value = await api.dashboard()
  } catch (err) {
    console.error(err)
  }
  return summary.value
}

provide('rental', { summary, refreshSummary })
onMounted(refreshSummary)
</script>
