<template>
  <TextInput
    ref="input"
    v-model="code"
    class="w-56 lg:w-72"
    placeholder="Scan or type a serial…"
    autocomplete="off"
    @keydown.enter.prevent="go"
    @keydown.esc="code = ''"
  >
    <template #prefix><Icon name="scan" :size="14" class="text-ink-gray-5" /></template>
    <template #suffix>
      <kbd v-if="!code" class="rounded border border-outline-gray-2 bg-surface-gray-1 px-1.5 text-[10px] text-ink-gray-5">/</kbd>
    </template>
  </TextInput>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { TextInput, toast } from 'frappe-ui'
import Icon from './Icon.vue'
import { api, readError } from '../api'

const router = useRouter()
const input = ref(null)
const field = () => input.value?.$el?.querySelector('input')
const code = ref('')

async function go() {
  const value = code.value.trim()
  if (!value) return
  try {
    const unit = await api.findUnit(value)
    if (!unit) return toast.error(`No unit with serial ${value}`)
    code.value = ''
    field()?.blur()
    router.push({ name: 'unit', params: { name: unit.name } })
  } catch (err) {
    toast.error(readError(err))
  }
}

function shortcut(event) {
  const typing = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)
  if (event.key === '/' && !typing && !event.ctrlKey && !event.metaKey) {
    event.preventDefault()
    field()?.focus()
  }
}

onMounted(() => window.addEventListener('keydown', shortcut))
onBeforeUnmount(() => window.removeEventListener('keydown', shortcut))
</script>
