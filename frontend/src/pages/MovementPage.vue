<template>
  <PageFrame
    :title="move ? move.name : 'Movement'"
    :subtitle="move ? `${fullDate(move.creation)} · ${userName(move.owner)}` : ''"
    :back-to="{ name: 'movements' }"
    back-label="Movements"
    narrow
  >
    <template #actions>
      <template v-if="move">
        <StatusBadge :value="move.transaction_type" kind="type" size="md" />
        <a :href="`/desk/stock-entry/${encodeURIComponent(move.name)}`" target="_blank">
          <Button size="sm" variant="ghost"><template #prefix><Icon name="external" :size="13" /></template>Desk</Button>
        </a>
      </template>
    </template>

    <div v-if="!data" class="p-10 text-center text-sm text-ink-gray-5">{{ failure || 'Loading…' }}</div>

    <template v-else>
      <section class="grid gap-x-6 gap-y-3 rounded-lg border border-outline-gray-2 bg-surface-white p-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <div><div class="text-xs text-ink-gray-5">From</div><div class="font-medium text-ink-gray-9">{{ move.from_location || '—' }}</div></div>
        <div><div class="text-xs text-ink-gray-5">To</div><div class="font-medium text-ink-gray-9">{{ move.to_location || '—' }}</div></div>
        <div><div class="text-xs text-ink-gray-5">Issued to</div><div class="font-medium text-ink-gray-9">{{ move.issued_to || '—' }}</div></div>
        <div><div class="text-xs text-ink-gray-5">Received by</div><div class="font-medium text-ink-gray-9">{{ move.received_by || '—' }}</div></div>
        <div v-if="data.note" class="sm:col-span-2 lg:col-span-4">
          <div class="text-xs text-ink-gray-5">Note</div>
          <div class="whitespace-pre-line text-ink-gray-8">{{ data.note }}</div>
        </div>
      </section>

      <section class="overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-white">
        <header class="border-b border-outline-gray-1 px-4 py-2.5 text-sm font-semibold text-ink-gray-9">Units ({{ data.units.length }})</header>
        <table class="w-full text-sm">
          <tbody>
            <tr
              v-for="row in data.units"
              :key="row.name"
              class="cursor-pointer border-b border-outline-gray-1 last:border-0 hover:bg-surface-gray-1"
              @click="router.push({ name: 'unit', params: { name: row.name } })"
            >
              <td class="px-4 py-2.5 font-mono text-xs font-medium text-ink-gray-9">{{ row.serial_no }}</td>
              <td class="px-3 py-2.5 text-ink-gray-7">{{ row.item_name }}</td>
              <td class="px-3 py-2.5 text-xs text-ink-gray-6">from {{ row.previous || '—' }}</td>
              <td class="px-4 py-2.5 text-right"><StatusBadge :value="row.condition" kind="condition" /></td>
            </tr>
            <tr v-if="!data.units.length"><td class="px-4 py-8 text-center text-sm text-ink-gray-5">No serialised units on this movement.</td></tr>
          </tbody>
        </table>
      </section>

      <section v-if="data.bulk.length" class="overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-white">
        <header class="border-b border-outline-gray-1 px-4 py-2.5 text-sm font-semibold text-ink-gray-9">Bulk items ({{ data.bulk.length }})</header>
        <table class="w-full text-sm">
          <tbody>
            <tr v-for="row in data.bulk" :key="row.item_code" class="border-b border-outline-gray-1 last:border-0">
              <td class="px-4 py-2.5 font-medium text-ink-gray-8">{{ row.item_name || row.item_code }}</td>
              <td class="px-3 py-2.5 text-right tabular">× {{ row.qty }}</td>
              <td class="px-4 py-2.5 text-xs text-ink-gray-5">{{ row.uom }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </template>
  </PageFrame>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button } from 'frappe-ui'
import Icon from '../components/Icon.vue'
import PageFrame from '../components/PageFrame.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { api, readError } from '../api'
import { fullDate, userName } from '../format'

const route = useRoute()
const router = useRouter()
const data = ref(null)
const failure = ref('')
const move = computed(() => data.value?.movement)

onMounted(async () => {
  try {
    data.value = await api.getMovement(route.params.name)
  } catch (err) {
    failure.value = readError(err)
  }
})
</script>
