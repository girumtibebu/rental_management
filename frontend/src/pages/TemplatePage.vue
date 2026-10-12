<template>
  <PageFrame
    :title="template ? template.item_name || template.item_model : 'Catalog item'"
    :subtitle="template ? `${template.item_category} · ${template.item_brand} · ${template.kind}` : ''"
    :back-to="{ name: 'catalog' }"
    back-label="Catalog"
  >
    <template #actions>
      <template v-if="data">
        <Badge v-if="template.status === 'Draft'" label="Draft" theme="orange" size="md" />
        <Button v-if="data.can.activate" size="sm" variant="solid" :loading="busy" @click="activate">Activate</Button>
        <Button v-if="data.can.generate" size="sm" variant="solid" @click="generateOpen = true">
          <template #prefix><Icon name="plus" :size="13" /></template>Create units
        </Button>
        <a :href="`/desk/rental-item-template/${encodeURIComponent(template.name)}`" target="_blank">
          <Button size="sm" variant="ghost"><template #prefix><Icon name="external" :size="13" /></template>Desk</Button>
        </a>
      </template>
    </template>

    <div v-if="!data" class="p-10 text-center text-sm text-ink-gray-5">{{ failure || 'Loading…' }}</div>

    <template v-else>
      <div v-if="template.kind !== 'Bulk'" class="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <button
          v-for="stat in stats"
          :key="stat.label"
          class="rounded-lg border border-outline-gray-2 bg-surface-white p-4 text-left hover:border-outline-gray-4"
          @click="filterUnits(stat.query)"
        >
          <div class="text-[11px] font-medium uppercase tracking-wide text-ink-gray-5">{{ stat.label }}</div>
          <div class="mt-1 text-2xl font-semibold tabular text-ink-gray-9">{{ stat.value }}</div>
        </button>
      </div>

      <section v-if="template.kind !== 'Bulk'" class="overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-white">
        <header class="flex items-center justify-between border-b border-outline-gray-1 px-4 py-2.5">
          <span class="text-sm font-semibold text-ink-gray-9">Units</span>
          <router-link :to="{ name: 'units', query: { template: template.name } }" class="text-xs text-ink-blue-6 hover:underline">Open in Units</router-link>
        </header>
        <table class="w-full text-sm">
          <tbody>
            <tr
              v-for="unit in units"
              :key="unit.name"
              class="cursor-pointer border-b border-outline-gray-1 last:border-0 hover:bg-surface-gray-1"
              @click="router.push({ name: 'unit', params: { name: unit.name } })"
            >
              <td class="px-4 py-2.5 font-mono text-xs font-medium text-ink-gray-9">{{ unit.unit_serial_number || unit.name }}</td>
              <td class="px-3 py-2.5"><StatusBadge :value="unit.movement_status" /></td>
              <td class="px-3 py-2.5"><StatusBadge :value="unit.unit_condition" kind="condition" /></td>
              <td class="px-3 py-2.5 text-ink-gray-7">{{ unit.location || '—' }}</td>
              <td class="px-4 py-2.5 text-right text-xs text-ink-gray-5">{{ timeAgo(unit.modified) }}</td>
            </tr>
            <tr v-if="!units.length">
              <td class="px-4 py-10 text-center text-sm text-ink-gray-5">
                No units yet.
                <button v-if="data.can.generate" class="text-ink-blue-6 hover:underline" @click="generateOpen = true">Create the first ones</button>
                <span v-else-if="template.status === 'Draft'">Activate this item first.</span>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="unitTotal > units.length" class="border-t border-outline-gray-1 px-4 py-2 text-xs text-ink-gray-5">
          Showing {{ units.length }} of {{ unitTotal }} —
          <router-link :to="{ name: 'units', query: { template: template.name } }" class="text-ink-blue-6 hover:underline">see all</router-link>
        </div>
      </section>

      <section v-else class="overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-white">
        <header class="border-b border-outline-gray-1 px-4 py-2.5 text-sm font-semibold text-ink-gray-9">Bulk stock</header>
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-outline-gray-1 bg-surface-gray-1 text-[11px] uppercase tracking-wide text-ink-gray-5">
              <th class="px-4 py-2 text-left font-medium">Name</th>
              <th class="px-3 py-2 text-left font-medium">Type</th>
              <th class="px-3 py-2 text-right font-medium">Quantity</th>
              <th class="px-3 py-2 text-right font-medium">Available</th>
              <th class="px-4 py-2 text-left font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in data.bulk" :key="item.name" class="border-b border-outline-gray-1 last:border-0">
              <td class="px-4 py-2.5 font-medium text-ink-gray-8">{{ item.name1 || item.name }} <span class="text-xs text-ink-gray-5">{{ item.size }}</span></td>
              <td class="px-3 py-2.5 text-ink-gray-7">{{ item.bulk_type }}</td>
              <td class="px-3 py-2.5 text-right tabular">{{ number(item.quantity) }} {{ item.uom }}</td>
              <td class="px-3 py-2.5 text-right tabular">{{ number(item.total_availability) }}</td>
              <td class="px-4 py-2.5"><Badge :label="item.status" :theme="item.status === 'Active' ? 'green' : 'gray'" size="sm" /></td>
            </tr>
            <tr v-if="!data.bulk.length"><td colspan="5" class="px-4 py-10 text-center text-sm text-ink-gray-5">No bulk stock recorded for this item.</td></tr>
          </tbody>
        </table>
      </section>
    </template>

    <Dialog v-model="generateOpen" :options="{ title: 'Create units', size: 'sm' }">
      <template #body-content>
        <label class="grid gap-1 text-sm">
          <span class="text-ink-gray-6">How many units? (1 to 50)</span>
          <input v-model.number="count" type="number" min="1" max="50" class="h-8 rounded-md border border-outline-gray-3 px-2.5 outline-none focus:border-outline-blue-3" @keydown.enter="generate" />
          <span class="text-xs text-ink-gray-5">Serial numbers continue after the highest one in use ({{ template?.sku_naming_series }}).</span>
        </label>
        <div class="mt-4 flex justify-end gap-2">
          <Button label="Cancel" @click="generateOpen = false" />
          <Button variant="solid" label="Create" :loading="busy" @click="generate" />
        </div>
      </template>
    </Dialog>
  </PageFrame>
