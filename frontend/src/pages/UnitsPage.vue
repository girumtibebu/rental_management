<template>
  <PageFrame title="Units" :subtitle="`${number(total)} serial-numbered units${filtered ? ' match your filters' : ''}`">
    <div class="flex flex-col overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-white">
      <div class="flex flex-wrap items-center gap-2 border-b border-outline-gray-2 px-3 py-2.5">
        <div class="relative">
          <Icon name="search" :size="13" class="pointer-events-none absolute left-2.5 top-[9px] text-ink-gray-5" />
          <input
            v-model="filters.search"
            class="h-8 w-60 rounded-md border border-outline-gray-3 bg-surface-white pl-8 pr-2 text-sm outline-none focus:border-outline-blue-3"
            placeholder="Serial, name or location…"
            @input="reload(true)"
          />
        </div>

        <div class="inline-flex overflow-hidden rounded-md border border-outline-gray-3 text-sm">
          <button
            v-for="status in STATUS_FILTERS"
            :key="status.value"
            class="px-3 py-1"
            :class="filters.status === status.value ? 'bg-surface-gray-8 text-ink-white' : 'bg-surface-white text-ink-gray-7 hover:bg-surface-gray-2'"
            @click="setStatus(status.value)"
          >
            {{ status.label }}
          </button>
        </div>

        <select v-model="filters.condition" class="h-8 rounded-md border border-outline-gray-3 bg-surface-white px-2 py-0 text-sm" @change="reload(true)">
          <option value="">Any condition</option>
          <option v-for="item in CONDITIONS" :key="item" :value="item">{{ item }}</option>
        </select>
        <select v-model="filters.category" class="h-8 rounded-md border border-outline-gray-3 bg-surface-white px-2 py-0 text-sm" @change="reload(true)">
          <option value="">All categories</option>
          <option v-for="item in facets.categories" :key="item" :value="item">{{ item }}</option>
        </select>
        <select v-model="filters.kind" class="h-8 rounded-md border border-outline-gray-3 bg-surface-white px-2 py-0 text-sm" @change="reload(true)">
          <option value="">Units and boxes</option>
          <option value="Unit">Units</option>
          <option value="Box">Boxes</option>
        </select>

        <button
          v-if="filters.item_code || filters.location"
          class="flex items-center gap-1 rounded-full bg-surface-blue-2 px-2.5 py-1 text-xs text-ink-blue-8"
          @click="clearExtra"
        >
          {{ filters.item_code || filters.location }} <Icon name="close" :size="10" />
        </button>
        <Button v-if="filtered" size="sm" variant="ghost" @click="clearAll">Clear filters</Button>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full min-w-[860px] text-sm">
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
import { Button, toast } from 'frappe-ui'
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
