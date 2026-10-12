<template>
  <Dialog v-model="open" :options="{ title: 'New catalog item', size: 'lg' }">
    <template #body-content>
      <div class="grid gap-3 text-sm">
        <div class="grid gap-1">
          <span class="text-ink-gray-6">How is it tracked?</span>
          <div class="grid grid-cols-3 gap-2">
            <button
              v-for="kind in KINDS"
              :key="kind.value"
              class="rounded-lg border px-3 py-2 text-left"
              :class="form.kind === kind.value ? 'border-outline-blue-3 bg-surface-blue-2' : 'border-outline-gray-2 hover:border-outline-gray-4'"
              @click="form.kind = kind.value"
            >
              <div class="font-medium text-ink-gray-9">{{ kind.value }}</div>
              <div class="text-xs text-ink-gray-5">{{ kind.hint }}</div>
            </button>
          </div>
        </div>

        <label class="grid gap-1">
          <span class="text-ink-gray-6">Model name</span>
          <input v-model="form.model" class="h-8 rounded-md border border-outline-gray-3 px-2.5 outline-none focus:border-outline-blue-3" placeholder="e.g. LED Wall Panel 3.9mm" />
        </label>

        <div class="grid grid-cols-3 gap-3">
          <label class="grid gap-1">
            <span class="text-ink-gray-6">Category</span>
            <select v-model="form.category" class="h-8 rounded-md border border-outline-gray-3 bg-surface-white px-2 py-0">
              <option value="" disabled>Choose…</option>
              <option v-for="name in facets.categories" :key="name" :value="name">{{ name }}</option>
            </select>
          </label>
          <label class="grid gap-1">
            <span class="text-ink-gray-6">Type</span>
            <select v-model="form.type" class="h-8 rounded-md border border-outline-gray-3 bg-surface-white px-2 py-0">
              <option value="" disabled>Choose…</option>
              <option v-for="name in facets.types" :key="name" :value="name">{{ name }}</option>
            </select>
          </label>
          <LinkPicker v-model="form.brand" label="Brand" doctype="Brand" />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <LinkPicker v-model="form.uom" label="Unit of measure (default Nos)" doctype="UOM" />
          <label v-if="form.kind !== 'Bulk'" class="grid gap-1">
            <span class="text-ink-gray-6">Serial digits</span>
            <select v-model="form.digits" class="h-8 rounded-md border border-outline-gray-3 bg-surface-white px-2 py-0">
              <option v-for="n in ['1', '2', '3', '4']" :key="n" :value="n">{{ n }} digits — {{ example(n) }}</option>
            </select>
          </label>
        </div>

        <p v-if="form.kind !== 'Bulk' && preview" class="rounded-md bg-surface-gray-1 px-3 py-2 text-xs text-ink-gray-6">
          Item code and serial prefix: <span class="font-mono text-ink-gray-9">{{ preview }}</span>
        </p>

        <div class="mt-1 flex justify-end gap-2">
          <Button label="Cancel" @click="open = false" />
          <Button variant="solid" label="Create item" :disabled="!ready" :loading="busy" @click="submit" />
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { Button, Dialog, toast } from 'frappe-ui'
import LinkPicker from './LinkPicker.vue'
import { api, readError } from '../api'

const props = defineProps({ modelValue: Boolean, facets: Object })
const emit = defineEmits(['update:modelValue', 'created'])

const KINDS = [
  { value: 'Unit', hint: 'One serial number each' },
  { value: 'Box', hint: 'A case holding units' },
  { value: 'Bulk', hint: 'Counted, no serials' },
]
const BLANK = { kind: 'Unit', model: '', category: '', type: '', brand: '', uom: '', digits: '3' }

const open = computed({ get: () => props.modelValue, set: (value) => emit('update:modelValue', value) })
const form = reactive({ ...BLANK })
const busy = ref(false)

const ready = computed(() => form.model.trim() && form.category && form.type && form.brand)
const code = (value) => (value || '').replace(/[^a-zA-Z0-9]/g, '').toUpperCase()
const preview = computed(() => {
  const model = code(form.model)
  if (!model) return ''
  return form.kind === 'Unit' ? `${model}-${code(form.brand).slice(0, 2)}-${code(form.type).slice(0, 2)}` : model
})
const example = (digits) => `${preview.value || '…'}-${'0'.repeat(Number(digits) - 1)}1`

watch(open, (value) => {
  if (value) Object.assign(form, BLANK)
})

async function submit() {
  busy.value = true
  try {
    const name = await api.createItem({
      rental_model: form.model,
      item_group: form.category,
      rental_item_type: form.type,
      brand: form.brand,
      rental_tracking: form.kind,
      stock_uom: form.uom || undefined,
      rental_serial_digits: form.digits,
    })
    toast.success('Item created')
    open.value = false
    emit('created', name)
  } catch (err) {
    toast.error(readError(err))
  } finally {
    busy.value = false
  }
}
</script>
