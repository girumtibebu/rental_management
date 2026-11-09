<template>
  <PageFrame title="New movement" :subtitle="qtyFirst ? 'Pick movement type, then add items and quantities.' : 'Pick movement type, then scan equipment.'" :back-to="{ name: 'movements' }" back-label="Movements">
    <!-- Movement Type Picker: Horizontal Scrolling Pills on Mobile, Grid on Desktop -->
    <div class="flex gap-2 overflow-x-auto pb-1 sm:grid sm:grid-cols-3 xl:grid-cols-5 sm:overflow-visible">
      <button
        v-for="kind in SCAN_TYPES"
        :key="kind"
        class="flex shrink-0 items-center gap-2.5 rounded-xl border px-3.5 py-2.5 text-left transition-all active:scale-98"
        :class="type === kind ? 'border-outline-blue-5 bg-surface-blue-2 shadow-xs' : 'border-outline-gray-2 bg-surface-base hover:border-outline-gray-4'"
        @click="setType(kind)"
      >
        <span
          class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ring-1 transition-colors"
          :class="type === kind ? 'bg-surface-blue-8 text-ink-base ring-surface-blue-8' : 'bg-surface-gray-1 text-ink-gray-7 ring-outline-gray-2'"
        >
          <Icon :name="MOVEMENT_TYPES[kind].icon" :size="15" />
        </span>
        <span class="min-w-0">
          <span class="block text-xs-semibold sm:text-sm text-ink-gray-9 whitespace-nowrap">{{ MOVEMENT_TYPES[kind].label }}</span>
          <span class="hidden sm:block truncate text-[11px] text-ink-gray-5">{{ MOVEMENT_TYPES[kind].hint }}</span>
        </span>
      </button>
    </div>

    <!-- Mobile View Tabs: Items vs Details -->
    <div class="flex rounded-lg border border-outline-gray-2 bg-surface-gray-2 p-1 lg:hidden">
      <button
        class="flex-1 rounded-md py-1.5 text-xs-semibold transition-all"
        :class="mobileTab === 'scan' ? 'bg-surface-base text-ink-gray-9 shadow-xs' : 'text-ink-gray-6'"
        @click="mobileTab = 'scan'"
      >
        {{ qtyFirst ? 'Items' : 'Scanned Items' }} ({{ items.length + bulk.length }})
      </button>
      <button
        class="flex-1 rounded-md py-1.5 text-xs-semibold transition-all"
        :class="mobileTab === 'details' ? 'bg-surface-base text-ink-gray-9 shadow-xs' : 'text-ink-gray-6'"
        @click="mobileTab = 'details'"
      >
        Destination & Notes
      </button>
    </div>

    <!-- Main Layout: Grid on Desktop, Tabbed or Stacked on Mobile -->
    <div class="grid gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      <!-- Left Column: Barcode Scanning & Items List -->
      <section
        class="flex flex-col overflow-hidden rounded-xl border border-outline-gray-2 bg-surface-base shadow-xs"
        :class="mobileTab === 'details' ? 'hidden lg:flex' : 'flex'"
      >
        <!-- Barcode Scan Input Bar -->
        <div class="border-b border-outline-gray-1 bg-surface-gray-1/40 p-3.5 sm:p-4" :class="qtyFirst ? 'order-2' : ''">
          <div v-if="qtyFirst" class="mb-2 text-xs-semibold uppercase tracking-wider text-ink-gray-6">
            Or scan units <span class="font-normal lowercase text-ink-gray-5">(optional)</span>
          </div>
          <div class="flex items-center gap-2">
            <TextInput
              ref="scanInput"
              v-model="code"
              type="search"
              size="lg"
              class="flex-1 font-mono"
              placeholder="Scan barcode or type serial…"
              autocomplete="off"
              enterkeyhint="done"
              :disabled="scanning"
              @keydown.enter.prevent="scan"
            >
              <template #prefix><Icon name="scan" :size="16" class="text-ink-gray-5" /></template>
            </TextInput>

            <!-- Mobile Camera Scan Button -->
            <button
              class="flex h-10 items-center justify-center gap-1.5 rounded-lg border border-outline-blue-4 bg-surface-blue-2 px-3 text-xs-semibold text-ink-blue-8 active:scale-95"
              title="Scan with Camera"
              @click="cameraOpen = true"
            >
              <Icon name="camera" :size="16" />
              <span class="hidden sm:inline">Camera</span>
            </button>

            <!-- Enter / Add Button -->
            <button
              class="h-10 rounded-lg bg-surface-gray-9 px-3.5 text-sm-medium text-ink-base shadow-xs disabled:opacity-40 active:scale-95"
              :disabled="!code.trim() || scanning"
              @click="scan"
            >
              {{ scanning ? 'Checking…' : 'Add' }}
            </button>
          </div>
          <div class="mt-2 flex items-center justify-between text-xs text-ink-gray-5">
            <span>Hardware USB/Bluetooth scanners supported.</span>
            <span class="font-medium text-ink-gray-7">{{ validCodes.length }} valid item{{ validCodes.length === 1 ? '' : 's' }}</span>
          </div>
        </div>

        <!-- Scanned Items List -->
        <div v-if="!qtyFirst || items.length" class="max-h-[380px] sm:max-h-[460px] overflow-y-auto" :class="qtyFirst ? 'order-3' : ''">
          <ul v-if="items.length" class="divide-y divide-outline-gray-1">
            <li
              v-for="item in items"
              :key="item.code"
              class="flex items-center gap-3 px-3.5 sm:px-4 py-2.5 hover:bg-surface-gray-1/60"
            >
              <span
                class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full"
                :class="item.ok ? 'bg-surface-green-2 text-ink-green-7' : 'bg-surface-red-2 text-ink-red-7'"
              >
                <Icon :name="item.ok ? 'check' : 'alert'" :size="13" />
              </span>
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-2">
                  <span class="font-mono text-sm-bold text-ink-gray-9">{{ item.unit?.serial_no || item.code }}</span>
                  <span v-if="item.unit" class="truncate text-xs sm:text-sm text-ink-gray-7">{{ item.unit.item_name }}</span>
                  <span v-if="item.unit?.contents" class="rounded bg-surface-gray-2 px-1.5 text-[10px] text-ink-gray-6">
                    box · {{ item.unit.contents }}
                  </span>
                </div>
                <div v-if="item.problem" class="text-xs-medium text-ink-red-6">{{ item.problem }}</div>
                <div v-else-if="item.unit" class="mt-0.5 flex flex-wrap items-center gap-1.5 text-xs text-ink-gray-5">
                  <StatusBadge :value="item.unit.status" size="sm" />
                  <StatusBadge :value="item.unit.condition" kind="condition" size="sm" />
                  <span class="truncate">{{ item.unit.location }}</span>
                </div>
              </div>
              <button
                class="flex h-8 w-8 items-center justify-center rounded-md text-ink-gray-4 hover:bg-surface-red-1 hover:text-ink-red-6 active:scale-95"
                title="Remove"
                @click="remove(item)"
              >
                <Icon name="close" :size="14" />
              </button>
            </li>
          </ul>

          <div v-else class="px-4 py-12 text-center text-sm text-ink-gray-5">
            <Icon name="scan" :size="28" class="mx-auto mb-2 text-ink-gray-4" />
            <div class="font-medium">Nothing scanned yet</div>
            <p class="mt-1 text-xs text-ink-gray-4">Scan a barcode or use the camera to start adding equipment.</p>
          </div>
        </div>

        <!-- Bulk Items Section -->
        <div v-if="canBulk" class="border-outline-gray-1 bg-surface-gray-1/30 p-3.5 sm:p-4" :class="qtyFirst ? 'order-1 border-b' : 'border-t'">
          <div class="mb-2 text-xs-semibold uppercase tracking-wider text-ink-gray-6">
            {{ qtyFirst ? 'Items and quantities' : 'Bulk items' }}
            <span v-if="!qtyFirst" class="font-normal lowercase text-ink-gray-5">(counted, not serialized)</span>
          </div>
          <ul v-if="bulk.length" class="mb-2 flex flex-col gap-1.5">
            <li
              v-for="(row, index) in bulk"
              :key="row.item_code"
              class="flex items-center justify-between rounded-lg border border-outline-gray-2 bg-surface-base px-3 py-2 text-sm shadow-2xs"
            >
              <span class="flex-1 truncate font-medium text-ink-gray-8">{{ row.item_code }}</span>
              <span class="tabular font-bold text-ink-gray-9 mr-3">× {{ row.qty }}</span>
              <button class="text-ink-gray-4 hover:text-ink-red-6" @click="bulk.splice(index, 1)">
                <Icon name="close" :size="13" />
              </button>
            </li>
          </ul>
          <div class="flex items-end gap-2">
            <div class="flex-1">
              <LinkPicker v-model="bulkDraft.item_code" doctype="Item" :filters="BULK_FILTERS" placeholder="Select item…" />
            </div>
            <TextInput v-model="bulkDraft.qty" type="number" min="1" class="w-16 sm:w-20" />
            <Button size="sm" :disabled="!bulkDraft.item_code || !(Number(bulkDraft.qty) > 0)" @click="addBulk">Add</Button>
          </div>
        </div>
      </section>

      <!-- Right Column: Details & Submission -->
      <section
        class="flex flex-col gap-3 rounded-xl border border-outline-gray-2 bg-surface-base p-4 shadow-xs"
        :class="mobileTab === 'scan' ? 'hidden lg:flex' : 'flex'"
      >
        <div class="flex items-center justify-between border-b border-outline-gray-1 pb-2.5">
          <h2 class="text-sm-bold text-ink-gray-9">{{ MOVEMENT_TYPES[type].label }} Details</h2>
          <span class="text-xs text-ink-gray-5">{{ validCodes.length }} unit{{ validCodes.length === 1 ? '' : 's' }} selected</span>
        </div>

        <FormControl
          v-if="goesOut"
          v-model="to"
          :label="type === 'CHECK_OUT' ? 'Destination (Event or Venue)' : 'Destination'"
          :required="type === 'CHECK_OUT'"
          :placeholder="type === 'CHECK_OUT' ? 'e.g. Skylight Hall, Gala Dinner' : 'Repair Shop'"
        />
        <p v-else class="rounded-lg bg-surface-gray-1 p-3 text-xs text-ink-gray-7 border border-outline-gray-2">
          {{ type === 'LOST' ? 'These units will be marked as missing / lost.' : 'Equipment returns to the warehouse.' }}
        </p>

        <FormControl v-if="goesOut" v-model="issuedTo" label="Issued to" placeholder="Person or crew receiving equipment" />
        <FormControl v-else-if="type !== 'LOST'" v-model="receivedBy" label="Received by" placeholder="Staff member checking equipment in" />

        <FormControl v-model="note" type="textarea" :rows="3" label="Operation note" placeholder="Condition notes, accessories included, etc." />

        <!-- Desktop Action Area -->
        <div class="mt-auto hidden lg:block border-t border-outline-gray-1 pt-3">
          <div class="mb-3 flex items-baseline justify-between text-sm">
            <span class="text-ink-gray-6">Ready to move</span>
            <span class="text-lg-bold tabular text-ink-gray-9">
              {{ validCodes.length }}
              <span class="text-xs text-ink-gray-5">unit{{ validCodes.length === 1 ? '' : 's' }}<template v-if="bulk.length"> + {{ bulk.length }} bulk</template></span>
            </span>
          </div>
          <p v-if="blocked" class="mb-2 text-xs-medium text-ink-amber-8">
            {{ blocked }} scanned item{{ blocked === 1 ? '' : 's' }} can't be moved and will be skipped.
          </p>
          <Button variant="solid" class="w-full" :disabled="!canSubmit" :loading="busy" @click="submit">
            {{ MOVEMENT_TYPES[type].label }} {{ validCodes.length + bulk.length ? `(${validCodes.length + bulk.length})` : '' }}
          </Button>
          <p v-if="why" class="mt-2 text-center text-xs text-ink-gray-5">{{ why }}</p>
        </div>
      </section>
    </div>

    <!-- Sticky Mobile Bottom Action Bar (Fixed above bottom tabs) -->
    <div class="fixed bottom-16 inset-x-0 z-20 border-t border-outline-gray-2 bg-surface-base/95 p-3 backdrop-blur-md lg:hidden shadow-lg">
      <div class="flex items-center gap-2">
        <button
          v-if="mobileTab === 'scan'"
          class="flex h-11 flex-1 items-center justify-between rounded-xl border border-outline-gray-3 bg-surface-gray-1 px-3 text-left active:bg-surface-gray-2"
          @click="mobileTab = 'details'"
        >
          <div>
            <div class="text-xs-semibold text-ink-gray-9">
              {{ validCodes.length }} unit{{ validCodes.length === 1 ? '' : 's' }} ready
            </div>
            <div class="text-[10px] text-ink-gray-5">{{ needsDestination ? 'Needs destination' : 'Tap to edit details' }}</div>
          </div>
          <Icon name="chevright" :size="14" class="text-ink-gray-4" />
        </button>

        <button
          class="flex h-11 items-center justify-center gap-2 rounded-xl bg-surface-blue-8 px-4 font-semibold text-ink-base shadow-md active:scale-95 disabled:opacity-50"
          :class="mobileTab === 'details' ? 'w-full' : 'shrink-0'"
          :disabled="!canSubmit || busy"
          @click="submit"
        >
          <Icon :name="MOVEMENT_TYPES[type].icon" :size="16" />
          <span>{{ MOVEMENT_TYPES[type].label }} {{ validCodes.length + bulk.length ? `(${validCodes.length + bulk.length})` : '' }}</span>
        </button>
      </div>
      <p v-if="why" class="mt-1 text-center text-[10px] text-ink-amber-8">{{ why }}</p>
    </div>

    <!-- Live Camera Scanner Modal -->
    <MobileScannerModal v-model="cameraOpen" @scanned="handleCameraScan" />
  </PageFrame>
