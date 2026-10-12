<template>
  <PageFrame title="New movement" subtitle="Pick what is happening, then scan the equipment." :back-to="{ name: 'movements' }" back-label="Movements">
    <div class="grid gap-2 sm:grid-cols-3 xl:grid-cols-5">
      <button
        v-for="kind in SCAN_TYPES"
        :key="kind"
        class="flex items-center gap-3 rounded-lg border px-3.5 py-3 text-left"
        :class="type === kind ? 'border-outline-blue-3 bg-surface-blue-2' : 'border-outline-gray-2 bg-surface-white hover:border-outline-gray-4'"
        @click="setType(kind)"
      >
        <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-surface-white text-ink-gray-7 ring-1 ring-outline-gray-2">
          <Icon :name="MOVEMENT_TYPES[kind].icon" :size="15" />
        </span>
        <span class="min-w-0">
          <span class="block text-sm font-medium text-ink-gray-9">{{ MOVEMENT_TYPES[kind].label }}</span>
          <span class="block truncate text-[11px] text-ink-gray-5">{{ MOVEMENT_TYPES[kind].hint }}</span>
        </span>
      </button>
    </div>

    <div class="grid gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      <section class="overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-white">
        <div class="border-b border-outline-gray-1 p-4">
          <div class="relative">
            <Icon name="scan" :size="16" class="pointer-events-none absolute left-3 top-[13px] text-ink-gray-5" />
            <input
              ref="scanInput"
              v-model="code"
              class="h-10 w-full rounded-lg border border-outline-gray-3 bg-surface-white pl-10 pr-4 text-base outline-none focus:border-outline-blue-3"
              placeholder="Scan a barcode, or type a serial and press Enter"
              autocomplete="off"
              :disabled="scanning"
              @keydown.enter.prevent="scan"
            />
          </div>
          <p class="mt-1.5 text-xs text-ink-gray-5">Each scan is checked straight away. Problems stay in the list so you can see why, but they are not moved.</p>
        </div>

        <ul v-if="items.length" class="divide-y divide-outline-gray-1">
          <li v-for="item in items" :key="item.code" class="flex items-center gap-3 px-4 py-2.5">
            <span
              class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full"
              :class="item.ok ? 'bg-surface-green-2 text-ink-green-6' : 'bg-surface-red-2 text-ink-red-6'"
            >
              <Icon :name="item.ok ? 'check' : 'alert'" :size="12" />
            </span>
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <span class="font-mono text-sm font-medium text-ink-gray-9">{{ item.unit?.unit_serial_number || item.code }}</span>
                <span v-if="item.unit" class="truncate text-sm text-ink-gray-7">{{ item.unit.unit_name }}</span>
              </div>
              <div v-if="item.problem" class="text-xs text-ink-red-6">{{ item.problem }}</div>
              <div v-else-if="item.unit" class="flex items-center gap-1.5 text-xs text-ink-gray-5">
                <StatusBadge :value="item.unit.movement_status" /> <StatusBadge :value="item.unit.unit_condition" kind="condition" />
                <span>{{ item.unit.location }}</span>
              </div>
            </div>
            <button class="text-ink-gray-4 hover:text-ink-red-6" title="Remove" @click="remove(item)"><Icon name="close" :size="13" /></button>
          </li>
        </ul>
        <div v-else class="px-4 py-10 text-center text-sm text-ink-gray-5">
          <Icon name="scan" :size="22" class="mx-auto mb-2 text-ink-gray-4" />
          Nothing scanned yet.
        </div>

        <div v-if="canBulk" class="border-t border-outline-gray-1 p-4">
          <div class="mb-2 text-sm font-medium text-ink-gray-8">Bulk items <span class="text-xs font-normal text-ink-gray-5">(counted, not scanned)</span></div>
          <ul v-if="bulk.length" class="mb-2 flex flex-col gap-1">
            <li v-for="(row, index) in bulk" :key="row.template" class="flex items-center gap-2 rounded-md bg-surface-gray-1 px-3 py-1.5 text-sm">
              <span class="flex-1 truncate">{{ row.template }}</span>
              <span class="tabular font-medium">× {{ row.qty }}</span>
              <button class="text-ink-gray-4 hover:text-ink-red-6" @click="bulk.splice(index, 1)"><Icon name="close" :size="12" /></button>
            </li>
          </ul>
          <div class="flex items-end gap-2">
            <div class="flex-1"><LinkPicker v-model="bulkDraft.template" doctype="Rental Item Template" placeholder="Search a bulk item…" /></div>
            <input v-model.number="bulkDraft.qty" type="number" min="1" class="h-8 w-20 rounded-md border border-outline-gray-3 px-2 text-sm" />
            <Button :disabled="!bulkDraft.template || !(bulkDraft.qty > 0)" @click="addBulk">Add</Button>
          </div>
        </div>
      </section>

      <section class="flex flex-col gap-3 rounded-lg border border-outline-gray-2 bg-surface-white p-4">
        <h2 class="text-sm font-semibold text-ink-gray-9">{{ MOVEMENT_TYPES[type].label }}</h2>

        <label v-if="goesOut" class="grid gap-1 text-sm">
          <span class="text-ink-gray-6">{{ type === 'CHECK_OUT' ? 'Going to (event or venue)' : 'Going to' }} <span v-if="type === 'CHECK_OUT'" class="text-ink-red-6">*</span></span>
          <input v-model="to" class="h-8 rounded-md border border-outline-gray-3 px-2.5 outline-none focus:border-outline-blue-3" :placeholder="type === 'CHECK_OUT' ? 'e.g. Gala Dinner, Skylight Hall' : 'Repair Shop'" />
        </label>
        <p v-else class="rounded-md bg-surface-gray-1 px-3 py-2 text-xs text-ink-gray-6">
          {{ type === 'LOST' ? 'These units will be marked missing.' : 'Returns to the main warehouse.' }}
        </p>

        <label v-if="goesOut" class="grid gap-1 text-sm">
          <span class="text-ink-gray-6">Issued to</span>
          <input v-model="issuedTo" class="h-8 rounded-md border border-outline-gray-3 px-2.5 outline-none focus:border-outline-blue-3" placeholder="Person or crew taking it" />
        </label>
        <label v-else-if="type !== 'LOST'" class="grid gap-1 text-sm">
          <span class="text-ink-gray-6">Received by</span>
          <input v-model="receivedBy" class="h-8 rounded-md border border-outline-gray-3 px-2.5 outline-none focus:border-outline-blue-3" placeholder="Who checked it in" />
        </label>

        <label class="grid gap-1 text-sm">
          <span class="text-ink-gray-6">Note</span>
          <textarea v-model="note" rows="3" class="rounded-md border border-outline-gray-3 p-2.5 outline-none focus:border-outline-blue-3" placeholder="Anything the next person should know" />
        </label>

        <div class="mt-auto border-t border-outline-gray-1 pt-3">
          <div class="mb-3 flex items-baseline justify-between text-sm">
            <span class="text-ink-gray-6">Ready to move</span>
            <span class="text-lg font-semibold tabular text-ink-gray-9">{{ validCodes.length }} <span class="text-sm font-normal text-ink-gray-5">unit{{ validCodes.length === 1 ? '' : 's' }}<template v-if="bulk.length"> + {{ bulk.length }} bulk</template></span></span>
          </div>
          <p v-if="blocked" class="mb-2 text-xs text-ink-amber-8">{{ blocked }} scanned item{{ blocked === 1 ? '' : 's' }} can't be moved and will be left out.</p>
          <Button variant="solid" class="w-full" :disabled="!canSubmit" :loading="busy" @click="submit">
            {{ MOVEMENT_TYPES[type].label }} {{ validCodes.length + bulk.length ? `(${validCodes.length + bulk.length})` : '' }}
          </Button>
          <p v-if="why" class="mt-2 text-center text-xs text-ink-gray-5">{{ why }}</p>
        </div>
      </section>
    </div>
  </PageFrame>
