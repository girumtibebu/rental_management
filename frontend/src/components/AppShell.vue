<template>
  <div class="flex h-full overflow-hidden bg-surface-gray-1 text-ink-gray-8">
    <!-- Backdrop for Mobile Drawer -->
    <div
      v-if="isMobile && drawerOpen"
      class="fixed inset-0 z-40 bg-black/50 backdrop-blur-xs transition-opacity"
      @click="drawerOpen = false"
    />

    <!-- Aside Navigation: Sidebar on Desktop, Slide-over Drawer on Mobile -->
    <aside
      class="z-50 flex shrink-0 flex-col border-r border-outline-gray-2 bg-surface-gray-1 transition-transform duration-200"
      :class="[
        rail ? 'w-[56px]' : 'w-[250px]',
        isMobile ? 'fixed inset-y-0 left-0 shadow-2xl' : '',
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
          v-if="isMobile || !rail"
          class="ml-auto flex h-7 w-7 items-center justify-center rounded border border-outline-gray-2 text-ink-gray-6 hover:bg-surface-gray-2 active:bg-surface-gray-3"
          :title="isMobile ? 'Close menu' : 'Back to Desk'"
          @click="isMobile ? (drawerOpen = false) : goToDesk()"
        >
          <Icon name="close" :size="13" />
        </button>
      </div>

      <div v-if="!rail" class="px-4 pb-2 pt-4 text-[10px] font-semibold uppercase tracking-widest text-ink-gray-5">Workspace</div>
      <nav class="flex flex-col gap-0.5 px-2" :class="rail ? 'pt-3' : ''">
        <router-link v-for="item in NAV" :key="item.name" :to="item.path" custom v-slot="{ navigate }">
          <button
            class="flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors"
            :class="[
              isActive(item) ? 'bg-surface-white font-medium text-ink-gray-9 shadow-xs ring-1 ring-outline-gray-2' : 'text-ink-gray-7 hover:bg-surface-gray-2',
              rail ? 'justify-center' : '',
            ]"
            :title="rail ? item.label : undefined"
            @click="navigate(); drawerOpen = false"
          >
            <Icon :name="item.icon" :size="16" />
            <span v-if="!rail" class="flex-1 text-left">{{ item.label }}</span>
            <span
              v-if="!rail && badge(item)"
              class="rounded-full px-1.5 py-0.2 text-[10px] font-medium"
              :class="item.name === 'maintenance' ? 'bg-surface-red-2 text-ink-red-6' : 'bg-surface-gray-3 text-ink-gray-6'"
            >{{ badge(item) }}</span>
          </button>
        </router-link>
      </nav>

      <template v-if="!rail">
        <div class="px-4 pb-2 pt-4 text-[10px] font-semibold uppercase tracking-widest text-ink-gray-5">Quick actions</div>
        <div class="flex flex-col gap-1.5 px-2.5">
          <button
            class="flex items-center gap-2 rounded-lg border border-outline-blue-3 bg-surface-blue-2 px-3 py-2 text-sm font-medium text-ink-blue-8 hover:bg-surface-blue-3 active:scale-98"
            @click="mobileScannerOpen = true; drawerOpen = false"
          >
            <Icon name="scan" :size="15" class="text-ink-blue-6" /> Open Scanner
          </button>
          <router-link
            :to="{ name: 'movement-new', query: { type: 'CHECK_OUT' } }"
            class="flex items-center gap-2 rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2 text-sm hover:border-outline-gray-4 active:bg-surface-gray-1"
            @click="drawerOpen = false"
          >
            <Icon name="out" :size="14" class="text-ink-blue-6" /> Check out equipment
          </router-link>
          <router-link
            :to="{ name: 'movement-new', query: { type: 'CHECK_IN' } }"
            class="flex items-center gap-2 rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2 text-sm hover:border-outline-gray-4 active:bg-surface-gray-1"
            @click="drawerOpen = false"
          >
            <Icon name="in" :size="14" class="text-ink-green-6" /> Check in equipment
          </router-link>
          <router-link
            :to="{ name: 'maintenance', query: { flag: '1' } }"
            class="flex items-center gap-2 rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2 text-sm hover:border-outline-gray-4 active:bg-surface-gray-1"
            @click="drawerOpen = false"
          >
            <Icon name="alert" :size="14" class="text-ink-amber-6" /> Report a problem
          </router-link>
        </div>

        <div class="px-4 pb-2 pt-4 text-[10px] font-semibold uppercase tracking-widest text-ink-gray-5">Right now</div>
        <div v-if="summary" class="mx-2.5 grid grid-cols-2 gap-1.5">
          <router-link
            v-for="stat in stats"
            :key="stat.label"
            :to="{ name: 'units', query: stat.query }"
            class="rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2 hover:border-outline-gray-4 active:bg-surface-gray-1"
            @click="drawerOpen = false"
          >
            <div class="text-lg font-semibold leading-tight tabular text-ink-gray-9">{{ stat.value }}</div>
            <div class="text-[11px] text-ink-gray-5">{{ stat.label }}</div>
          </router-link>
        </div>
      </template>

      <div class="mt-auto flex items-center justify-between border-t border-outline-gray-2 px-3 py-2.5" :class="rail ? 'justify-center' : ''">
        <div class="flex items-center gap-2 min-w-0">
          <Avatar :label="userLabel" size="sm" />
          <div v-if="!rail" class="min-w-0">
            <div class="truncate text-xs font-medium text-ink-gray-8">{{ userLabel }}</div>
            <div class="text-[11px] text-ink-gray-5">Signed in</div>
          </div>
        </div>
        <button
          v-if="!rail"
          class="flex h-7 items-center gap-1 rounded border border-outline-gray-2 bg-surface-white px-2 text-xs text-ink-gray-6 hover:bg-surface-gray-2"
          title="Open ERPNext Desk"
          @click="goToDesk"
        >
          <Icon name="external" :size="11" /> Desk
        </button>
      </div>
    </aside>

    <!-- Main Content Container -->
    <div class="flex min-w-0 flex-1 flex-col">
      <!-- Top App Bar -->
      <header class="flex h-[52px] shrink-0 items-center gap-2.5 border-b border-outline-gray-2 bg-surface-white px-3 sm:px-4">
        <!-- Back button on mobile when navigated into a subpage -->
        <button
          v-if="isMobile && canGoBack"
          class="flex h-8 w-8 items-center justify-center rounded-md border border-outline-gray-2 text-ink-gray-7 active:bg-surface-gray-2"
          title="Back"
          @click="goBack"
        >
          <Icon name="back" :size="15" />
        </button>
        <span
          v-else-if="isMobile"
          class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-surface-gray-9 text-[11px] font-bold text-ink-white"
        >
          RM
        </span>

        <button
          v-if="!isMobile"
          class="flex h-7 items-center gap-1.5 rounded-md border border-outline-gray-2 bg-surface-white px-2.5 text-xs font-medium text-ink-gray-7 hover:bg-surface-gray-1"
          @click="goToDesk"
        >
          <Icon name="back" :size="12" /> Desk
        </button>
        <Icon v-if="!isMobile" name="chevright" :size="12" class="text-ink-gray-4" />

        <div class="min-w-0 truncate text-sm font-semibold text-ink-gray-9">
          {{ route.meta.title || 'Rental Management' }}
        </div>

        <div class="ml-auto flex items-center gap-2">
          <!-- Mobile dedicated scan button in header -->
          <button
            v-if="isMobile"
            class="flex h-8 items-center gap-1.5 rounded-lg border border-outline-blue-3 bg-surface-blue-2 px-2.5 text-xs font-semibold text-ink-blue-8 active:scale-95"
            @click="mobileScannerOpen = true"
          >
            <Icon name="scan" :size="14" />
            <span>Scan</span>
          </button>

          <!-- Desktop ScanBox -->
          <ScanBox v-if="!isMobile" />

          <!-- New Movement Button -->
          <Button size="sm" variant="solid" @click="router.push({ name: 'movement-new' })">
            <template #prefix><Icon name="plus" :size="13" /></template>
            <span class="hidden sm:inline">New movement</span>
          </Button>
        </div>
      </header>

      <!-- Scrollable Main View (with bottom padding on mobile for tab bar) -->
      <main class="flex min-h-0 flex-1 flex-col overflow-hidden pb-16 md:pb-0">
        <slot />
      </main>

      <!-- Mobile Dedicated Bottom Tab Bar -->
      <nav
        class="fixed bottom-0 inset-x-0 z-30 flex h-16 items-center justify-around border-t border-outline-gray-2 bg-surface-white/95 px-2 backdrop-blur-md pb-[env(safe-area-inset-bottom)] md:hidden shadow-[0_-2px_8px_rgba(0,0,0,0.04)]"
      >
        <!-- Tab 1: Dashboard (Home) -->
        <router-link
          to="/"
          class="flex flex-1 flex-col items-center justify-center py-1 text-[11px] transition-colors"
          :class="route.name === 'dashboard' ? 'text-ink-blue-6 font-semibold' : 'text-ink-gray-6 active:text-ink-gray-9'"
        >
          <Icon name="home" :size="18" />
          <span class="mt-0.5">Home</span>
        </router-link>

        <!-- Tab 2: Movements -->
        <router-link
          to="/movements"
          class="flex flex-1 flex-col items-center justify-center py-1 text-[11px] transition-colors"
          :class="isMovementActive ? 'text-ink-blue-6 font-semibold' : 'text-ink-gray-6 active:text-ink-gray-9'"
        >
          <Icon name="truck" :size="18" />
          <span class="mt-0.5">Move</span>
        </router-link>

        <!-- Tab 3: Prominent Center Raised SCAN Button -->
        <div class="relative flex flex-1 items-center justify-center">
          <button
            class="relative -top-3.5 flex h-14 w-14 flex-col items-center justify-center rounded-full bg-gradient-to-tr from-surface-blue-7 to-surface-blue-5 text-white shadow-lg ring-4 ring-surface-white active:scale-90 transition-transform"
            title="Open Mobile Scanner"
            @click="mobileScannerOpen = true"
          >
            <Icon name="scan" :size="22" :stroke-width="2.2" />
            <span class="text-[9px] font-bold tracking-tight uppercase">Scan</span>
          </button>
        </div>

        <!-- Tab 4: Units -->
        <router-link
          to="/units"
          class="flex flex-1 flex-col items-center justify-center py-1 text-[11px] transition-colors"
          :class="isUnitsActive ? 'text-ink-blue-6 font-semibold' : 'text-ink-gray-6 active:text-ink-gray-9'"
        >
          <Icon name="layers" :size="18" />
          <span class="mt-0.5">Units</span>
        </router-link>

        <!-- Tab 5: More Menu -->
        <button
          class="relative flex flex-1 flex-col items-center justify-center py-1 text-[11px] transition-colors"
          :class="drawerOpen ? 'text-ink-blue-6 font-semibold' : 'text-ink-gray-6 active:text-ink-gray-9'"
          @click="drawerOpen = !drawerOpen"
        >
          <Icon name="menu" :size="18" />
          <span class="mt-0.5">More</span>
          <span
            v-if="summary?.tickets?.length"
            class="absolute top-1 right-5 h-2 w-2 rounded-full bg-surface-red-5 ring-1 ring-surface-white"
          />
        </button>
      </nav>
    </div>

    <!-- Mobile Scanner Modal -->
    <MobileScannerModal v-model="mobileScannerOpen" />
  </div>
</template>

<script setup>
import { computed, inject, onBeforeUnmount, onMounted, provide, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Avatar, Button } from 'frappe-ui'
import Icon from './Icon.vue'
import MobileScannerModal from './MobileScannerModal.vue'
import ScanBox from './ScanBox.vue'
import { NAV } from '../router'

const { summary } = inject('rental')
const route = useRoute()
const router = useRouter()

const userLabel = window.user_fullname || window.user || 'You'
const drawerOpen = ref(false)
const mobileScannerOpen = ref(false)
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
const isMovementActive = computed(() => ['movements', 'movement', 'movement-new'].includes(route.name))
const isUnitsActive = computed(() => ['units', 'unit'].includes(route.name))

const canGoBack = computed(() => Boolean(route.meta.parent) || route.path !== '/')

function goBack() {
  if (route.meta.parent) {
    router.push({ name: route.meta.parent })
  } else {
    router.back()
  }
}

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

provide('scanner', {
  openScanner: () => {
    mobileScannerOpen.value = true
  },
})
</script>
