<template>
  <div class="relative">
    <Icon name="scan" :size="14" class="pointer-events-none absolute left-2.5 top-[9px] text-ink-gray-5" />
    <input
      ref="input"
      v-model="code"
      class="h-8 w-56 rounded-md border border-outline-gray-3 bg-surface-white pl-8 pr-8 text-sm outline-none focus:border-outline-blue-3 lg:w-72"
      placeholder="Scan or type a serial…"
      autocomplete="off"
      @keydown.enter.prevent="go"
      @keydown.esc="code = ''"
    />
    <kbd
      v-if="!code"
      class="pointer-events-none absolute right-2 top-[7px] rounded border border-outline-gray-2 bg-surface-gray-1 px-1.5 text-[10px] text-ink-gray-5"
    >/</kbd>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'frappe-ui'
import Icon from './Icon.vue'
import { api, readError } from '../api'

const router = useRouter()
const input = ref(null)
const code = ref('')

async function go() {
  const value = code.value.trim()
  if (!value) return
  try {
    const unit = await api.findUnit(value)
    if (!unit) return toast.error(`No unit with serial ${value}`)
    code.value = ''
    input.value?.blur()
    router.push({ name: 'unit', params: { name: unit.name } })
  } catch (err) {
    toast.error(readError(err))
  }
}

function shortcut(event) {
  const typing = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)
  if (event.key === '/' && !typing && !event.ctrlKey && !event.metaKey) {
    event.preventDefault()
    input.value?.focus()
  }
}

onMounted(() => window.addEventListener('keydown', shortcut))
onBeforeUnmount(() => window.removeEventListener('keydown', shortcut))
</script>