</template>

<script setup>
import { computed, inject, nextTick, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, FormControl, TextInput, toast } from 'frappe-ui'
import Icon from '../components/Icon.vue'
import LinkPicker from '../components/LinkPicker.vue'
import MobileScannerModal from '../components/MobileScannerModal.vue'
import PageFrame from '../components/PageFrame.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { api, readError } from '../api'
import { MOVEMENT_TYPES, SCAN_TYPES } from '../theme'
import { bulkFirst, currentWorkspace } from '../workspace'
import {
  playScanErrorBeep,
  playScanSuccessBeep,
  triggerHaptic,
} from '../scannerUtils'

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
const bulkDraft = reactive({ item_code: '', qty: 1 })
// Quantity-first workspaces can move any counted stock item, flagged as rental or not.
const BULK_FILTERS = computed(() =>
  bulkFirst.value
    ? {
        is_stock_item: 1,
        has_serial_no: 0,
        disabled: 0,
        ...(currentWorkspace.value?.item_group ? { item_group: ['descendants of (inclusive)', currentWorkspace.value.item_group] } : {}),
      }
    : { is_rental_item: 1, rental_tracking: 'Bulk', disabled: 0 },
)
const to = ref(type.value === 'MAINTENANCE_OUT' ? 'Repair Shop' : '')
const issuedTo = ref('')
const receivedBy = ref('')
const note = ref('')

