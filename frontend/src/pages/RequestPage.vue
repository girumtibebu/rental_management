<template>
  <!-- One request card: every list sent for the event, one table each. The warehouse answers; it never edits the lists. -->
  <PageFrame :title="req ? req.title : 'Request'" :subtitle="req ? subtitle : ''" :back-to="{ name: 'requests' }" back-label="Requests" narrow>
    <template #actions>
      <template v-if="req">
        <RequestBadge :request="req" size="md" />
        <template v-if="data.can_write">
          <Button v-if="req.status === 'Pending'" theme="red" label="Reject" @click="rejectOpen = true" />
          <Button v-if="req.status === 'Pending'" variant="solid" :label="req.needs_review ? 'Accept changes' : 'Accept'" :loading="busy" @click="setStatus('Accepted')" />
          <Button v-if="req.status === 'Accepted'" variant="solid" label="Check out items" icon-left="lucide-log-out" @click="movement('CHECK_OUT')" />
          <Button v-if="req.status === 'Checked out'" label="Check in items" icon-left="lucide-log-in" @click="movement('CHECK_IN')" />
          <Button v-if="req.status === 'Checked out'" variant="solid" label="Mark returned" :loading="busy" @click="setStatus('Returned')" />
        </template>
      </template>
    </template>

    <div v-if="!data" class="p-10 text-center text-sm text-ink-gray-5">{{ failure || 'Loading…' }}</div>

    <template v-else>
      <div v-if="req.needs_review && req.status === 'Pending'" class="flex items-start gap-2 rounded-md bg-surface-amber-1 px-3 py-2 text-sm text-ink-amber-8">
        <span class="lucide-triangle-alert mt-0.5 size-4 shrink-0" />
        <span>Changed since you last accepted it. Changed lines and lists are marked; accepting again clears the marks.</span>
      </div>
      <div v-if="req.status === 'Rejected'" class="rounded-md bg-surface-red-1 px-3 py-2 text-sm text-ink-red-4"><b>Rejected:</b> {{ req.reject_reason }}</div>

      <dl class="grid gap-x-6 gap-y-3 rounded-lg border border-outline-gray-2 p-4 text-base sm:grid-cols-2 lg:grid-cols-4">
        <div><dt class="text-sm text-ink-gray-5">Client</dt><dd class="text-ink-gray-9">{{ req.customer || '—' }}</dd></div>
        <div><dt class="text-sm text-ink-gray-5">Dates</dt><dd class="text-ink-gray-9">{{ dates }}</dd></div>
        <div><dt class="text-sm text-ink-gray-5">Venue</dt><dd class="text-ink-gray-9">{{ req.location || '—' }}</dd></div>
        <div>
          <dt class="text-sm text-ink-gray-5">From</dt>
          <dd><a v-if="req.reference_name" :href="sourceLink" class="text-ink-gray-9 underline decoration-outline-gray-3 underline-offset-2 hover:decoration-ink-gray-6">{{ req.reference_name }}</a></dd>
        </div>
      </dl>

      <section v-for="s in data.sections" :key="s.source">
        <header class="mb-2 flex flex-wrap items-center gap-2">
          <span>{{ s.icon || '📦' }}</span>
          <h2 class="text-lg font-semibold text-ink-gray-9">{{ s.title }}</h2>
          <span v-if="s.department" class="text-sm text-ink-gray-5">{{ s.department }}</span>
          <Badge v-if="s.changed" label="Changed" theme="orange" />
          <span class="ml-auto text-sm text-ink-gray-5">{{ s.lines.length }} line{{ s.lines.length === 1 ? '' : 's' }}</span>
        </header>
        <table class="w-full border-separate border-spacing-0 text-base">
          <thead>
            <tr class="text-left text-sm text-ink-gray-5">
              <th class="h-8 w-10 rounded-l-md bg-surface-gray-2 pl-3 font-normal">#</th>
              <th class="h-8 bg-surface-gray-2 px-2 font-normal">Item</th>
              <th class="h-8 w-24 bg-surface-gray-2 px-2 text-right font-normal">Qty</th>
              <th class="h-8 w-20 bg-surface-gray-2 px-2 font-normal">Unit</th>
              <th class="h-8 rounded-r-md bg-surface-gray-2 px-2 font-normal">Note</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(line, i) in s.lines" :key="line.name">
              <td class="h-10 border-b border-outline-gray-1 pl-3 text-sm text-ink-gray-4">{{ i + 1 }}</td>
              <td class="h-10 border-b border-outline-gray-1 px-2 text-ink-gray-8">
                {{ line.item }}
                <Badge v-if="line.changed" label="Changed" theme="orange" class="ml-1.5" />
              </td>
              <td class="h-10 border-b border-outline-gray-1 px-2 text-right tabular text-ink-gray-9">{{ number(line.qty) }}</td>
              <td class="h-10 border-b border-outline-gray-1 px-2 text-ink-gray-6">{{ line.unit }}</td>
              <td class="h-10 border-b border-outline-gray-1 px-2 text-ink-gray-6">{{ line.note }}</td>
            </tr>
            <tr v-for="r in s.removed" :key="r" class="text-ink-gray-4">
              <td class="h-10 border-b border-outline-gray-1 pl-3"><span class="lucide-minus block size-3.5" /></td>
              <td colspan="4" class="h-10 border-b border-outline-gray-1 px-2 line-through">{{ r }} <span class="ml-1.5 no-underline">removed</span></td>
            </tr>
            <tr v-if="!s.lines.length && !s.removed.length"><td colspan="5" class="py-6 text-center text-sm text-ink-gray-5">No lines.</td></tr>
          </tbody>
        </table>
      </section>
      <div v-if="!data.sections.length" class="p-8 text-center text-sm text-ink-gray-5">No lists on this request.</div>

      <section v-if="data.movements.length">
        <h2 class="mb-2 text-lg font-semibold text-ink-gray-9">Movements</h2>
        <div class="divide-y divide-outline-gray-1 rounded-lg border border-outline-gray-2">
          <RouterLink v-for="m in data.movements" :key="m.name" :to="{ name: 'movement', params: { name: m.name } }" class="flex items-center gap-3 px-3 py-2.5 text-base hover:bg-surface-gray-1">
            <StatusBadge :value="m.transaction_type" kind="type" />
            <span class="font-mono text-sm text-ink-gray-7">{{ m.name }}</span>
            <span class="truncate text-ink-gray-6">{{ m.venue || m.issued_to || m.received_by }}</span>
            <span class="ml-auto text-sm text-ink-gray-5">{{ shortDate(m.posting_date) }}</span>
          </RouterLink>
        </div>
      </section>

      <section v-if="data.versions.length">
        <h2 class="mb-2 text-lg font-semibold text-ink-gray-9">Versions</h2>
        <ol class="flex flex-col gap-2 text-base">
          <li v-for="v in data.versions" :key="v.version" class="flex flex-wrap items-baseline gap-x-2">
            <span class="w-8 text-sm text-ink-gray-5">v{{ v.version }}</span>
            <span class="text-ink-gray-8">{{ v.section }}</span>
            <span class="text-ink-gray-6">{{ v.summary }}</span>
            <span class="ml-auto text-sm text-ink-gray-5">{{ userName(v.sent_by) }} · {{ timeAgo(v.sent_at) }}</span>
          </li>
        </ol>
      </section>
    </template>

    <Dialog v-model="rejectOpen" :options="{ title: 'Reject request' }">
      <template #body-content>
        <FormControl v-model="reason" type="textarea" label="Why?" placeholder="e.g. The LED screens are booked that week." />
        <p class="mt-2 text-sm text-ink-gray-5">The team that sent it sees the reason on their lists.</p>
      </template>
      <template #actions>
        <div class="flex justify-end gap-2">
          <Button label="Cancel" @click="rejectOpen = false" />
          <Button variant="solid" theme="red" label="Reject" :disabled="!reason.trim()" :loading="busy" @click="reject" />
        </div>
      </template>
    </Dialog>
  </PageFrame>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Badge, Button, Dialog, FormControl, toast } from 'frappe-ui'
