<template>
  <Badge v-if="value" :label="label" :theme="theme" :size="size" />
</template>

<script setup>
import { computed } from 'vue'
import { Badge } from 'frappe-ui'
import { CONDITION_THEME, STATUS_THEME, TICKET_THEME, movementLabel, movementTheme } from '../theme'

const props = defineProps({
  value: String,
  kind: { type: String, default: 'status' },
  size: { type: String, default: 'sm' },
})

const theme = computed(() => {
  if (props.kind === 'condition') return CONDITION_THEME[props.value] || 'gray'
  if (props.kind === 'ticket') return TICKET_THEME[props.value] || 'gray'
  if (props.kind === 'type') return movementTheme(props.value)
  return STATUS_THEME[props.value] || 'gray'
})

const label = computed(() => (props.kind === 'type' ? movementLabel(props.value) : props.value))
</script>
