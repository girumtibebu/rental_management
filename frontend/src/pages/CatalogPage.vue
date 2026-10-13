<template>
  <PageFrame title="Catalog" subtitle="What you own, and how much of it is ready to go out.">
    <template #actions>
      <Button variant="solid" size="sm" @click="newOpen = true"><template #prefix><Icon name="plus" :size="13" /></template>New item</Button>
    </template>

    <div class="flex flex-col sm:flex-row flex-wrap items-stretch sm:items-center gap-2">
      <div class="relative flex-1 sm:flex-initial">
        <Icon name="search" :size="13" class="pointer-events-none absolute left-2.5 top-[9px] text-ink-gray-5" />
        <input
          v-model="filters.search"
          class="h-8 w-full sm:w-64 rounded-md border border-outline-gray-3 bg-surface-white pl-8 pr-7 text-sm outline-none focus:border-outline-blue-3"
          placeholder="Search equipment…"
          @input="reload(true)"
        />
        <button
          v-if="filters.search"
          class="absolute right-2 top-2 text-ink-gray-4 hover:text-ink-gray-7"
          @click="filters.search = ''; reload(true)"
        >
          <Icon name="close" :size="13" />
        </button>
      </div>
      <div class="flex items-center gap-2 overflow-x-auto no-scrollbar pb-0.5 sm:pb-0">
        <select v-model="filters.category" class="h-8 rounded-md border border-outline-gray-3 bg-surface-white px-2 py-0 text-sm shrink-0" @change="reload(true)">
          <option value="">All categories</option>
          <option v-for="item in facets.categories" :key="item" :value="item">{{ item }}</option>
        </select>
        <div class="inline-flex overflow-hidden rounded-md border border-outline-gray-3 text-sm shrink-0">
          <button
            v-for="kind in KINDS"
            :key="kind.value"
            class="px-2.5 py-1 text-xs sm:text-sm whitespace-nowrap"
            :class="filters.kind === kind.value ? 'bg-surface-gray-8 text-ink-white font-medium' : 'bg-surface-white text-ink-gray-7 hover:bg-surface-gray-2'"
            @click="filters.kind = kind.value; reload(true)"
          >
            {{ kind.label }}
          </button>
        </div>
        <span class="ml-auto text-xs text-ink-gray-5 shrink-0 hidden sm:inline">{{ number(total) }} items</span>
      </div>
    </div>

    <div v-if="rows.length" class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
      <router-link
        v-for="item in rows"
        :key="item.name"
        :to="{ name: 'item', params: { name: item.name } }"
        class="group overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-white hover:border-outline-gray-4"
      >
        <div class="flex h-28 items-center justify-center bg-surface-gray-2">
          <img v-if="item.image" :src="item.image" class="h-full w-full object-cover" />
          <Icon v-else name="box" :size="30" class="text-ink-gray-4" />
        </div>
        <div class="p-3.5">
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <div class="truncate text-sm font-semibold text-ink-gray-9">{{ item.item_name || item.rental_model }}</div>
              <div class="truncate text-xs text-ink-gray-5">{{ item.category }} · {{ item.brand }}</div>
            </div>
            <Badge :label="item.kind" theme="gray" size="sm" />
          </div>

          <div class="mt-3 flex items-baseline justify-between text-sm">
            <span class="font-semibold tabular text-ink-gray-9">{{ number(item.counts.available) }} <span class="font-normal text-ink-gray-5">available of {{ number(item.counts.total) }}</span></span>
          </div>
          <template v-if="item.kind !== 'Bulk'">
            <div class="mt-1.5 flex h-1.5 overflow-hidden rounded-full bg-surface-gray-2">
              <div class="bg-surface-green-7" :style="{ width: share(item.counts.available, item.counts.total) }" />
              <div class="bg-surface-blue-7" :style="{ width: share(item.counts['At Event'], item.counts.total) }" />
              <div class="bg-surface-amber-7" :style="{ width: share(item.counts['In Maintenance'], item.counts.total) }" />
              <div class="bg-surface-red-7" :style="{ width: share(item.counts.Missing, item.counts.total) }" />
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
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Badge, Button, toast } from 'frappe-ui'
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

const router = useRouter()
const filters = reactive({ search: '', category: '', kind: '' })
const facets = reactive({ categories: [], types: [], brands: [], kinds: [] })
const rows = ref([])
const total = ref(0)
const page = ref(1)
const loading = ref(true)
const newOpen = ref(false)
let timer

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
