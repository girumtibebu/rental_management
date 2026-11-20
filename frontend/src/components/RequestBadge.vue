<template>
  <!-- A request's status; a pending one that changed after the warehouse answered says so -->
  <Badge :label="label" :theme="theme" :size="size" />
</template>

<script setup>
import { computed } from 'vue'
import { Badge } from 'frappe-ui'

const props = defineProps({ request: Object, size: { type: String, default: 'sm' } })
const THEME = { Pending: 'orange', Accepted: 'green', Rejected: 'red', 'Checked out': 'blue', Returned: 'gray', Cancelled: 'gray' }
const label = computed(() => (props.request.status === 'Pending' ? (props.request.needs_review ? 'Changed' : 'Waiting') : props.request.status))
const theme = computed(() => THEME[props.request.status] || 'gray')
</script>
