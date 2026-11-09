<template>
  <!-- frappe-ui Combobox renders its list in a portal, so it is never cut off by a card or dialog edge. -->
  <Combobox
    v-model:query="query"
    :model-value="modelValue || null"
    :options="items"
    :label="label"
    :placeholder="placeholder || 'Search…'"
    :loading="loading"
    :filterable="false"
    open-on-focus
    open-on-click
    empty-text="No matches"
    @update:model-value="(value) => emit('update:modelValue', value || '')"
    @update:open="(isOpen) => isOpen && fetch(query)"
  />
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Combobox, toast } from 'frappe-ui'
import { api, readError } from '../api'

const props = defineProps({
  modelValue: String,
  label: String,
  doctype: String,
  placeholder: String,
  filters: Object,
  // offer "+ Create …" when nothing matches the typed name exactly
  creatable: Boolean,
})
const emit = defineEmits(['update:modelValue'])

const query = ref(props.modelValue || '')
const found = ref([])
const loading = ref(false)
const doctypeLabel = computed(() => (props.label || props.doctype).replace(/\s*\(.*\)$/, '').toLowerCase())
let timer
let ticket = 0

const items = computed(() => {
  const options = found.value.map((o) => ({ label: o.value, value: o.value, description: o.description }))
  // Keep the committed value resolvable even when the latest search did not return it.
  if (props.modelValue && !options.some((o) => o.value === props.modelValue)) {
    options.unshift({ label: props.modelValue, value: props.modelValue })
  }
  if (props.creatable) {
    options.push({
      type: 'custom',
      key: 'create',
      label: `Create ${doctypeLabel.value}`,
      icon: 'lucide-plus',
      condition: ({ query: typed }) => {
        const text = typed.trim().toLowerCase()
        return Boolean(text) && !loading.value && !found.value.some((o) => o.value.toLowerCase() === text)
      },
      onClick: ({ query: typed }) => create(typed.trim()),
    })
  }
  return options
})

watch(() => props.modelValue, (value) => {
  if ((value || '') !== query.value) query.value = value || ''
})

watch(query, (text) => {
  clearTimeout(timer)
  timer = setTimeout(() => fetch(text), 150)
})

async function fetch(txt) {
  const mine = ++ticket
  loading.value = true
  // The input shows the committed value; searching for it would hide every other option.
  const result = (await api.searchLink(props.doctype, txt === props.modelValue ? '' : txt, props.filters).catch(() => [])) || []
  if (mine !== ticket) return
  found.value = result
  loading.value = false
}

async function create(text) {
  try {
    const name = await api.quickCreate(props.doctype, text)
    toast.success(`${props.doctype} “${name}” created`)
    emit('update:modelValue', name)
  } catch (err) {
    toast.error(readError(err))
  }
}
</script>