import PageFrame from '../components/PageFrame.vue'
import RequestBadge from '../components/RequestBadge.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { api, readError } from '../api'
import { number, shortDate, timeAgo, userName } from '../format'

const route = useRoute()
const router = useRouter()
const data = ref(null)
const failure = ref('')
const busy = ref(false)
const rejectOpen = ref(false)
const reason = ref('')
const req = computed(() => data.value?.request)
const subtitle = computed(() => `${req.value.name} · v${req.value.version || 1} · ${data.value.sections.length} list${data.value.sections.length === 1 ? '' : 's'}`)
const dates = computed(() => {
  const r = req.value
  if (!r.start_date) return 'No dates'
  return r.end_date && r.end_date !== r.start_date ? `${shortDate(r.start_date)} – ${shortDate(r.end_date)}` : shortDate(r.start_date)
})
// a planner project opens in the planner; anything else in the desk
const sourceLink = computed(() => (req.value.reference_doctype === 'Project' ? `/planner/${req.value.reference_name}` : `/app/${req.value.reference_doctype.toLowerCase().replace(/ /g, '-')}/${req.value.reference_name}`))

async function load() {
  try {
    data.value = await api.getRequest(route.params.name)
  } catch (err) {
    failure.value = readError(err)
  }
}

async function setStatus(status, why) {
  busy.value = true
  try {
    data.value = await api.setRequestStatus(req.value.name, status, why)
    toast.success(`Request ${status.toLowerCase()}`)
  } catch (err) {
    toast.error(readError(err))
  } finally {
    busy.value = false
  }
}

async function reject() {
  await setStatus('Rejected', reason.value.trim())
  rejectOpen.value = false
}

const movement = (type) => router.push({ name: 'movement-new', query: { type, request: req.value.name } })

onMounted(load)
</script>
