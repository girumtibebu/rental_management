<template>
  <PageFrame title="Catalog" subtitle="What you own, and how much of it is ready to go out.">
    <template #actions>
      <Button variant="solid" size="sm" @click="newOpen = true"><template #prefix><Icon name="plus" :size="13" /></template>New item</Button>
    </template>

    <div class="flex flex-col sm:flex-row flex-wrap items-stretch sm:items-center gap-2">
      <TextInput v-model="filters.search" type="search" class="w-full sm:w-64" placeholder="Search equipment…" @update:model-value="reload(true)">
          <template #prefix><Icon name="search" :size="14" class="text-ink-gray-5" /></template>
        </TextInput>
      <div class="flex items-center gap-2 overflow-x-auto no-scrollbar pb-0.5 sm:pb-0">
        <Select v-model="filters.category" class="w-44 shrink-0" :options="categoryOptions" @update:model-value="reload(true)" />
        <TabButtons v-model="filters.kind" :buttons="KINDS" class="shrink-0" @update:model-value="reload(true)" />
        <span class="ml-auto text-xs text-ink-gray-5 shrink-0 hidden sm:inline">{{ number(total) }} items</span>
        <div class="inline-flex shrink-0 overflow-hidden rounded-md border border-outline-gray-3" role="group" aria-label="View">
          <button
            v-for="option in VIEWS"
            :key="option.value"
            class="flex h-7 w-8 items-center justify-center"
            :class="view === option.value ? 'bg-surface-gray-3 text-ink-gray-9' : 'bg-surface-base text-ink-gray-5 hover:bg-surface-gray-2'"
            :title="option.label"
            :aria-label="option.label"
            :aria-pressed="view === option.value"
            @click="setView(option.value)"
          >
            <span :class="option.icon" class="size-4" />
          </button>
        </div>
      </div>
    </div>

    <div v-if="rows.length && view === 'list'" class="overflow-x-auto rounded-lg border border-outline-gray-2 bg-surface-base">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-outline-gray-1 bg-surface-gray-1 text-[11px] uppercase tracking-wide text-ink-gray-5">
            <th class="px-4 py-2 text-left font-medium">Equipment</th>
            <th class="px-3 py-2 text-left font-medium">Category</th>
            <th class="px-3 py-2 text-left font-medium">Type</th>
            <th class="px-3 py-2 text-right font-medium">Available</th>
            <th class="px-3 py-2 text-right font-medium">Out</th>
            <th class="px-3 py-2 text-right font-medium">In repair</th>
            <th class="px-4 py-2 text-right font-medium">Missing</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="item in rows"
            :key="item.name"
            class="cursor-pointer border-b border-outline-gray-1 last:border-0 hover:bg-surface-gray-1"
            @click="router.push({ name: 'item', params: { name: item.name } })"
          >
            <td class="px-4 py-2">
              <div class="flex min-w-0 items-center gap-2.5">
                <div class="flex size-8 shrink-0 items-center justify-center overflow-hidden rounded bg-surface-gray-2">
                  <img v-if="item.image" :src="item.image" class="h-full w-full object-cover" />
                  <Icon v-else name="box" :size="14" class="text-ink-gray-4" />
                </div>
                <div class="min-w-0">
                  <div class="truncate font-medium text-ink-gray-9">{{ item.item_name || item.rental_model }}</div>
                  <div class="truncate text-xs text-ink-gray-5">{{ item.name }}</div>
                </div>
              </div>
            </td>
            <td class="px-3 py-2 text-ink-gray-7">
              <div class="truncate">{{ item.category }}</div>
              <div class="truncate text-xs text-ink-gray-5">{{ item.brand }}</div>
            </td>
            <td class="px-3 py-2"><Badge :label="item.kind" theme="gray" size="sm" /></td>
            <td class="px-3 py-2 text-right tabular">
              <span class="font-semibold text-ink-gray-9">{{ number(item.counts.available) }}</span>
              <span class="text-ink-gray-5"> / {{ number(item.counts.total) }}</span>
            </td>
            <td class="px-3 py-2 text-right tabular text-ink-gray-7">{{ number(item.counts['At Event']) }}</td>
            <td class="px-3 py-2 text-right tabular text-ink-gray-7">{{ item.kind === 'Bulk' ? '' : number(item.counts['In Maintenance']) }}</td>
            <td class="px-4 py-2 text-right tabular" :class="item.counts.Missing ? 'text-ink-red-6' : 'text-ink-gray-7'">
              {{ item.kind === 'Bulk' ? '' : number(item.counts.Missing) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else-if="rows.length" class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
      <router-link
        v-for="item in rows"
        :key="item.name"
        :to="{ name: 'item', params: { name: item.name } }"
        class="group overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-base hover:border-outline-gray-4"
      >
        <div class="flex h-28 items-center justify-center bg-surface-gray-2">
          <img v-if="item.image" :src="item.image" class="h-full w-full object-cover" />
          <Icon v-else name="box" :size="30" class="text-ink-gray-4" />
        </div>
        <div class="p-3.5">
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <div class="truncate text-sm-semibold text-ink-gray-9">{{ item.item_name || item.rental_model }}</div>
              <div class="truncate text-xs text-ink-gray-5">{{ item.category }} · {{ item.brand }}</div>
            </div>
            <Badge :label="item.kind" theme="gray" size="sm" />
          </div>

          <div class="mt-3 flex items-baseline justify-between text-sm">
            <span class="font-semibold tabular text-ink-gray-9">{{ number(item.counts.available) }} <span class="font-normal text-ink-gray-5">available of {{ number(item.counts.total) }}</span></span>
          </div>
          <template v-if="item.kind !== 'Bulk'">
            <div class="mt-1.5 flex h-1.5 overflow-hidden rounded-full bg-surface-gray-2">
              <div class="bg-surface-green-9" :style="{ width: share(item.counts.available, item.counts.total) }" />
              <div class="bg-surface-blue-9" :style="{ width: share(item.counts['At Event'], item.counts.total) }" />
              <div class="bg-surface-amber-9" :style="{ width: share(item.counts['In Maintenance'], item.counts.total) }" />
              <div class="bg-surface-red-9" :style="{ width: share(item.counts.Missing, item.counts.total) }" />
            </div>
            <div class="mt-2 flex flex-wrap gap-x-3 text-[11px] text-ink-gray-5">
              <span>{{ item.counts['At Event'] }} out</span>
              <span>{{ item.counts['In Maintenance'] }} in repair</span>
              <span v-if="item.counts.Missing" class="text-ink-red-6">{{ item.counts.Missing }} missing</span>
            </div>
          </template>
          <div v-else class="mt-2 text-[11px] text-ink-gray-5">{{ number(item.counts['At Event']) }} {{ item.stock_uom }} out · counted, not serialised</div>
        </div>
      </router-link>
    </div>
    <div v-else-if="!loading" class="rounded-lg border border-dashed border-outline-gray-3 p-12 text-center text-sm text-ink-gray-5">
      Nothing here yet. Add your first item to start tracking equipment.
    </div>

    <Pagination v-model:page="page" :total="total" :page-length="PAGE" @update:page="reload(false)" />

    <NewItemDialog v-model="newOpen" @created="created" />
  </PageFrame>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Badge, Button, Select, TabButtons, TextInput, toast } from 'frappe-ui'
import Icon from '../components/Icon.vue'
import NewItemDialog from '../components/NewItemDialog.vue'
import PageFrame from '../components/PageFrame.vue'
import Pagination from '../components/Pagination.vue'
import { api, readError } from '../api'
import { number } from '../format'

const PAGE = 24
const KINDS = [
  { value: '', label: 'All' },
  { value: 'Unit', label: 'Units' },
  { value: 'Box', label: 'Boxes' },
  { value: 'Bulk', label: 'Bulk' },
]

const VIEWS = [
  { value: 'cards', label: 'Card view', icon: 'lucide-layout-grid' },
  { value: 'list', label: 'List view', icon: 'lucide-list' },
]

const router = useRouter()
const categoryOptions = computed(() => [{ label: 'All categories', value: '' }, ...facets.categories])
const filters = reactive({ search: '', category: '', kind: '' })
const facets = reactive({ categories: [], types: [], brands: [], kinds: [] })
const rows = ref([])
const total = ref(0)
const page = ref(1)
const loading = ref(true)
const newOpen = ref(false)
let timer

// Remember the chosen view per browser; storage can be blocked, so fall back to cards.
const VIEW_KEY = 'rental.catalog.view'
const view = ref(readView())
function readView() {
  try {
    return localStorage.getItem(VIEW_KEY) === 'list' ? 'list' : 'cards'
  } catch {
    return 'cards'
  }
}
function setView(value) {
  view.value = value
  try {
    localStorage.setItem(VIEW_KEY, value)
  } catch {}
}

const share = (part, whole) => `${whole ? (part / whole) * 100 : 0}%`

async function load() {
  loading.value = true
  try {
    const result = await api.listItems({ ...filters, page: page.value, page_length: PAGE })
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

function created(name) {
  router.push({ name: 'item', params: { name } })
}

onMounted(() => {
  load()
  api.facets().then((data) => Object.assign(facets, data)).catch(() => {})
})
</script>
