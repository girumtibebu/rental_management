<template>
  <!-- What other teams ask the warehouse for, one request per event, soonest first -->
  <PageFrame title="Requests" :subtitle="todo ? `${number(todo)} waiting for the warehouse` : 'Nothing waiting'">
    <div class="flex flex-col overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-base">
      <div class="flex flex-col gap-2.5 border-b border-outline-gray-2 p-3 sm:p-3.5">
        <TextInput v-model="search" type="search" class="w-full" placeholder="Search event, client or venue…" @update:model-value="reload(true)">
          <template #prefix><Icon name="search" :size="14" class="text-ink-gray-5" /></template>
        </TextInput>
        <div class="no-scrollbar flex items-center gap-1.5 overflow-x-auto pb-0.5">
          <button
            v-for="option in FILTERS"
            :key="option.value"
            class="shrink-0 rounded px-2.5 py-1 text-sm transition-colors"
            :class="status === option.value ? 'bg-surface-gray-3 text-ink-gray-9' : 'text-ink-gray-6 hover:bg-surface-gray-2'"
            @click="(status = option.value), reload(true)"
          >
            {{ option.label }}
          </button>
        </div>
      </div>

      <div class="divide-y divide-outline-gray-1">
        <div
          v-for="req in rows"
          :key="req.name"
          class="flex cursor-pointer items-center gap-3 p-3.5 transition-colors hover:bg-surface-gray-1 active:bg-surface-gray-2 sm:px-4"
          @click="router.push({ name: 'request', params: { name: req.name } })"
        >
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-x-2 gap-y-1">
              <span class="truncate text-sm-semibold text-ink-gray-9">{{ req.title }}</span>
              <span class="font-mono text-[11px] text-ink-gray-5">{{ req.name }}</span>
              <RequestBadge :request="req" />
            </div>
            <div class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-ink-gray-6">
              <span v-if="req.customer">{{ req.customer }}</span>
              <span class="flex items-center gap-1"><Icon name="clock" :size="11" /> {{ dates(req) }}</span>
              <span v-if="req.location" class="flex items-center gap-1"><Icon name="pin" :size="11" /> {{ req.location }}</span>
            </div>
          </div>
          <div class="shrink-0 text-right text-xs text-ink-gray-6">
            <div>
              <strong class="tabular text-ink-gray-8">{{ req.lines }}</strong> line{{ req.lines === 1 ? '' : 's' }} · {{ req.sections }} list{{ req.sections === 1 ? '' : 's' }}
            </div>
            <div v-if="req.changed" class="text-ink-amber-7">{{ req.changed }} changed</div>
          </div>
          <Icon name="chevright" :size="15" class="shrink-0 text-ink-gray-4" />
        </div>
        <div v-if="!rows.length && !loading" class="p-10 text-center text-sm text-ink-gray-5">
          <Icon name="tag" :size="28" class="mx-auto mb-2 text-ink-gray-4" />
          {{ status === 'todo' ? 'No requests waiting.' : 'No requests here.' }}
        </div>
      </div>

      <Pagination v-model:page="page" :total="total" :page-length="PAGE" @update:page="reload(false)" />
    </div>
  </PageFrame>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { TextInput, toast } from 'frappe-ui'
import Icon from '../components/Icon.vue'
import PageFrame from '../components/PageFrame.vue'
import Pagination from '../components/Pagination.vue'
import RequestBadge from '../components/RequestBadge.vue'
import { api, readError } from '../api'
import { number, shortDate } from '../format'

const PAGE = 25
const FILTERS = [
  { value: 'todo', label: 'Waiting' },
  { value: 'Accepted', label: 'Accepted' },
  { value: 'Checked out', label: 'Checked out' },
  { value: 'Returned', label: 'Returned' },
  { value: 'Rejected', label: 'Rejected' },
  { value: '', label: 'All' },
]

const router = useRouter()
const rows = ref([])
const total = ref(0)
const todo = ref(0)
const page = ref(1)
const search = ref('')
const status = ref('todo')
const loading = ref(true)
let timer

const dates = (r) => (!r.start_date ? 'No dates' : r.end_date && r.end_date !== r.start_date ? `${shortDate(r.start_date)} – ${shortDate(r.end_date)}` : shortDate(r.start_date))

async function load() {
  loading.value = true
  try {
    const result = await api.listRequests({ status: status.value, search: search.value, page: page.value, page_length: PAGE })
    rows.value = result.rows
    total.value = result.total
    todo.value = result.todo
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
