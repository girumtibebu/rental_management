<template>
  <PageFrame title="Dashboard" subtitle="Where equipment is right now, and what needs attention.">
    <template #actions>
      <Button size="sm" @click="refreshSummary"><template #prefix><Icon name="refresh" :size="13" /></template>Refresh</Button>
    </template>

    <div v-if="!data" class="p-10 text-center text-sm text-ink-gray-5">Loading…</div>

    <template v-else>
      <!-- Mobile Quick Actions & Hero Scanner Bar -->
      <div class="flex flex-col gap-2 rounded-xl border border-outline-blue-3 bg-gradient-to-r from-surface-blue-2 to-surface-white p-3.5 sm:hidden shadow-xs">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="flex h-8 w-8 items-center justify-center rounded-lg bg-surface-blue-6 text-white shadow-xs">
              <Icon name="scan" :size="18" />
            </span>
            <div>
              <div class="text-xs font-bold text-ink-blue-9">Warehouse Operations</div>
              <div class="text-[10px] text-ink-blue-7">Fast mobile scanner & equipment movement</div>
            </div>
          </div>
          <button
            class="flex items-center gap-1.5 rounded-lg bg-surface-blue-6 px-3 py-1.5 text-xs font-semibold text-white shadow-xs active:scale-95"
            @click="scanner?.openScanner"
          >
            <Icon name="camera" :size="13" /> Scan
          </button>
        </div>

        <div class="grid grid-cols-3 gap-1.5 pt-1 border-t border-outline-blue-2">
          <router-link
            :to="{ name: 'movement-new', query: { type: 'CHECK_OUT' } }"
            class="flex items-center justify-center gap-1 rounded-lg border border-outline-gray-2 bg-surface-white py-2 text-[11px] font-semibold text-ink-gray-8 active:scale-95 shadow-2xs"
          >
            <Icon name="out" :size="13" class="text-ink-blue-6" /> Check Out
          </router-link>
          <router-link
            :to="{ name: 'movement-new', query: { type: 'CHECK_IN' } }"
            class="flex items-center justify-center gap-1 rounded-lg border border-outline-gray-2 bg-surface-white py-2 text-[11px] font-semibold text-ink-gray-8 active:scale-95 shadow-2xs"
          >
            <Icon name="in" :size="13" class="text-ink-green-6" /> Check In
          </router-link>
          <router-link
            :to="{ name: 'maintenance', query: { flag: '1' } }"
            class="flex items-center justify-center gap-1 rounded-lg border border-outline-gray-2 bg-surface-white py-2 text-[11px] font-semibold text-ink-amber-8 active:scale-95 shadow-2xs"
          >
            <Icon name="alert" :size="13" class="text-ink-amber-6" /> Report
          </router-link>
        </div>
      </div>

      <!-- Overview Metric Cards -->
      <div class="grid grid-cols-2 gap-2.5 sm:gap-3 md:grid-cols-3 xl:grid-cols-6">
        <router-link
          v-for="card in cards"
          :key="card.label"
          :to="{ name: 'units', query: card.query }"
          class="rounded-xl border bg-surface-white p-3 sm:p-4 hover:border-outline-gray-4 active:bg-surface-gray-1 transition-colors shadow-2xs"
          :class="card.alert && card.value ? 'border-outline-red-3 bg-surface-red-1/30' : 'border-outline-gray-2'"
        >
          <div class="text-[10px] sm:text-[11px] font-semibold uppercase tracking-wider text-ink-gray-5 truncate">{{ card.label }}</div>
          <div class="mt-1 text-xl sm:text-2xl font-bold tabular" :class="card.alert && card.value ? 'text-ink-red-6' : 'text-ink-gray-9'">{{ number(card.value) }}</div>
          <div class="mt-0.5 truncate text-[11px] text-ink-gray-5">{{ card.note }}</div>
        </router-link>
      </div>

      <div class="grid gap-4 lg:grid-cols-2">
        <section class="rounded-xl border border-outline-gray-2 bg-surface-white shadow-xs overflow-hidden">
          <header class="border-b border-outline-gray-1 px-4 py-2.5 text-sm font-bold text-ink-gray-9">Where equipment is</header>
          <ul v-if="data.locations.length" class="divide-y divide-outline-gray-1">
            <li v-for="row in data.locations" :key="row.location + row.status">
              <router-link :to="{ name: 'units', query: { status: row.status, location: row.location === 'Unknown' ? '' : row.location } }" class="flex items-center gap-3 px-4 py-2.5 text-sm hover:bg-surface-gray-1 active:bg-surface-gray-2">
                <Icon name="pin" :size="14" class="text-ink-gray-5" />
                <span class="flex-1 truncate font-medium text-ink-gray-8">{{ row.location }}</span>
                <StatusBadge :value="row.status" size="sm" />
                <span class="w-12 text-right font-bold tabular text-ink-gray-9">{{ row.units }}</span>
              </router-link>
            </li>
          </ul>
          <div v-else class="p-6 text-center text-sm text-ink-gray-5">Everything is in the warehouse.</div>
        </section>

        <section class="rounded-xl border border-outline-gray-2 bg-surface-white shadow-xs overflow-hidden">
          <header class="border-b border-outline-gray-1 px-4 py-2.5 text-sm font-bold text-ink-gray-9">Condition of equipment</header>
          <ul class="flex flex-col gap-3 p-4">
            <li v-for="item in data.conditions" :key="item.condition">
              <div class="mb-1 flex items-center justify-between text-sm">
                <router-link :to="{ name: 'units', query: { condition: item.condition } }" class="hover:underline"><StatusBadge :value="item.condition" kind="condition" /></router-link>
                <span class="tabular font-medium text-ink-gray-7">{{ number(item.count) }} <span class="text-xs text-ink-gray-5">({{ percent(item.count) }})</span></span>
              </div>
              <div class="h-2 overflow-hidden rounded-full bg-surface-gray-2">
                <div class="h-full rounded-full transition-all" :class="barColor(item.condition)" :style="{ width: percent(item.count) }" />
              </div>
            </li>
            <li v-if="!data.conditions.length" class="text-center text-sm text-ink-gray-5">No units yet.</li>
          </ul>
        </section>
      </div>

      <div class="grid gap-4 lg:grid-cols-2">
        <section class="rounded-xl border border-outline-gray-2 bg-surface-white shadow-xs overflow-hidden">
          <header class="flex items-center justify-between border-b border-outline-gray-1 px-4 py-2.5">
            <span class="text-sm font-bold text-ink-gray-9">Running low</span>
            <span class="text-xs text-ink-gray-5">Available now</span>
          </header>
          <ul v-if="data.tight.length" class="divide-y divide-outline-gray-1">
            <li v-for="row in data.tight" :key="row.name">
              <router-link :to="{ name: 'item', params: { name: row.name } }" class="flex items-center gap-3 px-4 py-2.5 hover:bg-surface-gray-1 active:bg-surface-gray-2">
                <div class="min-w-0 flex-1">
                  <div class="truncate text-sm font-medium text-ink-gray-8">{{ row.item_name }}</div>
                  <div class="text-xs text-ink-gray-5">{{ row.category }} · {{ row.out }} out</div>
                </div>
                <div class="w-20 sm:w-28">
                  <div class="h-2 overflow-hidden rounded-full bg-surface-gray-2">
                    <div class="h-full rounded-full" :class="row.tight ? 'bg-surface-red-7' : 'bg-surface-green-7'" :style="{ width: (row.total ? (row.available / row.total) * 100 : 0) + '%' }" />
                  </div>
                </div>
                <span class="w-14 text-right text-sm tabular font-semibold" :class="row.tight ? 'text-ink-red-6' : 'text-ink-gray-8'">{{ row.available }}/{{ row.total }}</span>
              </router-link>
            </li>
          </ul>
          <div v-else class="p-6 text-center text-sm text-ink-gray-5">No serialised equipment yet.</div>
        </section>

        <section class="rounded-xl border border-outline-gray-2 bg-surface-white shadow-xs overflow-hidden">
          <header class="flex items-center justify-between border-b border-outline-gray-1 px-4 py-2.5">
            <span class="text-sm font-bold text-ink-gray-9">Open maintenance</span>
            <router-link :to="{ name: 'maintenance' }" class="text-xs font-semibold text-ink-blue-6 hover:underline">Open board</router-link>
          </header>
          <ul v-if="data.tickets.length" class="divide-y divide-outline-gray-1">
            <li v-for="ticket in data.tickets" :key="ticket.name" class="flex items-center gap-3 px-4 py-2.5">
              <div class="min-w-0 flex-1">
                <div class="truncate text-sm font-medium text-ink-gray-8">{{ ticket.item_name }}</div>
                <div class="truncate text-xs text-ink-gray-5">{{ ticket.serial_no }} · {{ ticket.issue_description || 'No description' }}</div>
              </div>
              <StatusBadge :value="ticket.workflow_state" kind="ticket" size="sm" />
              <span class="w-16 text-right text-xs text-ink-gray-5">{{ timeAgo(ticket.creation) }}</span>
            </li>
          </ul>
          <div v-else class="p-6 text-center text-sm text-ink-gray-5">Nothing waiting for repair.</div>
        </section>
      </div>

      <section class="rounded-xl border border-outline-gray-2 bg-surface-white shadow-xs overflow-hidden">
        <header class="flex items-center justify-between border-b border-outline-gray-1 px-4 py-2.5">
          <span class="text-sm font-bold text-ink-gray-9">Recent movements</span>
          <router-link :to="{ name: 'movements' }" class="text-xs font-semibold text-ink-blue-6 hover:underline">All movements</router-link>
        </header>
        <ul v-if="data.movements.length" class="divide-y divide-outline-gray-1">
          <li v-for="move in data.movements" :key="move.name">
            <router-link :to="{ name: 'movement', params: { name: move.name } }" class="flex items-center gap-3 px-4 py-2.5 text-sm hover:bg-surface-gray-1 active:bg-surface-gray-2">
              <StatusBadge :value="move.transaction_type" kind="type" size="sm" />
              <span class="font-mono text-xs text-ink-gray-5">{{ move.name }}</span>
              <span class="flex-1 truncate text-ink-gray-7">{{ move.from_location || '—' }} → {{ move.to_location || '—' }}</span>
              <span class="text-xs text-ink-gray-5">{{ userName(move.owner) }} · {{ timeAgo(move.creation) }}</span>
            </router-link>
          </li>
        </ul>
        <div v-else class="p-6 text-center text-sm text-ink-gray-5">No movements recorded yet.</div>
      </section>
    </template>
  </PageFrame>
