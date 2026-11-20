<template>
  <!-- One request card: every list sent for the event, merged on one page but kept apart by list -->
  <PageFrame :title="req ? req.title : 'Request'" :subtitle="req ? subtitle : ''" :back-to="{ name: 'requests' }" back-label="Requests" narrow>
    <template #actions>
      <template v-if="req">
        <RequestBadge :request="req" size="md" />
        <template v-if="data.can_write">
          <Button v-if="req.status === 'Pending'" variant="subtle" theme="red" size="sm" label="Reject" @click="rejectOpen = true" />
          <Button v-if="req.status === 'Pending'" variant="solid" size="sm" :label="req.needs_review ? 'Accept changes' : 'Accept'" :loading="busy" @click="setStatus('Accepted')" />
          <Button v-if="req.status === 'Accepted'" variant="solid" size="sm" label="Mark checked out" :loading="busy" @click="setStatus('Checked out')" />
          <Button v-if="req.status === 'Checked out'" variant="solid" size="sm" label="Mark returned" :loading="busy" @click="setStatus('Returned')" />
        </template>
      </template>
    </template>

    <div v-if="!data" class="p-10 text-center text-sm text-ink-gray-5">{{ failure || 'Loading…' }}</div>

    <template v-else>
      <div v-if="req.needs_review && req.status === 'Pending'" class="flex items-start gap-2 rounded-lg border border-outline-amber-2 bg-surface-amber-1 p-3 text-sm text-ink-amber-8">
        <Icon name="alert" :size="15" class="mt-0.5 shrink-0" />
        <span>Changed since the warehouse answered. Changed lines and lists are marked; accepting again clears the marks.</span>
      </div>
      <div v-if="req.status === 'Rejected'" class="rounded-lg border border-outline-red-2 bg-surface-red-1 p-3 text-sm text-ink-red-8">
        <b>Rejected:</b> {{ req.reject_reason }}
      </div>

      <section class="grid gap-x-6 gap-y-3 rounded-lg border border-outline-gray-2 bg-surface-base p-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <div><div class="text-xs text-ink-gray-5">Client</div><div class="font-medium text-ink-gray-9">{{ req.customer || '—' }}</div></div>
        <div><div class="text-xs text-ink-gray-5">Dates</div><div class="font-medium text-ink-gray-9">{{ dates }}</div></div>
        <div><div class="text-xs text-ink-gray-5">Venue</div><div class="font-medium text-ink-gray-9">{{ req.location || '—' }}</div></div>
        <div>
          <div class="text-xs text-ink-gray-5">Requested by</div>
          <div class="font-medium text-ink-gray-9">{{ userName(req.requested_by) || '—' }}</div>
        </div>
        <div v-if="req.accepted_at" class="sm:col-span-2">
          <div class="text-xs text-ink-gray-5">Last accepted</div>
          <div class="text-ink-gray-8">{{ fullDate(req.accepted_at) }} by {{ userName(req.accepted_by) }}</div>
        </div>
        <div v-if="req.reference_name" class="sm:col-span-2">
          <div class="text-xs text-ink-gray-5">From</div>
          <a :href="sourceLink" class="text-ink-blue-7 hover:underline">{{ req.reference_doctype }} {{ req.reference_name }}</a>
        </div>
      </section>

      <section v-for="s in data.sections" :key="s.source" class="overflow-hidden rounded-xl border bg-surface-base shadow-xs" :class="s.changed ? 'border-outline-amber-3' : 'border-outline-gray-2'">
        <header class="flex flex-wrap items-center gap-2 border-b border-outline-gray-1 px-4 py-2.5">
          <span>{{ s.icon || '📦' }}</span>
          <span class="text-sm-semibold text-ink-gray-9">{{ s.title }}</span>
          <span v-if="s.department" class="text-xs text-ink-gray-5">{{ s.department }}</span>
          <span class="ml-auto flex items-center gap-2 text-xs">
            <span v-if="s.lines_removed" class="text-ink-amber-7">{{ s.lines_removed }} line{{ s.lines_removed === 1 ? '' : 's' }} removed</span>
            <Badge v-if="s.changed" label="Changed" theme="orange" size="sm" />
            <span class="text-ink-gray-5">{{ s.lines.length }} line{{ s.lines.length === 1 ? '' : 's' }}</span>
          </span>
        </header>
        <table class="w-full text-sm">
          <tbody>
            <tr v-for="line in s.lines" :key="line.name" class="border-b border-outline-gray-1 last:border-0" :class="line.changed && 'bg-surface-amber-1'">
              <td class="px-4 py-2.5 text-ink-gray-8">
                {{ line.item }}
                <span v-if="line.changed" class="ml-1 text-[11px] font-medium text-ink-amber-7">changed</span>
                <div v-if="line.note" class="text-xs text-ink-gray-5">{{ line.note }}</div>
              </td>
              <td class="w-20 px-3 py-2.5 text-right tabular text-ink-gray-9">{{ number(line.qty) }}</td>
              <td class="w-16 px-4 py-2.5 text-xs text-ink-gray-5">{{ line.unit }}</td>
            </tr>
            <tr v-if="!s.lines.length"><td colspan="3" class="px-4 py-6 text-center text-sm text-ink-gray-5">No lines.</td></tr>
          </tbody>
        </table>
      </section>
      <div v-if="!data.sections.length" class="p-8 text-center text-sm text-ink-gray-5">No lists on this request.</div>
    </template>

    <Dialog v-model="rejectOpen" :options="{ title: 'Reject request' }">
      <template #body-content>
        <FormControl v-model="reason" type="textarea" label="Why?" placeholder="e.g. The LED screens are booked that week." />
        <p class="mt-2 text-xs text-ink-gray-5">The team that asked sees the reason on their lists.</p>
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
import { useRoute } from 'vue-router'
import { Badge, Button, Dialog, FormControl, toast } from 'frappe-ui'
import Icon from '../components/Icon.vue'
import PageFrame from '../components/PageFrame.vue'
import RequestBadge from '../components/RequestBadge.vue'
import { api, readError } from '../api'
import { fullDate, number, shortDate, userName } from '../format'

const route = useRoute()
const data = ref(null)
const failure = ref('')
const busy = ref(false)
const rejectOpen = ref(false)
const reason = ref('')
const req = computed(() => data.value?.request)
const subtitle = computed(() => `${req.value.name} · ${data.value.sections.length} list${data.value.sections.length === 1 ? '' : 's'}`)
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

onMounted(load)
</script>
