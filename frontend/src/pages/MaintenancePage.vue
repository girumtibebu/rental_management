<template>
  <PageFrame title="Maintenance" subtitle="Every repair ticket, from first report to finished work.">
    <template #actions>
      <Button size="sm" @click="load"><template #prefix><Icon name="refresh" :size="13" /></template>Refresh</Button>
      <Button variant="solid" size="sm" :disabled="board && !board.can.create" @click="flagOpen = true">
        <template #prefix><Icon name="plus" :size="13" /></template>Report a problem
      </Button>
    </template>

    <div v-if="!board" class="p-10 text-center text-sm text-ink-gray-5">{{ failure || 'Loading…' }}</div>

    <div v-else class="grid min-h-0 flex-1 gap-4 lg:grid-cols-3">
      <section v-for="state in board.states" :key="state" class="flex min-h-[260px] flex-col rounded-lg border border-outline-gray-2 bg-surface-gray-2/60">
        <header class="flex items-center gap-2 px-3.5 py-2.5">
          <span class="h-2 w-2 rounded-full" :class="DOT[state]" />
          <span class="text-sm font-semibold text-ink-gray-9">{{ state }}</span>
          <span class="rounded-full bg-surface-white px-2 text-xs tabular text-ink-gray-6 ring-1 ring-outline-gray-2">{{ board.columns[state].length }}</span>
        </header>
        <ul class="flex flex-1 flex-col gap-2 overflow-y-auto px-2.5 pb-2.5">
          <li v-for="ticket in board.columns[state]" :key="ticket.name">
            <button
              class="w-full rounded-lg border border-outline-gray-2 bg-surface-white p-3 text-left hover:border-outline-gray-4"
              @click="openTicket(ticket.name)"
            >
              <div class="flex items-start justify-between gap-2">
                <div class="min-w-0">
                  <div class="truncate text-sm font-medium text-ink-gray-9">{{ ticket.unit_name }}</div>
                  <div class="font-mono text-xs text-ink-gray-5">{{ ticket.serial_number }}</div>
                </div>
                <StatusBadge :value="state === 'Complete' ? ticket.final_condition : ticket.unit_condition" kind="condition" />
              </div>
              <p class="mt-2 line-clamp-2 text-xs text-ink-gray-6">{{ ticket.issue_description || 'No description' }}</p>
              <div class="mt-2 flex items-center justify-between text-[11px] text-ink-gray-5">
                <span>{{ ticket.name }}</span>
                <span :title="fullDate(ticket.modified)">{{ timeAgo(ticket.modified) }}</span>
              </div>
            </button>
          </li>
          <li v-if="!board.columns[state].length" class="rounded-lg border border-dashed border-outline-gray-3 px-3 py-6 text-center text-xs text-ink-gray-5">
            {{ EMPTY[state] }}
          </li>
        </ul>
      </section>
    </div>

    <FlagProblemDialog v-model="flagOpen" @created="afterChange" />

    <Dialog v-model="ticketOpen" :options="{ title: detail ? detail.ticket.name : 'Ticket', size: 'lg' }">
      <template #body-content>
        <div v-if="detail" class="grid gap-3 text-sm">
          <div class="flex flex-wrap items-center gap-2">
            <StatusBadge :value="detail.ticket.workflow_state" kind="ticket" size="md" />
            <router-link v-if="detail.unit" :to="{ name: 'unit', params: { name: detail.unit.name } }" class="font-mono text-xs text-ink-blue-6 hover:underline" @click="ticketOpen = false">
              {{ detail.unit.unit_serial_number }}
            </router-link>
            <span class="text-ink-gray-7">{{ detail.unit?.unit_name }}</span>
            <StatusBadge v-if="detail.unit" :value="detail.unit.unit_condition" kind="condition" />
          </div>

          <div class="rounded-md bg-surface-gray-1 px-3 py-2">
            <div class="text-xs text-ink-gray-5">Reported problem · {{ detail.ticket.unit_condition }}</div>
            <div class="text-ink-gray-8">{{ detail.ticket.issue_description || 'No description' }}</div>
          </div>

          <div v-if="detail.ticket.workflow_state === 'Complete'" class="rounded-md bg-surface-green-2 px-3 py-2">
            <div class="text-xs text-ink-green-8">Finished — {{ detail.ticket.final_condition }} · {{ detail.ticket.maintained_by }}</div>
            <div class="text-ink-gray-8">{{ detail.ticket.maintenance_result || 'No notes' }}</div>
          </div>

          <template v-if="detail.ticket.workflow_state === 'In Repair' && detail.can.write">
            <div class="grid gap-1">
              <span class="text-ink-gray-6">Result of the repair</span>
              <div class="grid grid-cols-2 gap-2">
                <button v-for="option in FINALS" :key="option.value" class="rounded-lg border px-3 py-2 text-left" :class="final === option.value ? 'border-outline-blue-3 bg-surface-blue-2' : 'border-outline-gray-2 hover:border-outline-gray-4'" @click="final = option.value">
                  <div class="font-medium text-ink-gray-9">{{ option.label }}</div>
                  <div class="text-xs text-ink-gray-5">{{ option.hint }}</div>
                </button>
              </div>
            </div>
            <label class="grid gap-1">
              <span class="text-ink-gray-6">What was done</span>
              <textarea v-model="result" rows="3" class="rounded-md border border-outline-gray-3 p-2.5 outline-none focus:border-outline-blue-3" placeholder="Parts replaced, cleaning done…" />
            </label>
          </template>

          <div class="mt-1 flex justify-end gap-2">
            <Button label="Close" @click="ticketOpen = false" />
            <Button v-if="detail.ticket.workflow_state === 'Attention Required' && detail.can.write" variant="solid" label="Send to repair" :loading="busy" @click="start" />
            <Button v-if="detail.ticket.workflow_state === 'In Repair' && detail.can.write" variant="solid" label="Complete repair" :loading="busy" @click="finish" />
          </div>
        </div>
      </template>
    </Dialog>
  </PageFrame>