</template>

<script setup>
import { computed, inject, onMounted } from 'vue'
import { Button } from 'frappe-ui'
import Icon from '../components/Icon.vue'
import PageFrame from '../components/PageFrame.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { number, timeAgo, userName } from '../format'

const { summary: data, refreshSummary } = inject('rental')
const scanner = inject('scanner', null)

onMounted(refreshSummary)

const cards = computed(() => {
  const t = data.value.totals
  return [
    { label: 'Total units', value: t.total, note: `${t.items} catalog items`, query: {} },
    { label: 'In warehouse', value: t.Warehouse, note: 'ready to go out', query: { status: 'Warehouse' } },
    { label: 'At events', value: t['At Event'], note: 'out with crews', query: { status: 'At Event' } },
    { label: 'In repair', value: t['In Maintenance'], note: 'at the repair shop', query: { status: 'In Maintenance' } },
    { label: 'Missing', value: t.Missing, note: 'cannot be found', query: { status: 'Missing' }, alert: true },
    { label: 'Need attention', value: t.needs_attention, note: 'not in OK condition', query: {}, alert: true },
  ]
})

const total = computed(() => data.value.conditions.reduce((sum, item) => sum + item.count, 0) || 1)
const percent = (count) => `${Math.round((count / total.value) * 100)}%`
const barColor = (condition) =>
  ({ OK: 'bg-surface-green-7', Damaged: 'bg-surface-red-7', Scrapped: 'bg-surface-gray-7' })[condition] || 'bg-surface-amber-7'
</script>