</template>

<script setup>
import { computed, inject, nextTick, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, toast } from 'frappe-ui'
import Icon from '../components/Icon.vue'
import LinkPicker from '../components/LinkPicker.vue'
import PageFrame from '../components/PageFrame.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { api, readError } from '../api'
import { MOVEMENT_TYPES, SCAN_TYPES } from '../theme'

const route = useRoute()
const router = useRouter()
const { refreshSummary } = inject('rental')

const type = ref(SCAN_TYPES.includes(route.query.type) ? route.query.type : 'CHECK_OUT')
const scanInput = ref(null)
const code = ref('')
const scanning = ref(false)
const busy = ref(false)
const items = ref([])
const bulk = ref([])
const bulkDraft = reactive({ template: '', qty: 1 })
const to = ref(type.value === 'MAINTENANCE_OUT' ? 'Repair Shop' : '')
const issuedTo = ref('')
const receivedBy = ref('')
const note = ref('')

const goesOut = computed(() => ['CHECK_OUT', 'MAINTENANCE_OUT', 'LOST'].includes(type.value) && type.value !== 'LOST')
const canBulk = computed(() => ['CHECK_OUT', 'CHECK_IN'].includes(type.value))
const validCodes = computed(() => items.value.filter((item) => item.ok).map((item) => item.unit.unit_serial_number || item.code))
const blocked = computed(() => items.value.filter((item) => !item.ok).length)
const needsDestination = computed(() => type.value === 'CHECK_OUT' && !to.value.trim())
const canSubmit = computed(() => (validCodes.value.length || bulk.value.length) && !needsDestination.value)
const why = computed(() => {
  if (!validCodes.value.length && !bulk.value.length) return 'Scan at least one unit to continue.'
  if (needsDestination.value) return 'Say where the equipment is going.'
  return ''
})

