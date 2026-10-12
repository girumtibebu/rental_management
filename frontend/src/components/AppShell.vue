<template>
  <div class="flex h-full overflow-hidden bg-surface-gray-1 text-ink-gray-8">
    <div v-if="isMobile && drawerOpen" class="fixed inset-0 z-40 bg-black-overlay-200" @click="drawerOpen = false" />

    <aside
      class="z-50 flex shrink-0 flex-col border-r border-outline-gray-2 bg-surface-gray-1 transition-all"
      :class="[
        rail ? 'w-[56px]' : 'w-[240px]',
        isMobile ? 'fixed inset-y-0 left-0 shadow-xl' : '',
        isMobile && !drawerOpen ? '-translate-x-full' : '',
      ]"
    >
      <div class="flex items-center gap-2.5 border-b border-outline-gray-2 p-3.5" :class="rail ? 'justify-center' : ''">
        <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-surface-gray-9 text-[11px] font-bold text-ink-white">RM</span>
        <div v-if="!rail" class="min-w-0 leading-tight">
          <div class="truncate text-sm font-semibold text-ink-gray-9">Rental Management</div>
          <div class="text-[10px] uppercase tracking-widest text-ink-gray-5">Warehouse operations</div>
        </div>
        <button
          v-if="!rail"
          class="ml-auto flex h-6 w-6 items-center justify-center rounded border border-outline-gray-2 text-ink-gray-6 hover:bg-surface-gray-2"
          title="Back to Desk"
          @click="goToDesk"
        >
          <Icon name="close" :size="12" />
        </button>
      </div>

      <div v-if="!rail" class="px-4 pb-2 pt-4 text-[10px] font-semibold uppercase tracking-widest text-ink-gray-5">Workspace</div>
      <nav class="flex flex-col gap-0.5 px-2" :class="rail ? 'pt-3' : ''">
        <router-link v-for="item in NAV" :key="item.name" :to="item.path" custom v-slot="{ navigate }">
          <button
            class="flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm"
            :class="[
              isActive(item) ? 'bg-surface-white font-medium text-ink-gray-9 shadow-sm ring-1 ring-outline-gray-2' : 'text-ink-gray-7 hover:bg-surface-gray-2',
              rail ? 'justify-center' : '',
            ]"
            :title="rail ? item.label : undefined"
            @click="navigate(); drawerOpen = false"
          >
            <Icon :name="item.icon" :size="15" />
            <span v-if="!rail" class="flex-1 text-left">{{ item.label }}</span>
            <span
              v-if="!rail && badge(item)"
              class="rounded-full px-1.5 text-[10px] font-medium"
              :class="item.name === 'maintenance' ? 'bg-surface-red-2 text-ink-red-6' : 'bg-surface-gray-3 text-ink-gray-6'"
            >{{ badge(item) }}</span>
          </button>
        </router-link>
      </nav>

      <template v-if="!rail">
        <div class="px-4 pb-2 pt-5 text-[10px] font-semibold uppercase tracking-widest text-ink-gray-5">Quick actions</div>
        <div class="flex flex-col gap-1.5 px-2.5">
          <router-link :to="{ name: 'movement-new', query: { type: 'CHECK_OUT' } }" class="flex items-center gap-2 rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2 text-sm hover:border-outline-gray-4">
            <Icon name="out" :size="14" class="text-ink-blue-6" /> Check out equipment
          </router-link>
          <router-link :to="{ name: 'movement-new', query: { type: 'CHECK_IN' } }" class="flex items-center gap-2 rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2 text-sm hover:border-outline-gray-4">
            <Icon name="in" :size="14" class="text-ink-green-6" /> Check in equipment
          </router-link>
          <router-link :to="{ name: 'maintenance', query: { flag: '1' } }" class="flex items-center gap-2 rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2 text-sm hover:border-outline-gray-4">
            <Icon name="alert" :size="14" class="text-ink-amber-6" /> Report a problem
          </router-link>
        </div>

        <div class="px-4 pb-2 pt-5 text-[10px] font-semibold uppercase tracking-widest text-ink-gray-5">Right now</div>
        <div v-if="summary" class="mx-2.5 grid grid-cols-2 gap-1.5">
          <router-link
            v-for="stat in stats"
            :key="stat.label"
            :to="{ name: 'units', query: stat.query }"
            class="rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2 hover:border-outline-gray-4"
          >
            <div class="text-lg font-semibold leading-tight tabular text-ink-gray-9">{{ stat.value }}</div>
            <div class="text-[11px] text-ink-gray-5">{{ stat.label }}</div>
          </router-link>
        </div>
      </template>

      <div class="mt-auto flex items-center gap-2 border-t border-outline-gray-2 px-3 py-2.5" :class="rail ? 'justify-center' : ''">
        <Avatar :label="userLabel" size="sm" />
        <div v-if="!rail" class="min-w-0">
          <div class="truncate text-xs font-medium text-ink-gray-8">{{ userLabel }}</div>
          <div class="text-[11px] text-ink-gray-5">Signed in</div>
        </div>
      </div>
    </aside>

    <div class="flex min-w-0 flex-1 flex-col">
      <header class="flex h-[52px] shrink-0 items-center gap-2.5 border-b border-outline-gray-2 bg-surface-white px-4">
        <button
          v-if="isMobile"
          class="flex h-8 w-8 items-center justify-center rounded-md border border-outline-gray-2 text-ink-gray-6"
          @click="drawerOpen = !drawerOpen"
        >
          <Icon name="menu" :size="15" />
        </button>
        <button
          class="flex h-7 items-center gap-1.5 rounded-md border border-outline-gray-2 bg-surface-white px-2.5 text-xs font-medium text-ink-gray-7 hover:bg-surface-gray-1"
          @click="goToDesk"
        >
          <Icon name="back" :size="12" /> <span class="hidden sm:inline">Desk</span>
        </button>
        <Icon name="chevright" :size="12" class="text-ink-gray-4" />
        <div class="min-w-0 truncate text-sm font-semibold text-ink-gray-9">{{ route.meta.title || 'Rental Management' }}</div>

        <div class="ml-auto flex items-center gap-2">
          <ScanBox />
          <Button size="sm" variant="solid" @click="router.push({ name: 'movement-new' })">
            <template #prefix><Icon name="plus" :size="13" /></template>
            New movement
          </Button>
        </div>
      </header>

      <main class="flex min-h-0 flex-1 flex-col overflow-hidden"><slot /></main>
    </div>
  </div>
