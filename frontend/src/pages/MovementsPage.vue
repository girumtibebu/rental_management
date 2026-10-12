<template>
  <PageFrame title="Movements" :subtitle="`${number(total)} recorded`">
    <template #actions>
      <Button variant="solid" size="sm" @click="router.push({ name: 'movement-new' })"><template #prefix><Icon name="plus" :size="13" /></template>New movement</Button>
    </template>

    <div class="flex flex-col overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-white">
      <div class="flex flex-wrap items-center gap-2 border-b border-outline-gray-2 px-3 py-2.5">
        <div class="relative">
          <Icon name="search" :size="13" class="pointer-events-none absolute left-2.5 top-[9px] text-ink-gray-5" />
          <input
            v-model="search"
            class="h-8 w-60 rounded-md border border-outline-gray-3 bg-surface-white pl-8 pr-2 text-sm outline-none focus:border-outline-blue-3"
            placeholder="Number, place or person…"
            @input="reload(true)"
          />
        </div>
        <div class="inline-flex overflow-hidden rounded-md border border-outline-gray-3 text-sm">
          <button
            v-for="option in TYPE_FILTERS"
            :key="option.value"
            class="px-3 py-1"
            :class="type === option.value ? 'bg-surface-gray-8 text-ink-white' : 'bg-surface-white text-ink-gray-7 hover:bg-surface-gray-2'"
            @click="type = option.value; reload(true)"
          >
            {{ option.label }}
          </button>
        </div>
      </div>

      <table class="w-full text-sm">
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
            <td class="px-3 py-2.5 text-ink-gray-7">{{ move.issued_to || move.recieved_by || userName(move.owner) }}</td>
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
