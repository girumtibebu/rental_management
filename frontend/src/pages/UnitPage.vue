<template>
  <PageFrame
    :title="unit ? unit.serial_no : 'Unit'"
    :subtitle="unit ? unit.item_name || '' : ''"
    :back-to="{ name: 'units' }"
    back-label="All units"
  >
    <template #actions>
      <template v-if="data">
        <StatusBadge :value="unit.status" size="md" />
        <StatusBadge :value="unit.condition" kind="condition" size="md" />
        <div class="hidden sm:flex items-center gap-2">
          <Button v-for="action in moveActions" :key="action.type" size="sm" :disabled="!data.can.move" @click="move(action.type)">
            <template #prefix><Icon :name="action.icon" :size="13" /></template>{{ action.label }}
          </Button>
          <Button size="sm" :disabled="!data.can.maintain || Boolean(data.open_ticket)" @click="flagOpen = true">
            <template #prefix><Icon name="alert" :size="13" /></template>Report a problem
          </Button>
          <a :href="`/desk/serial-no/${encodeURIComponent(unit.name)}`" target="_blank">
            <Button size="sm" variant="ghost"><template #prefix><Icon name="external" :size="13" /></template>Desk</Button>
          </a>
        </div>
      </template>
    </template>

    <div v-if="!data" class="p-10 text-center text-sm text-ink-gray-5">{{ failure || 'Loading…' }}</div>

    <div v-else class="flex flex-col gap-4">
      <!-- Mobile Quick Actions Bar -->
      <div v-if="moveActions.length || data.can.maintain" class="flex flex-wrap gap-2 sm:hidden">
        <button
          v-for="action in moveActions"
          :key="action.type"
          class="flex flex-1 items-center justify-center gap-1.5 rounded-xl border border-outline-blue-3 bg-surface-blue-2 py-2.5 px-3 text-xs font-bold text-ink-blue-8 active:scale-95 shadow-2xs disabled:opacity-50"
          :disabled="!data.can.move"
          @click="move(action.type)"
        >
          <Icon :name="action.icon" :size="14" />
          <span>{{ action.label }}</span>
        </button>
        <button
          class="flex items-center justify-center gap-1.5 rounded-xl border border-outline-gray-2 bg-surface-white py-2.5 px-3 text-xs font-semibold text-ink-amber-8 active:scale-95 shadow-2xs disabled:opacity-50"
          :disabled="!data.can.maintain || Boolean(data.open_ticket)"
          @click="flagOpen = true"
        >
          <Icon name="alert" :size="14" />
          <span>Report problem</span>
        </button>
      </div>

      <div class="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <div class="flex flex-col gap-4">
        <div
          v-if="data.open_ticket"
          class="flex items-center gap-3 rounded-lg border border-outline-amber-3 bg-surface-amber-2 px-4 py-2.5 text-sm text-ink-amber-8"
        >
          <Icon name="wrench" :size="14" />
          <span class="flex-1">Open maintenance ticket {{ data.open_ticket.name }} — {{ data.open_ticket.workflow_state }}</span>
          <router-link :to="{ name: 'maintenance' }" class="font-medium underline">Open board</router-link>
        </div>

        <section class="rounded-lg border border-outline-gray-2 bg-surface-white">
          <header class="border-b border-outline-gray-1 px-4 py-2.5 text-sm font-semibold text-ink-gray-9">Details</header>
          <dl class="grid grid-cols-[110px_1fr] gap-y-2 px-4 py-3 text-sm">
            <dt class="text-ink-gray-5">Equipment</dt>
            <dd>
              <router-link :to="{ name: 'item', params: { name: unit.item_code } }" class="text-ink-blue-6 hover:underline">
                {{ data.item.item_name || unit.item_code }}
              </router-link>
            </dd>
            <dt class="text-ink-gray-5">Category</dt>
            <dd>{{ data.item.item_group || '—' }} · {{ data.item.brand || '' }}</dd>
            <dt class="text-ink-gray-5">Tracked as</dt>
            <dd>{{ unit.kind }}</dd>
            <dt class="text-ink-gray-5">Location</dt>
            <dd>{{ unit.location || '—' }}</dd>
            <dt class="text-ink-gray-5">Warehouse</dt>
            <dd class="text-ink-gray-7">{{ unit.warehouse || 'Not in stock' }}</dd>
            <dt class="text-ink-gray-5">Storage</dt>
            <dd class="font-mono text-xs">{{ unit.storage || '—' }}</dd>
            <template v-if="data.parent_box">
              <dt class="text-ink-gray-5">In box</dt>
              <dd class="flex items-center gap-2">
                <router-link :to="{ name: 'unit', params: { name: data.parent_box } }" class="font-mono text-xs text-ink-blue-6 hover:underline">{{ data.parent_box }}</router-link>
                <button v-if="data.can.write" class="text-xs text-ink-gray-5 hover:text-ink-red-6" @click="unpack(unit.name)">Take out</button>
              </dd>
            </template>
            <dt class="text-ink-gray-5">Added</dt>
            <dd class="text-ink-gray-7">{{ fullDate(unit.creation) }} · {{ userName(unit.owner) }}</dd>
          </dl>
        </section>

        <section v-if="unit.status === 'Warehouse' && data.can.write" class="rounded-lg border border-outline-gray-2 bg-surface-white">
          <header class="border-b border-outline-gray-1 px-4 py-2.5 text-sm font-semibold text-ink-gray-9">Warehouse storage</header>
          <div class="grid grid-cols-2 gap-3 px-4 py-3">
            <LinkPicker v-model="place.rental_zone" label="Zone" doctype="Zone" creatable />
            <LinkPicker v-model="place.rental_aisle" label="Aisle" doctype="Aisle" creatable />
            <LinkPicker v-model="place.rental_section" label="Section" doctype="Section" creatable />
            <LinkPicker v-model="place.rental_level" label="Level" doctype="Level" creatable />
            <LinkPicker v-model="place.rental_position" label="Position" doctype="Position" creatable />
          </div>
          <div class="flex justify-end border-t border-outline-gray-1 px-4 py-2.5">
            <Button size="sm" variant="solid" :loading="saving" @click="saveStorage">Save storage</Button>
          </div>
        </section>

        <section v-if="unit.kind === 'Box'" class="rounded-lg border border-outline-gray-2 bg-surface-white">
          <header class="border-b border-outline-gray-1 px-4 py-2.5 text-sm font-semibold text-ink-gray-9">In this box ({{ data.contents.length }})</header>
          <ul v-if="data.contents.length" class="divide-y divide-outline-gray-1">
            <li v-for="child in data.contents" :key="child.name" class="flex items-center gap-3 px-4 py-2 text-sm">
              <router-link :to="{ name: 'unit', params: { name: child.name } }" class="font-mono text-xs text-ink-blue-6 hover:underline">{{ child.serial_no }}</router-link>
              <span class="flex-1 truncate text-ink-gray-6">{{ child.item_name }}</span>
              <StatusBadge :value="child.condition" kind="condition" />
              <button v-if="data.can.write" class="text-ink-gray-4 hover:text-ink-red-6" title="Take out" @click="unpack(child.name)"><Icon name="close" :size="12" /></button>
            </li>
          </ul>
          <div v-if="data.can.write" class="border-t border-outline-gray-1 p-3">
            <input
              v-model="packCode"
              class="h-8 w-full rounded-md border border-outline-gray-3 px-2.5 font-mono text-sm outline-none focus:border-outline-blue-3"
              placeholder="Scan a unit to pack it into this box"
              autocomplete="off"
              :disabled="saving"
              @keydown.enter.prevent="packUnit"
            />
          </div>
        </section>
      </div>

      <section class="rounded-lg border border-outline-gray-2 bg-surface-white">
        <header class="border-b border-outline-gray-1 px-4 py-2.5 text-sm font-semibold text-ink-gray-9">History</header>
        <ol v-if="data.history.length" class="px-4 py-3">
          <li v-for="(event, index) in data.history" :key="event.kind + event.name" class="relative flex gap-3 pb-4 last:pb-0">
            <div class="flex flex-col items-center">
              <span class="flex h-7 w-7 items-center justify-center rounded-full" :class="event.kind === 'Movement' ? 'bg-surface-blue-2 text-ink-blue-6' : 'bg-surface-amber-2 text-ink-amber-6'">
                <Icon :name="event.kind === 'Movement' ? 'truck' : 'wrench'" :size="13" />
              </span>
              <div v-if="index < data.history.length - 1" class="mt-1 w-px flex-1 bg-outline-gray-2" />
            </div>
            <div class="min-w-0 flex-1 pt-0.5 text-sm">
              <div class="flex flex-wrap items-center gap-2">
                <StatusBadge v-if="event.kind === 'Movement'" :value="event.status" kind="type" />
                <StatusBadge v-else :value="event.status" kind="ticket" />
                <router-link v-if="event.kind === 'Movement'" :to="{ name: 'movement', params: { name: event.reference_name } }" class="font-mono text-xs text-ink-blue-6 hover:underline">{{ event.reference_name }}</router-link>
                <span v-else class="font-mono text-xs text-ink-gray-5">{{ event.reference_name }}</span>
                <span class="text-xs text-ink-gray-5" :title="fullDate(event.when)">{{ timeAgo(event.when) }} · {{ userName(event.owner) }}</span>
              </div>
              <div v-if="event.from_location || event.to_location" class="mt-0.5 text-ink-gray-7">{{ event.from_location || '—' }} → {{ event.to_location || '—' }}</div>
              <div v-if="event.detail" class="mt-0.5 text-xs italic text-ink-gray-5">“{{ event.detail }}”</div>
            </div>
          </li>
        </ol>
        <div v-else class="p-8 text-center text-sm text-ink-gray-5">No history yet. Movements and repairs show up here.</div>
      </section>
      </div>
    </div>

    <FlagProblemDialog v-model="flagOpen" :serial="unit?.serial_no" @created="afterTicket" />
  </PageFrame>
