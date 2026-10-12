<template>
  <Dialog v-model="open" :options="{ title: 'Report a problem', size: 'md' }">
    <template #body-content>
      <div class="grid gap-3 text-sm">
        <label class="grid gap-1">
          <span class="text-ink-gray-6">Unit serial</span>
          <input
            ref="serialInput"
            v-model="serial"
            class="h-8 rounded-md border border-outline-gray-3 px-2.5 font-mono outline-none focus:border-outline-blue-3"
            placeholder="Scan or type a serial"
            autocomplete="off"
            @keydown.enter.prevent="lookup"
            @blur="lookup"
          />
          <span v-if="unit" class="flex items-center gap-2 text-xs text-ink-gray-6">
            <Icon name="check" :size="12" class="text-ink-green-6" /> {{ unit.unit_name }}
            <StatusBadge :value="unit.movement_status" /> <StatusBadge :value="unit.unit_condition" kind="condition" />
          </span>
          <span v-else-if="missing" class="text-xs text-ink-red-6">No unit with serial {{ serial.trim() }}</span>
        </label>

        <div class="grid gap-1">
          <span class="text-ink-gray-6">What is wrong?</span>
          <div class="grid grid-cols-2 gap-2">
            <button
              v-for="option in OPTIONS"
              :key="option.value"
              class="rounded-lg border px-3 py-2 text-left"
              :class="condition === option.value ? 'border-outline-blue-3 bg-surface-blue-2' : 'border-outline-gray-2 hover:border-outline-gray-4'"
              @click="condition = option.value"
            >
              <div class="font-medium text-ink-gray-9">{{ option.value }}</div>
              <div class="text-xs text-ink-gray-5">{{ option.hint }}</div>
            </button>
          </div>
        </div>

        <label class="grid gap-1">
          <span class="text-ink-gray-6">Description</span>
          <textarea
            v-model="description"
            rows="3"
            class="rounded-md border border-outline-gray-3 p-2.5 outline-none focus:border-outline-blue-3"
            placeholder="What happened? Which part is affected?"
          />
        </label>

        <div class="mt-1 flex justify-end gap-2">
          <Button label="Cancel" @click="open = false" />
          <Button variant="solid" label="Create ticket" :disabled="!unit" :loading="busy" @click="submit" />
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { Button, Dialog, toast } from 'frappe-ui'
import Icon from './Icon.vue'
import StatusBadge from './StatusBadge.vue'
import { api, readError } from '../api'

const props = defineProps({ modelValue: Boolean, serial: String })
const emit = defineEmits(['update:modelValue', 'created'])

const OPTIONS = [
  { value: 'Damaged', hint: 'Broken or not working' },
  { value: 'Need Cleaning', hint: 'Works but must be cleaned' },
]

const open = computed({ get: () => props.modelValue, set: (value) => emit('update:modelValue', value) })
const serialInput = ref(null)
const serial = ref('')
const unit = ref(null)
const missing = ref(false)
const condition = ref('Damaged')
const description = ref('')
const busy = ref(false)

watch(open, async (value) => {
  if (!value) return
  serial.value = props.serial || ''
  unit.value = null
  missing.value = false
  condition.value = 'Damaged'
  description.value = ''
  if (serial.value) lookup()
  await nextTick()
  if (!serial.value) serialInput.value?.focus()
})

async function lookup() {
  const code = serial.value.trim()
  if (!code) return
  try {
    unit.value = await api.findUnit(code)
    missing.value = !unit.value
  } catch (err) {
    toast.error(readError(err))
  }
}

async function submit() {
  busy.value = true
  try {
    const name = await api.createTicket({ code: unit.value.unit_serial_number || unit.value.name, unit_condition: condition.value, issue_description: description.value })
    toast.success('Ticket created')
    open.value = false
    emit('created', name)
  } catch (err) {
    toast.error(readError(err))
  } finally {
    busy.value = false
  }
}
</script>