</template>

<script setup>
import { computed, inject, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Avatar, Button } from 'frappe-ui'
import Icon from './Icon.vue'
import ScanBox from './ScanBox.vue'
import { NAV } from '../router'

const { summary } = inject('rental')
const route = useRoute()
const router = useRouter()

const userLabel = window.user_fullname || window.user || 'You'
const drawerOpen = ref(false)
const isMobile = ref(false)
const isTablet = ref(false)
const rail = computed(() => isTablet.value && !isMobile.value)

function check() {
  isMobile.value = window.innerWidth < 768
  isTablet.value = window.innerWidth >= 768 && window.innerWidth < 1100
}
onMounted(() => {
  check()
  window.addEventListener('resize', check)
})
onBeforeUnmount(() => window.removeEventListener('resize', check))

const isActive = (item) => route.name === item.name || route.meta.parent === item.name

const stats = computed(() => {
  const totals = summary.value?.totals
  if (!totals) return []
  return [
    { label: 'In warehouse', value: totals.Warehouse, query: { status: 'Warehouse' } },
    { label: 'At events', value: totals['At Event'], query: { status: 'At Event' } },
    { label: 'In repair', value: totals['In Maintenance'], query: { status: 'In Maintenance' } },
    { label: 'Need attention', value: totals.needs_attention, query: {} },
  ]
})

function badge(item) {
  const totals = summary.value?.totals
  if (!totals) return ''
  if (item.name === 'maintenance') return summary.value.tickets.length || ''
  return ''
}

function goToDesk() {
  window.location.href = '/desk'
}
</script>
