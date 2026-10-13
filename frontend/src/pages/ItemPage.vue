<template>
  <PageFrame
    :title="item ? item.item_name || item.rental_model : 'Catalog item'"
    :subtitle="item ? `${item.category} · ${item.brand || ''} · ${item.kind}` : ''"
    :back-to="{ name: 'catalog' }"
    back-label="Catalog"
  >
    <template #actions>
      <template v-if="data">
        <Button v-if="data.can.generate" size="sm" variant="solid" @click="generateOpen = true">
          <template #prefix><Icon name="plus" :size="13" /></template>Create units
        </Button>
        <Button v-if="data.can.receive" size="sm" variant="solid" @click="receiveOpen = true">
          <template #prefix><Icon name="plus" :size="13" /></template>Receive stock
        </Button>
        <a :href="`/desk/item/${encodeURIComponent(item.name)}`" target="_blank">
          <Button size="sm" variant="ghost"><template #prefix><Icon name="external" :size="13" /></template>Desk</Button>
        </a>
      </template>
    </template>

    <div v-if="!data" class="p-10 text-center text-sm text-ink-gray-5">{{ failure || 'Loading…' }}</div>

    <template v-else>
      <div class="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <button
          v-for="stat in stats"
          :key="stat.label"
          class="rounded-lg border border-outline-gray-2 bg-surface-white p-4 text-left hover:border-outline-gray-4"
          :disabled="item.kind === 'Bulk'"
          @click="filterUnits(stat.query)"
        >
          <div class="text-[11px] font-medium uppercase tracking-wide text-ink-gray-5">{{ stat.label }}</div>
          <div class="mt-1 text-2xl font-semibold tabular text-ink-gray-9">{{ number(stat.value) }}</div>
        </button>
      </div>

      <section v-if="item.kind !== 'Bulk'" class="overflow-hidden rounded-xl border border-outline-gray-2 bg-surface-white shadow-xs">
        <header class="flex items-center justify-between border-b border-outline-gray-1 px-4 py-2.5">
          <span class="text-sm font-semibold text-ink-gray-9">Units <span class="font-mono text-xs font-normal text-ink-gray-5">{{ item.serial_no_series }}</span></span>
          <router-link :to="{ name: 'units', query: { item_code: item.name } }" class="text-xs font-semibold text-ink-blue-6 hover:underline">Open in Units</router-link>
        </header>
        <table class="w-full text-sm">
          <tbody>
            <tr
              v-for="unit in units"
              :key="unit.name"
              class="cursor-pointer border-b border-outline-gray-1 last:border-0 hover:bg-surface-gray-1 active:bg-surface-gray-2"
              @click="router.push({ name: 'unit', params: { name: unit.name } })"
            >
              <td class="px-3 sm:px-4 py-2.5 font-mono text-xs font-semibold text-ink-gray-9">{{ unit.serial_no }}</td>
              <td class="px-2 sm:px-3 py-2.5"><StatusBadge :value="unit.status" size="sm" /></td>
              <td class="px-2 sm:px-3 py-2.5"><StatusBadge :value="unit.condition" kind="condition" size="sm" /></td>
              <td class="px-2 sm:px-3 py-2.5 text-xs text-ink-gray-7 truncate max-w-[120px] sm:max-w-none">{{ unit.location || '—' }}</td>
              <td class="hidden sm:table-cell px-4 py-2.5 text-right text-xs text-ink-gray-5">{{ timeAgo(unit.modified) }}</td>
            </tr>
            <tr v-if="!units.length">
              <td class="px-4 py-10 text-center text-sm text-ink-gray-5">
                No units yet.
                <button v-if="data.can.generate" class="text-ink-blue-6 hover:underline" @click="generateOpen = true">Create the first ones</button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="unitTotal > units.length" class="border-t border-outline-gray-1 px-4 py-2 text-xs text-ink-gray-5">
          Showing {{ units.length }} of {{ unitTotal }} —
          <router-link :to="{ name: 'units', query: { item_code: item.name } }" class="text-ink-blue-6 hover:underline">see all</router-link>
        </div>
      </section>

      <section v-else class="overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-white">
        <header class="border-b border-outline-gray-1 px-4 py-2.5 text-sm font-semibold text-ink-gray-9">Bulk stock</header>
        <table class="w-full text-sm">
          <tbody>
            <tr v-for="row in data.stock" :key="row.status" class="border-b border-outline-gray-1 last:border-0">
              <td class="px-4 py-2.5"><StatusBadge :value="row.status" /></td>
              <td class="px-3 py-2.5 text-ink-gray-7">{{ row.place }}</td>
              <td class="px-4 py-2.5 text-right tabular font-medium">{{ number(row.qty) }} {{ item.stock_uom }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </template>

    <Dialog v-model="generateOpen" :options="{ title: 'Create units', size: 'sm' }">
      <template #body-content>
        <label class="grid gap-1 text-sm">
          <span class="text-ink-gray-6">How many units? (1 to 50)</span>
          <input v-model.number="count" type="number" min="1" max="50" class="h-8 rounded-md border border-outline-gray-3 px-2.5 outline-none focus:border-outline-blue-3" @keydown.enter="generate" />
          <span class="text-xs text-ink-gray-5">New serial numbers follow {{ item?.serial_no_series }} and go into the warehouse.</span>
        </label>
        <div class="mt-4 flex justify-end gap-2">
          <Button label="Cancel" @click="generateOpen = false" />
          <Button variant="solid" label="Create" :loading="busy" @click="generate" />
        </div>
      </template>
    </Dialog>

    <Dialog v-model="receiveOpen" :options="{ title: 'Receive bulk stock', size: 'sm' }">
      <template #body-content>
        <label class="grid gap-1 text-sm">
          <span class="text-ink-gray-6">Quantity to add to the warehouse</span>
          <input v-model.number="quantity" type="number" min="1" class="h-8 rounded-md border border-outline-gray-3 px-2.5 outline-none focus:border-outline-blue-3" @keydown.enter="receive" />
        </label>
        <div class="mt-4 flex justify-end gap-2">
          <Button label="Cancel" @click="receiveOpen = false" />
          <Button variant="solid" label="Receive" :loading="busy" @click="receive" />
        </div>
      </template>
    </Dialog>
  </PageFrame>
</template>

<script setup>
import { computed, inject, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, Dialog, toast } from 'frappe-ui'
import Icon from '../components/Icon.vue'
import PageFrame from '../components/PageFrame.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { api, readError } from '../api'
import { number, timeAgo } from '../format'

const route = useRoute()
const router = useRouter()
const { refreshSummary } = inject('rental')

const data = ref(null)
const failure = ref('')
const units = ref([])
const unitTotal = ref(0)
const busy = ref(false)
const generateOpen = ref(false)
const receiveOpen = ref(false)
const count = ref(5)
const quantity = ref(10)

const item = computed(() => data.value?.item)

const stats = computed(() => {
  const c = item.value.counts
  const code = item.value.name
  return [
    { label: 'Total', value: c.total, query: { item_code: code } },
    { label: 'Available', value: c.available, query: { item_code: code, status: 'Warehouse', condition: 'OK' } },
    { label: 'At events', value: c['At Event'], query: { item_code: code, status: 'At Event' } },
    { label: 'In repair', value: c['In Maintenance'], query: { item_code: code, status: 'In Maintenance' } },
    { label: 'Missing', value: c.Missing, query: { item_code: code, status: 'Missing' } },
    { label: 'Need attention', value: c.needs_attention, query: { item_code: code } },
  ]
})

const filterUnits = (query) => router.push({ name: 'units', query })

async function load() {
  try {
    data.value = await api.getItem(route.params.name)
    if (data.value.item.kind !== 'Bulk') {
      const result = await api.listUnits({ item_code: route.params.name, page_length: 12 })
      units.value = result.rows
      unitTotal.value = result.total
    }
  } catch (err) {
    failure.value = readError(err)
  }
}

async function run(request, message, close) {
  busy.value = true
  try {
    const result = await request()
    toast.success(message(result))
    close()
    await load()
    refreshSummary()
  } catch (err) {
    toast.error(readError(err))
  } finally {
    busy.value = false
  }
}

const generate = () =>
  run(() => api.generateUnits(item.value.name, count.value), (result) => `${result.units_created.length} units created`, () => (generateOpen.value = false))

const receive = () =>
  run(() => api.receiveStock(item.value.name, quantity.value), () => `${quantity.value} ${item.value.stock_uom} received`, () => (receiveOpen.value = false))

onMounted(load)
</script>