const focusScan = () => nextTick(() => scanInput.value?.focus())

async function check(value) {
  const result = await api.checkScan(value, type.value)
  return { code: value, ok: result.ok, problem: result.problem, unit: result.unit }
}

async function scan() {
  const value = code.value.trim()
  if (!value) return
  if (items.value.some((item) => item.code.toLowerCase() === value.toLowerCase() || item.unit?.unit_serial_number?.toLowerCase() === value.toLowerCase())) {
    code.value = ''
    return toast.info(`${value} is already in the list`)
  }
  scanning.value = true
  try {
    const row = await check(value)
    items.value.unshift(row)
    if (!row.ok) toast.error(`${value}: ${row.problem}`)
    code.value = ''
  } catch (err) {
    toast.error(readError(err))
  } finally {
    scanning.value = false
    focusScan()
  }
}

async function setType(kind) {
  if (kind === type.value) return
  type.value = kind
  to.value = kind === 'MAINTENANCE_OUT' ? 'Repair Shop' : ''
  items.value = await Promise.all(items.value.map((item) => check(item.code).catch(() => item)))
  focusScan()
}

const remove = (item) => (items.value = items.value.filter((row) => row !== item))

function addBulk() {
  const existing = bulk.value.find((row) => row.template === bulkDraft.template)
  if (existing) existing.qty += bulkDraft.qty
  else bulk.value.push({ template: bulkDraft.template, qty: bulkDraft.qty })
  bulkDraft.template = ''
  bulkDraft.qty = 1
}

async function submit() {
  busy.value = true
  try {
    const name = await api.createMovement({
      transaction_type: type.value,
      units: validCodes.value,
      bulk: bulk.value,
      to_location: goesOut.value ? to.value : undefined,
      issued_to: issuedTo.value || undefined,
      received_by: receivedBy.value || undefined,
      note: note.value || undefined,
    })
    toast.success(`${MOVEMENT_TYPES[type.value].label} saved`)
    refreshSummary()
    router.push({ name: 'movement', params: { name } })
  } catch (err) {
    toast.error(readError(err))
  } finally {
    busy.value = false
  }
}

onMounted(async () => {
  if (route.query.unit) {
    code.value = String(route.query.unit)
    await scan()
  }
  focusScan()
})
</script>