</template>

<script setup>
import { computed, inject, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, toast } from 'frappe-ui'
import FlagProblemDialog from '../components/FlagProblemDialog.vue'
import Icon from '../components/Icon.vue'
import LinkPicker from '../components/LinkPicker.vue'
import PageFrame from '../components/PageFrame.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { api, readError } from '../api'
import { fullDate, timeAgo, userName } from '../format'

const route = useRoute()
const router = useRouter()
const { refreshSummary } = inject('rental')

const data = ref(null)
const failure = ref('')
const flagOpen = ref(false)
const saving = ref(false)
const packCode = ref('')
const place = reactive({ rental_zone: '', rental_aisle: '', rental_section: '', rental_level: '', rental_position: '' })

const unit = computed(() => data.value?.unit)

const ACTIONS = {
  Warehouse: [
    { type: 'CHECK_OUT', label: 'Check out', icon: 'out' },
    { type: 'MAINTENANCE_OUT', label: 'Send to repair', icon: 'wrench' },
  ],
  'At Event': [{ type: 'CHECK_IN', label: 'Check in', icon: 'in' }],
  'In Maintenance': [{ type: 'MAINTENANCE_IN', label: 'Back from repair', icon: 'check' }],
  Missing: [{ type: 'CHECK_IN', label: 'Found — check in', icon: 'in' }],
}
const moveActions = computed(() => (data.value?.parent_box ? [] : ACTIONS[unit.value?.status] || []))

function fill(result) {
  data.value = result
  for (const key of Object.keys(place)) place[key] = result.unit[key] || ''
}

async function load() {
  try {
    fill(await api.getUnit(route.params.name))
  } catch (err) {
    failure.value = readError(err)
  }
}

const move = (type) => router.push({ name: 'movement-new', query: { type, unit: unit.value.serial_no } })

async function save(request, message) {
  saving.value = true
  try {
    await request()
    toast.success(message)
    await load()
  } catch (err) {
    toast.error(readError(err))
  } finally {
    saving.value = false
  }
}

const saveStorage = () => save(() => api.updateStorage(unit.value.name, place), 'Storage saved')

function packUnit() {
  const code = packCode.value.trim()
  if (!code) return
  save(() => api.pack(unit.value.name, [code]), `${code} packed`).then(() => (packCode.value = ''))
}

const unpack = (name) => save(() => api.pack('', [name]), `${name} taken out`)

async function afterTicket() {
  await load()
  refreshSummary()
}

onMounted(load)
</script>