const mobileTab = ref('scan')
const cameraOpen = ref(false)

const goesOut = computed(() => ['CHECK_OUT', 'MAINTENANCE_OUT', 'LOST'].includes(type.value) && type.value !== 'LOST')
const canBulk = computed(() => ['CHECK_OUT', 'CHECK_IN'].includes(type.value))
const qtyFirst = computed(() => bulkFirst.value && canBulk.value)
const validCodes = computed(() => items.value.filter((item) => item.ok).map((item) => item.unit.serial_no))
const blocked = computed(() => items.value.filter((item) => !item.ok).length)
const needsDestination = computed(() => type.value === 'CHECK_OUT' && !to.value.trim())
const canSubmit = computed(() => (validCodes.value.length || bulk.value.length) && !needsDestination.value)
const why = computed(() => {
  if (!validCodes.value.length && !bulk.value.length) return qtyFirst.value ? 'Add at least one item to continue.' : 'Scan at least one unit to continue.'
  if (needsDestination.value) return 'Please set destination before checkout.'
  return ''
})

const focusScan = () => nextTick(() => scanInput.value?.$el?.querySelector('input')?.focus())

async function check(value) {
  const result = await api.checkScan(value, type.value)
  return { code: value, ok: result.ok, problem: result.problem, unit: result.unit }
}

