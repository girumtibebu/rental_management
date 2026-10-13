<template>
  <PageFrame title="Units" :subtitle="`${number(total)} serial-numbered units${filtered ? ' match your filters' : ''}`">
    <div class="flex flex-col overflow-hidden rounded-xl border border-outline-gray-2 bg-surface-white shadow-xs">
      <!-- Filter Toolbar -->
      <div class="flex flex-col gap-2.5 border-b border-outline-gray-2 p-3 sm:p-3.5">
        <!-- Top Row: Search & Mobile Filter Toggle -->
        <div class="flex items-center gap-2">
          <div class="relative flex-1">
            <Icon name="search" :size="15" class="pointer-events-none absolute left-3 top-2.5 text-ink-gray-5" />
            <input
              v-model="filters.search"
              class="h-9 w-full rounded-lg border border-outline-gray-3 bg-surface-white pl-9 pr-8 text-sm outline-none focus:border-outline-blue-4"
              placeholder="Search serial, name or location…"
              @input="reload(true)"
            />
            <button
              v-if="filters.search"
              class="absolute right-2.5 top-2 text-ink-gray-4 hover:text-ink-gray-7"
              @click="filters.search = ''; reload(true)"
            >
              <Icon name="close" :size="14" />
            </button>
          </div>

          <!-- Mobile Filters Toggle -->
          <button
            class="flex h-9 items-center gap-1.5 rounded-lg border px-3 text-xs font-semibold sm:hidden"
            :class="hasExtraFilters ? 'border-outline-blue-4 bg-surface-blue-2 text-ink-blue-8' : 'border-outline-gray-3 bg-surface-white text-ink-gray-7'"
            @click="showMobileFilters = !showMobileFilters"
          >
            <Icon name="filter" :size="13" />
            <span>Filters</span>
          </button>
        </div>

        <!-- Status Filter Tabs: Horizontal Scrolling on Mobile -->
        <div class="flex items-center gap-1.5 overflow-x-auto no-scrollbar pb-0.5">
          <button
            v-for="status in STATUS_FILTERS"
            :key="status.value"
            class="shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors"
            :class="filters.status === status.value ? 'bg-surface-gray-9 text-white font-semibold shadow-2xs' : 'bg-surface-gray-1 text-ink-gray-7 hover:bg-surface-gray-2 border border-outline-gray-2'"
            @click="setStatus(status.value)"
          >
            {{ status.label }}
          </button>
        </div>

        <!-- Secondary Filters (Always visible on desktop, toggleable on mobile) -->
        <div
          class="flex flex-wrap items-center gap-2 pt-1 border-t border-outline-gray-1 sm:border-0 sm:pt-0"
          :class="showMobileFilters ? 'flex' : 'hidden sm:flex'"
        >
          <select
            v-model="filters.condition"
            class="h-8 rounded-lg border border-outline-gray-3 bg-surface-white px-2.5 text-xs text-ink-gray-8 outline-none"
            @change="reload(true)"
          >
            <option value="">Any condition</option>
            <option v-for="item in CONDITIONS" :key="item" :value="item">{{ item }}</option>
          </select>

          <select
            v-model="filters.category"
            class="h-8 rounded-lg border border-outline-gray-3 bg-surface-white px-2.5 text-xs text-ink-gray-8 outline-none"
            @change="reload(true)"
          >
            <option value="">All categories</option>
            <option v-for="item in facets.categories" :key="item" :value="item">{{ item }}</option>
          </select>

          <select
            v-model="filters.kind"
            class="h-8 rounded-lg border border-outline-gray-3 bg-surface-white px-2.5 text-xs text-ink-gray-8 outline-none"
            @change="reload(true)"
          >
            <option value="">Units and boxes</option>
            <option value="Unit">Units</option>
            <option value="Box">Boxes</option>
          </select>

          <button
            v-if="filters.item_code || filters.location"
            class="flex items-center gap-1 rounded-full bg-surface-blue-2 px-2.5 py-1 text-xs font-medium text-ink-blue-8"
            @click="clearExtra"
          >
            {{ filters.item_code || filters.location }} <Icon name="close" :size="10" />
          </button>

          <button
            v-if="filtered"
            class="text-xs text-ink-blue-6 hover:underline sm:ml-auto"
            @click="clearAll"
          >
            Clear all filters
          </button>
        </div>
      </div>

      <!-- Mobile Cards View (< 768px) -->
      <div class="divide-y divide-outline-gray-1 md:hidden">
        <div
          v-for="unit in rows"
          :key="unit.name"
          class="flex items-center gap-3 p-3.5 active:bg-surface-gray-1 transition-colors cursor-pointer"
          @click="open(unit)"
        >
          <div class="min-w-0 flex-1">
            <div class="flex items-center justify-between gap-2">
              <span class="font-mono text-sm font-bold text-ink-gray-9">{{ unit.serial_no }}</span>
              <div class="flex items-center gap-1.5">
                <StatusBadge :value="unit.status" size="sm" />
                <StatusBadge :value="unit.condition" kind="condition" size="sm" />
              </div>
            </div>

            <div class="mt-1 font-medium text-sm text-ink-gray-8 truncate">{{ unit.item_name }}</div>
            <div class="text-xs text-ink-gray-5">{{ unit.category }} · {{ unit.kind }}</div>

            <div class="mt-1.5 flex items-center justify-between text-xs text-ink-gray-6">
              <span class="flex items-center gap-1 truncate">
                <Icon name="pin" :size="12" class="text-ink-gray-4" />
                <span>{{ unit.location || 'Warehouse' }}</span>
                <span v-if="unit.storage" class="text-ink-gray-4">({{ unit.storage }})</span>
              </span>
              <span class="shrink-0 text-ink-gray-4 text-[11px]">{{ timeAgo(unit.modified) }}</span>
            </div>
          </div>
          <Icon name="chevright" :size="15" class="text-ink-gray-4 shrink-0" />
        </div>

        <div v-if="!rows.length && !loading" class="p-8 text-center text-sm text-ink-gray-5">
          <Icon name="layers" :size="28" class="mx-auto mb-2 text-ink-gray-4" />
          <div>No units match.</div>
          <button v-if="filtered" class="mt-1 text-xs text-ink-blue-6 underline" @click="clearAll">
            Clear all filters
          </button>
        </div>
      </div>

      <!-- Desktop Table View (>= 768px) -->
      <div class="hidden md:block overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-outline-gray-1 bg-surface-gray-1 text-[11px] uppercase tracking-wide text-ink-gray-5">
              <th class="px-4 py-2 text-left font-medium">Serial</th>
              <th class="px-3 py-2 text-left font-medium">Equipment</th>
              <th class="px-3 py-2 text-left font-medium">Status</th>
              <th class="px-3 py-2 text-left font-medium">Condition</th>
              <th class="px-3 py-2 text-left font-medium">Location</th>
              <th class="px-3 py-2 text-left font-medium">In box</th>
              <th class="px-4 py-2 text-right font-medium">Updated</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="unit in rows"
              :key="unit.name"
              class="cursor-pointer border-b border-outline-gray-1 last:border-0 hover:bg-surface-gray-1"
              @click="open(unit)"
            >
              <td class="px-4 py-2.5 font-mono text-xs font-medium text-ink-gray-9">{{ unit.serial_no }}</td>
              <td class="px-3 py-2.5">
                <div class="font-medium text-ink-gray-8">{{ unit.item_name }}</div>
                <div class="text-xs text-ink-gray-5">{{ unit.category }} · {{ unit.kind }}</div>
              </td>
              <td class="px-3 py-2.5"><StatusBadge :value="unit.status" /></td>
              <td class="px-3 py-2.5"><StatusBadge :value="unit.condition" kind="condition" /></td>
              <td class="px-3 py-2.5 text-ink-gray-7">
                {{ unit.location || '—' }}
                <div v-if="unit.storage" class="text-xs text-ink-gray-5">{{ unit.storage }}</div>
              </td>
              <td class="px-3 py-2.5 font-mono text-xs text-ink-gray-6">{{ unit.parent_box || '' }}</td>
              <td class="px-4 py-2.5 text-right text-xs text-ink-gray-5">{{ timeAgo(unit.modified) }}</td>
            </tr>
            <tr v-if="!rows.length && !loading">
              <td colspan="7" class="px-4 py-12 text-center text-sm text-ink-gray-5">
                No units match.
                <button v-if="filtered" class="text-ink-blue-6 hover:underline" @click="clearAll">Clear the filters</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <Pagination v-model:page="page" :total="total" :page-length="PAGE" @update:page="reload(false)" />
    </div>
  </PageFrame>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'frappe-ui'
