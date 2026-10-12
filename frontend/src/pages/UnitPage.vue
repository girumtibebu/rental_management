<template>
  <PageFrame
    :title="unit ? unit.unit_serial_number || unit.name : 'Unit'"
    :subtitle="unit ? `${unit.unit_name || ''}` : ''"
    :back-to="{ name: 'units' }"
    back-label="All units"
  >
    <template #actions>
      <template v-if="data">
        <StatusBadge :value="unit.movement_status" size="md" />
        <StatusBadge :value="unit.unit_condition" kind="condition" size="md" />
        <Button v-for="action in moveActions" :key="action.type" size="sm" :disabled="!data.can.move" @click="move(action.type)">
          <template #prefix><Icon :name="action.icon" :size="13" /></template>{{ action.label }}
        </Button>
        <Button size="sm" :disabled="!data.can.maintain || Boolean(data.open_ticket)" @click="flagOpen = true">
          <template #prefix><Icon name="alert" :size="13" /></template>Report a problem
        </Button>
        <a :href="`/desk/rental-item-unit/${encodeURIComponent(unit.name)}`" target="_blank">
          <Button size="sm" variant="ghost"><template #prefix><Icon name="external" :size="13" /></template>Desk</Button>
        </a>
      </template>
    </template>

    <div v-if="!data" class="p-10 text-center text-sm text-ink-gray-5">{{ failure || 'Loading…' }}</div>

    <div v-else class="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
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
              <router-link v-if="unit.item_template" :to="{ name: 'template', params: { name: unit.item_template } }" class="text-ink-blue-6 hover:underline">
                {{ data.template.item_name || unit.item_template }}
              </router-link>
            </dd>
            <dt class="text-ink-gray-5">Category</dt>
            <dd>{{ data.template.item_category || '—' }} · {{ data.template.item_brand || '' }}</dd>
            <dt class="text-ink-gray-5">Type</dt>
            <dd>{{ data.template.rental_item_type_box || unit.unit_type }}</dd>
            <dt class="text-ink-gray-5">Location</dt>
            <dd>{{ data.location || '—' }}</dd>
            <dt class="text-ink-gray-5">Storage</dt>
            <dd>{{ data.storage || '—' }}</dd>
            <template v-if="data.parent_box">
              <dt class="text-ink-gray-5">In box</dt>
              <dd>
                <router-link :to="{ name: 'unit', params: { name: data.parent_box } }" class="font-mono text-xs text-ink-blue-6 hover:underline">{{ data.parent_box }}</router-link>
              </dd>
            </template>
            <dt class="text-ink-gray-5">Added</dt>
            <dd class="text-ink-gray-7">{{ fullDate(unit.creation) }} · {{ userName(unit.owner) }}</dd>
          </dl>
        </section>

        <section v-if="unit.movement_status === 'Warehouse' && data.can.write" class="rounded-lg border border-outline-gray-2 bg-surface-white">
          <header class="border-b border-outline-gray-1 px-4 py-2.5 text-sm font-semibold text-ink-gray-9">Warehouse storage</header>
          <div class="grid grid-cols-2 gap-3 px-4 py-3">
            <LinkPicker v-model="place.zone" label="Zone" doctype="Zone" />
            <LinkPicker v-model="place.section" label="Section" doctype="Section" />
            <LinkPicker v-model="place.level" label="Level" doctype="Level" />
            <LinkPicker v-model="place.position" label="Position" doctype="Position" />
          </div>
          <div class="flex justify-end border-t border-outline-gray-1 px-4 py-2.5">
            <Button size="sm" variant="solid" :loading="saving" @click="saveStorage">Save storage</Button>
          </div>
        </section>

        <section v-if="data.contents.length" class="rounded-lg border border-outline-gray-2 bg-surface-white">
          <header class="border-b border-outline-gray-1 px-4 py-2.5 text-sm font-semibold text-ink-gray-9">In this box ({{ data.contents.length }})</header>
          <ul class="divide-y divide-outline-gray-1">
            <li v-for="item in data.contents" :key="item.document_id">
              <router-link :to="{ name: 'unit', params: { name: item.document_id } }" class="flex items-center gap-3 px-4 py-2 text-sm hover:bg-surface-gray-1">
                <span class="font-mono text-xs text-ink-gray-8">{{ item.unit_serial_number }}</span>
                <span class="flex-1 truncate text-ink-gray-6">{{ item.unit_name }}</span>
                <StatusBadge :value="item.unit_condition" kind="condition" />
              </router-link>
            </li>
          </ul>
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

    <FlagProblemDialog v-model="flagOpen" :serial="unit?.unit_serial_number" @created="afterTicket" />
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
const place = reactive({ zone: '', section: '', level: '', position: '' })

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
const moveActions = computed(() => ACTIONS[unit.value?.movement_status] || [])

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

const move = (type) => router.push({ name: 'movement-new', query: { type, unit: unit.value.unit_serial_number || unit.value.name } })

async function saveStorage() {
  saving.value = true
  try {
    fill(await api.updateStorage(unit.value.name, place))
    toast.success('Storage saved')
  } catch (err) {
    toast.error(readError(err))
  } finally {
    saving.value = false
  }
}

async function afterTicket() {
  await load()
  refreshSummary()
}

onMounted(load)
</script>
