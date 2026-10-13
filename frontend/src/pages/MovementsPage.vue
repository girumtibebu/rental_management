<template>
  <PageFrame title="Movements" :subtitle="`${number(total)} recorded`">
    <template #actions>
      <Button variant="solid" size="sm" @click="router.push({ name: 'movement-new' })">
        <template #prefix><Icon name="plus" :size="13" /></template>
        New movement
      </Button>
    </template>

    <div class="flex flex-col overflow-hidden rounded-xl border border-outline-gray-2 bg-surface-white shadow-xs">
      <!-- Search & Filters -->
      <div class="flex flex-col gap-2.5 border-b border-outline-gray-2 p-3 sm:p-3.5">
        <div class="relative w-full">
          <Icon name="search" :size="15" class="pointer-events-none absolute left-3 top-2.5 text-ink-gray-5" />
          <input
            v-model="search"
            class="h-9 w-full rounded-lg border border-outline-gray-3 bg-surface-white pl-9 pr-8 text-sm outline-none focus:border-outline-blue-4"
            placeholder="Search movement, location or person…"
            @input="reload(true)"
          />
          <button
            v-if="search"
            class="absolute right-2.5 top-2 text-ink-gray-4 hover:text-ink-gray-7"
            @click="search = ''; reload(true)"
          >
            <Icon name="close" :size="14" />
          </button>
        </div>

        <!-- Horizontal Scrolling Type Filters on Mobile -->
        <div class="flex items-center gap-1.5 overflow-x-auto no-scrollbar pb-0.5">
          <button
            v-for="option in TYPE_FILTERS"
            :key="option.value"
            class="shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors"
            :class="type === option.value ? 'bg-surface-gray-9 text-white font-semibold shadow-2xs' : 'bg-surface-gray-1 text-ink-gray-7 hover:bg-surface-gray-2 border border-outline-gray-2'"
            @click="type = option.value; reload(true)"
          >
            {{ option.label }}
          </button>
        </div>
      </div>

      <!-- Mobile Cards View (< 768px) -->
      <div class="divide-y divide-outline-gray-1 md:hidden">
        <div
          v-for="move in rows"
          :key="move.name"
          class="flex items-center gap-3 p-3.5 active:bg-surface-gray-1 transition-colors cursor-pointer"
          @click="router.push({ name: 'movement', params: { name: move.name } })"
        >
          <div class="min-w-0 flex-1">
            <div class="flex items-center justify-between gap-2">
              <span class="font-mono text-xs font-bold text-ink-gray-9">{{ move.name }}</span>
              <StatusBadge :value="move.transaction_type" kind="type" size="sm" />
            </div>

            <div class="mt-1.5 flex items-center gap-1.5 text-xs font-medium text-ink-gray-8">
              <span class="truncate">{{ move.from_location || 'Warehouse' }}</span>
              <Icon name="arrow" :size="11" class="text-ink-gray-4 shrink-0" />
              <span class="truncate font-semibold text-ink-blue-8">{{ move.to_location || 'Warehouse' }}</span>
            </div>

            <div class="mt-1 flex items-center justify-between text-xs text-ink-gray-5">
              <span>
                <strong class="text-ink-gray-8 tabular">{{ move.units }}</strong> unit{{ move.units === 1 ? '' : 's' }}
                <span v-if="move.bulk"> + {{ move.bulk }} bulk</span>
                <span v-if="move.issued_to || move.received_by" class="ml-1 text-ink-gray-6">· {{ move.issued_to || move.received_by }}</span>
              </span>
              <span class="text-[11px] text-ink-gray-4">{{ timeAgo(move.creation) }}</span>
            </div>
          </div>
          <Icon name="chevright" :size="15" class="text-ink-gray-4 shrink-0" />
        </div>

        <div v-if="!rows.length && !loading" class="p-8 text-center text-sm text-ink-gray-5">
          <Icon name="truck" :size="28" class="mx-auto mb-2 text-ink-gray-4" />
          <div>No movements found.</div>
        </div>
      </div>

      <!-- Desktop Table (>= 768px) -->
      <table class="hidden md:table w-full text-sm">
        <thead>
          <tr class="border-b border-outline-gray-1 bg-surface-gray-1 text-[11px] uppercase tracking-wide text-ink-gray-5">
            <th class="px-4 py-2 text-left font-medium">Movement</th>
            <th class="px-3 py-2 text-left font-medium">Type</th>
            <th class="px-3 py-2 text-left font-medium">From → to</th>
            <th class="px-3 py-2 text-right font-medium">Items</th>
            <th class="px-3 py-2 text-left font-medium">By</th>
            <th class="px-4 py-2 text-right font-medium">When</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="move in rows"
            :key="move.name"
            class="cursor-pointer border-b border-outline-gray-1 last:border-0 hover:bg-surface-gray-1"
            @click="router.push({ name: 'movement', params: { name: move.name } })"
          >
            <td class="px-4 py-2.5 font-mono text-xs font-medium text-ink-gray-9">{{ move.name }}</td>
            <td class="px-3 py-2.5"><StatusBadge :value="move.transaction_type" kind="type" /></td>
            <td class="px-3 py-2.5 text-ink-gray-7">{{ move.from_location || '—' }} → {{ move.to_location || '—' }}</td>
            <td class="px-3 py-2.5 text-right tabular text-ink-gray-8">{{ move.units }}<span v-if="move.bulk" class="text-xs text-ink-gray-5"> + {{ move.bulk }} bulk</span></td>
            <td class="px-3 py-2.5 text-ink-gray-7">{{ move.issued_to || move.received_by || userName(move.owner) }}</td>
            <td class="px-4 py-2.5 text-right text-xs text-ink-gray-5" :title="fullDate(move.creation)">{{ timeAgo(move.creation) }}</td>
          </tr>
          <tr v-if="!rows.length && !loading"><td colspan="6" class="px-4 py-12 text-center text-sm text-ink-gray-5">No movements yet.</td></tr>
        </tbody>
      </table>

      <Pagination v-model:page="page" :total="total" :page-length="PAGE" @update:page="reload(false)" />
    </div>
  </PageFrame>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Button, toast } from 'frappe-ui'
import Icon from '../components/Icon.vue'
import PageFrame from '../components/PageFrame.vue'
import Pagination from '../components/Pagination.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { api, readError } from '../api'
import { fullDate, number, timeAgo, userName } from '../format'

const PAGE = 25
const TYPE_FILTERS = [
  { value: '', label: 'All' },
  { value: 'CHECK_OUT', label: 'Check out' },
  { value: 'CHECK_IN', label: 'Check in' },
  { value: 'MAINTENANCE_OUT', label: 'To repair' },
  { value: 'MAINTENANCE_IN', label: 'From repair' },
  { value: 'LOST', label: 'Lost' },
]

const router = useRouter()
const rows = ref([])
const total = ref(0)
const page = ref(1)
const search = ref('')
const type = ref('')
const loading = ref(true)
let timer

async function load() {
  loading.value = true
  try {
    const result = await api.listMovements({ search: search.value, transaction_type: type.value, page: page.value, page_length: PAGE })
    rows.value = result.rows
    total.value = result.total
  } catch (err) {
    toast.error(readError(err))
  } finally {
    loading.value = false
  }
}

function reload(resetPage) {
  if (resetPage) page.value = 1
  clearTimeout(timer)
  timer = setTimeout(load, resetPage ? 200 : 0)
}

onMounted(load)
</script>