</template>

<script setup>
import { computed, inject, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Badge, Button, Dialog, toast } from 'frappe-ui'
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
const count = ref(5)

const template = computed(() => data.value?.template)

const stats = computed(() => {
  const c = template.value.counts
  const name = template.value.name
  return [
    { label: 'Total', value: c.total, query: { template: name } },
    { label: 'Available', value: c.available, query: { template: name, status: 'Warehouse', condition: 'OK' } },
    { label: 'At events', value: c['At Event'], query: { template: name, status: 'At Event' } },
    { label: 'In repair', value: c['In Maintenance'], query: { template: name, status: 'In Maintenance' } },
    { label: 'Missing', value: c.Missing, query: { template: name, status: 'Missing' } },
    { label: 'Need attention', value: c.needs_attention, query: { template: name } },
  ]
})

const filterUnits = (query) => router.push({ name: 'units', query })

async function load() {
  try {
    data.value = await api.getTemplate(route.params.name)
    if (data.value.template.kind !== 'Bulk') {
      const result = await api.listUnits({ template: route.params.name, page_length: 12 })
      units.value = result.rows
      unitTotal.value = result.total
    }
  } catch (err) {
    failure.value = readError(err)
  }
}

async function activate() {
  busy.value = true
  try {
    data.value = await api.activateTemplate(template.value.name)
    toast.success('Item activated')
  } catch (err) {
    toast.error(readError(err))
  } finally {
    busy.value = false
  }
}

async function generate() {
  busy.value = true
  try {
    const result = await api.generateUnits(template.value.name, count.value)
    toast.success(`${result.units_created.length} units created`)
    generateOpen.value = false
    await load()
    refreshSummary()
  } catch (err) {
    toast.error(readError(err))
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>
