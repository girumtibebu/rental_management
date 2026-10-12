<template>
  <div v-if="total > pageLength" class="flex items-center justify-between border-t border-outline-gray-1 px-4 py-2 text-xs text-ink-gray-6">
    <span class="tabular">{{ from }}–{{ to }} of {{ total }}</span>
    <div class="flex items-center gap-1">
      <Button size="sm" :disabled="page <= 1" @click="$emit('update:page', page - 1)">Previous</Button>
      <Button size="sm" :disabled="to >= total" @click="$emit('update:page', page + 1)">Next</Button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Button } from 'frappe-ui'

const props = defineProps({ total: Number, page: Number, pageLength: { type: Number, default: 25 } })
defineEmits(['update:page'])

const from = computed(() => (props.total ? (props.page - 1) * props.pageLength + 1 : 0))
const to = computed(() => Math.min(props.page * props.pageLength, props.total))
</script>
