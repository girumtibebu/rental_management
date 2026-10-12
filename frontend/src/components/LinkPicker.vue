<template>
  <label class="grid gap-1 text-sm">
    <span v-if="label" class="text-ink-gray-6">{{ label }}</span>
    <div class="relative">
      <input
        v-model="text"
        class="h-8 w-full rounded-md border border-outline-gray-3 bg-surface-white px-2.5 outline-none focus:border-outline-blue-3"
        :placeholder="placeholder || 'Search…'"
        autocomplete="off"
        @focus="open"
        @input="search"
        @blur="close"
        @keydown.down.prevent="move(1)"
        @keydown.up.prevent="move(-1)"
        @keydown.enter.prevent="pickHighlighted"
        @keydown.esc="shown = false"
      />
      <ul
        v-if="shown"
        class="absolute left-0 right-0 top-9 z-50 max-h-56 overflow-auto rounded-md border border-outline-gray-2 bg-surface-white py-1 shadow-xl"
      >
        <li
          v-for="(option, index) in options"
          :key="option.value"
          class="cursor-pointer px-3 py-1.5 text-sm"
          :class="index === highlighted ? 'bg-surface-blue-2' : 'hover:bg-surface-gray-2'"
          @mousedown.prevent="pick(option)"
          @mousemove="highlighted = index"
        >
          <div class="font-medium text-ink-gray-9">{{ option.value }}</div>
          <div v-if="option.description" class="truncate text-xs text-ink-gray-5">{{ option.description }}</div>
        </li>
        <li v-if="!options.length" class="px-3 py-2 text-sm text-ink-gray-5">{{ loading ? 'Searching…' : 'No matches' }}</li>
      </ul>
    </div>
  </label>
</template>

<script setup>
import { ref, watch } from 'vue'
import { api } from '../api'

const props = defineProps({ modelValue: String, label: String, doctype: String, placeholder: String, filters: Object })
const emit = defineEmits(['update:modelValue'])

const text = ref(props.modelValue || '')
const options = ref([])
const shown = ref(false)
const loading = ref(false)
const highlighted = ref(0)
let timer
let ticket = 0

watch(() => props.modelValue, (value) => {
  text.value = value || ''
})

async function fetch(txt) {
  const mine = ++ticket
  loading.value = true
  const found = (await api.searchLink(props.doctype, txt, props.filters).catch(() => [])) || []
  if (mine !== ticket) return
  options.value = found
  highlighted.value = 0
  loading.value = false
}

function open() {
  shown.value = true
  fetch(text.value)
}

function search() {
  shown.value = true
  clearTimeout(timer)
  timer = setTimeout(() => fetch(text.value), 150)
}

function pick(option) {
  text.value = option.value
  shown.value = false
  emit('update:modelValue', option.value)
}

function pickHighlighted() {
  const option = options.value[highlighted.value]
  if (option) pick(option)
}

function move(step) {
  if (!options.value.length) return
  highlighted.value = (highlighted.value + step + options.value.length) % options.value.length
}

function close() {
  setTimeout(() => {
    shown.value = false
    if (!text.value.trim() && props.modelValue) emit('update:modelValue', '')
    else if (text.value !== (props.modelValue || '')) text.value = props.modelValue || ''
  }, 120)
}
</script>