</template>

<script setup>
import { inject, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Button, Dialog, toast } from 'frappe-ui'
import FlagProblemDialog from '../components/FlagProblemDialog.vue'
import Icon from '../components/Icon.vue'
import PageFrame from '../components/PageFrame.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { api, readError } from '../api'
import { fullDate, timeAgo } from '../format'

const DOT = { 'Attention Required': 'bg-surface-red-7', 'In Repair': 'bg-surface-blue-7', Complete: 'bg-surface-green-7' }
const EMPTY = {
  'Attention Required': 'No new problems.',
  'In Repair': 'Nothing being repaired right now.',
  Complete: 'No finished repairs yet.',
}
const FINALS = [
  { value: 'OK', label: 'Repaired', hint: 'Back in service as OK' },
  { value: 'Scrapped', label: 'Scrapped', hint: 'Beyond repair' },
]

const route = useRoute()
const { refreshSummary } = inject('rental')

const board = ref(null)
const failure = ref('')
const flagOpen = ref(route.query.flag === '1')
const ticketOpen = ref(false)
const detail = ref(null)
const final = ref('OK')
const result = ref('')
const busy = ref(false)

async function load() {
  try {
    board.value = await api.board()
    failure.value = ''
  } catch (err) {
    failure.value = readError(err)
  }
}

async function openTicket(name) {
  try {
    detail.value = await api.getTicket(name)
    final.value = 'OK'
    result.value = ''
    ticketOpen.value = true
  } catch (err) {
    toast.error(readError(err))
  }
}

async function run(request, message) {
  busy.value = true
  try {
    detail.value = await request()
    toast.success(message)
    await afterChange()
  } catch (err) {
    toast.error(readError(err))
  } finally {
    busy.value = false
  }
}

const start = () => run(() => api.startRepair(detail.value.ticket.name), 'Sent to repair')
const finish = () =>
  run(() => api.completeTicket({ name: detail.value.ticket.name, final_condition: final.value, maintenance_result: result.value }), 'Repair completed')

async function afterChange() {
  await load()
  refreshSummary()
}

onMounted(load)
</script>