import Icon from '../components/Icon.vue'
import PageFrame from '../components/PageFrame.vue'
import Pagination from '../components/Pagination.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { api, readError } from '../api'
import { number, timeAgo } from '../format'

const PAGE = 25
const STATUS_FILTERS = [
  { value: '', label: 'All' },
  { value: 'Warehouse', label: 'Warehouse' },
  { value: 'At Event', label: 'At event' },
  { value: 'In Maintenance', label: 'In repair' },
  { value: 'Missing', label: 'Missing' },
  { value: 'Not In Stock', label: 'Not in stock' },
]
const CONDITIONS = ['OK', 'Need Cleaning', 'Damaged', 'Partially Ok', 'Scrapped']

const route = useRoute()
const router = useRouter()
const q = route.query

const showMobileFilters = ref(false)

const filters = reactive({
  search: q.search || '',
  status: q.status || '',
  condition: q.condition || '',
  category: q.category || '',
  kind: q.kind || '',
  item_code: q.item_code || '',
  location: q.location || '',
})
const facets = reactive({ categories: [] })
const rows = ref([])
const total = ref(0)
const page = ref(1)
const loading = ref(true)
let timer

const filtered = computed(() => Object.values(filters).some(Boolean))
const hasExtraFilters = computed(() => Boolean(filters.condition || filters.category || filters.kind))

async function load() {
  loading.value = true
  try {
    const result = await api.listUnits({ ...filters, page: page.value, page_length: PAGE })
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
  timer = setTimeout(() => {
    router.replace({ query: Object.fromEntries(Object.entries(filters).filter(([, value]) => value)) })
    load()
  }, resetPage ? 200 : 0)
}

function setStatus(value) {
  filters.status = value
  reload(true)
}

function clearExtra() {
  filters.item_code = ''
  filters.location = ''
  reload(true)
}

function clearAll() {
  Object.keys(filters).forEach((key) => (filters[key] = ''))
  reload(true)
}

const open = (unit) => router.push({ name: 'unit', params: { name: unit.name } })

onMounted(async () => {
  load()
  api.facets().then((data) => (facets.categories = data.categories)).catch(() => {})
})
</script>