async function addUnitByCode(value) {
  const clean = String(value || '').trim()
  if (!clean) return
  if (items.value.some((item) => item.code.toLowerCase() === clean.toLowerCase() || item.unit?.serial_no?.toLowerCase() === clean.toLowerCase())) {
    playScanErrorBeep()
    triggerHaptic('error')
    return toast.info(`${clean} is already in the list`)
  }

  scanning.value = true
  try {
    const row = await check(clean)
    items.value.unshift(row)
    if (row.ok) {
      playScanSuccessBeep()
      triggerHaptic('success')
    } else {
      playScanErrorBeep()
      triggerHaptic('error')
      toast.error(`${clean}: ${row.problem}`)
    }
  } catch (err) {
    playScanErrorBeep()
    triggerHaptic('error')
    toast.error(readError(err))
  } finally {
    scanning.value = false
    focusScan()
  }
}

async function scan() {
  const value = code.value.trim()
  if (!value) return
  code.value = ''
  await addUnitByCode(value)
}

function handleCameraScan(unit) {
  if (unit && unit.serial_no) {
    addUnitByCode(unit.serial_no)
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
  const qty = Number(bulkDraft.qty) // text inputs hand back strings
  const existing = bulk.value.find((row) => row.item_code === bulkDraft.item_code)
  if (existing) existing.qty += qty
  else bulk.value.push({ item_code: bulkDraft.item_code, qty })
  bulkDraft.item_code = ''
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
    await addUnitByCode(String(route.query.unit))
  }
  focusScan()
})
</script>
