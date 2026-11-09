<template>
  <div class="flex h-full overflow-hidden bg-surface-base text-ink-gray-8">
    <!-- Backdrop for Mobile Drawer -->
    <div
      v-if="isMobile && drawerOpen"
      class="fixed inset-0 z-40 bg-black/50 backdrop-blur-xs transition-opacity"
      @click="drawerOpen = false"
    />

    <!-- Sidebar on desktop and tablet, slide-over drawer on mobile -->
    <aside
      class="flex h-full shrink-0 border-r border-outline-gray-1 transition-transform duration-200"
      :class="[isMobile ? 'fixed inset-y-0 left-0 z-50 shadow-2xl' : '', isMobile && !drawerOpen ? '-translate-x-full' : '']"
    >
      <Sidebar v-model:collapsed="collapsed" :disable-collapse="isMobile">
        <div class="px-2">
          <SidebarHeader
            :title="currentWorkspace?.name || 'Rental'"
            :subtitle="userLabel"
            :logo="LOGO"
            :menu-items="appMenu"
          />
        </div>

        <div class="flex-1 overflow-y-auto overflow-x-hidden px-2 pt-1">
          <nav class="flex flex-col gap-0.5">
            <SidebarItem
              v-for="item in navItems"
              :key="item.name"
              :label="item.label"
              :to="item.path"
              :active="isActive(item)"
              @click="drawerOpen = false"
            >
              <template #prefix><Icon :name="item.icon" :size="16" class="text-ink-gray-6" /></template>
              <template v-if="badge(item)" #suffix>
                <span class="mr-2 text-xs-medium text-ink-red-6">{{ badge(item) }}</span>
              </template>
            </SidebarItem>
          </nav>

          <div class="mt-4 flex flex-col gap-0.5">
            <SidebarLabel divider>Quick actions</SidebarLabel>
            <SidebarItem v-if="!bulkFirst" label="Open scanner" icon="lucide-scan-line" @click="mobileScannerOpen = true; drawerOpen = false" />
            <SidebarItem
              label="Check out"
              icon="lucide-log-out"
              :to="{ name: 'movement-new', query: { type: 'CHECK_OUT' } }"
              :active="false"
              @click="drawerOpen = false"
            />
            <SidebarItem
              label="Check in"
              icon="lucide-log-in"
              :to="{ name: 'movement-new', query: { type: 'CHECK_IN' } }"
              :active="false"
              @click="drawerOpen = false"
            />
            <SidebarItem
              label="Report a problem"
              icon="lucide-triangle-alert"
              :to="{ name: 'maintenance', query: { flag: '1' } }"
              :active="false"
              @click="drawerOpen = false"
            />
          </div>
        </div>

        <div class="mt-auto flex flex-col gap-0.5 px-2 pb-2">
          <SidebarItem label="Getting Started" icon="lucide-user-check" @click="gettingStartedOpen = true; drawerOpen = false" />
          <SidebarCollapseToggle v-if="!isMobile" />
        </div>
      </Sidebar>
    </aside>

    <!-- Main Content Container -->
    <div class="flex min-w-0 flex-1 flex-col">
      <!-- Top bar: 48px to line up with the sidebar header, as in Frappe CRM -->
      <header class="flex h-12 shrink-0 items-center gap-2 border-b border-outline-gray-1 bg-surface-base px-3 sm:px-5">
        <!-- Back button on mobile when navigated into a subpage -->
        <button
          v-if="isMobile && canGoBack"
          class="flex h-8 w-8 items-center justify-center rounded-md text-ink-gray-7 active:bg-surface-gray-2"
          title="Back"
          @click="goBack"
        >
          <Icon name="back" :size="15" />
        </button>

        <Breadcrumbs :items="crumbs" class="min-w-0" />

        <div class="ml-auto flex items-center gap-2">
          <!-- Mobile dedicated scan button in header -->
          <button
            v-if="isMobile && !bulkFirst"
            class="flex h-8 items-center gap-1.5 rounded-lg border border-outline-blue-4 bg-surface-blue-2 px-2.5 text-xs-semibold text-ink-blue-8 active:scale-95"
            @click="mobileScannerOpen = true"
          >
            <Icon name="scan" :size="14" />
            <span>Scan</span>
          </button>

          <!-- Desktop ScanBox -->
          <ScanBox v-if="!isMobile && !bulkFirst" />

          <!-- New Movement Button -->
          <Button variant="solid" @click="router.push({ name: 'movement-new' })">
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
        class="fixed bottom-0 inset-x-0 z-30 flex h-16 items-center justify-around border-t border-outline-gray-2 bg-surface-base/95 px-2 backdrop-blur-md pb-[env(safe-area-inset-bottom)] md:hidden shadow-[0_-2px_8px_rgba(0,0,0,0.04)]"
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
        <div v-if="!bulkFirst" class="relative flex flex-1 items-center justify-center">
          <button
            class="relative -top-3.5 flex h-14 w-14 flex-col items-center justify-center rounded-full bg-gradient-to-tr from-surface-blue-9 to-surface-blue-7 text-white shadow-lg ring-4 ring-surface-base active:scale-90 transition-transform"
            title="Open Mobile Scanner"
            @click="mobileScannerOpen = true"
          >
            <Icon name="scan" :size="22" :stroke-width="2.2" />
            <span class="text-[9px] font-bold tracking-tight uppercase">Scan</span>
          </button>
        </div>

        <!-- Tab 4: Units -->
        <router-link
          v-if="!bulkFirst"
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
            class="absolute top-1 right-5 h-2 w-2 rounded-full bg-surface-red-7 ring-1 ring-surface-base"
          />
        </button>
      </nav>
    </div>

    <Dialog v-model="gettingStartedOpen" title="Getting Started">
      <div class="flex flex-col gap-1">
        <router-link
          v-for="step in GETTING_STARTED"
          :key="step.label"
          :to="step.to"
          class="flex items-start gap-3 rounded px-2 py-2 hover:bg-surface-gray-2"
          @click="gettingStartedOpen = false"
        >
          <span :class="step.icon" class="mt-0.5 size-4 shrink-0 text-ink-gray-6" />
          <span>
            <span class="block text-sm-medium text-ink-gray-8">{{ step.label }}</span>
            <span class="block text-sm text-ink-gray-5">{{ step.hint }}</span>
          </span>
        </router-link>
      </div>
    </Dialog>

    <Dialog v-model="aboutOpen" title="About">
        <div class="flex items-center gap-3">
          <img :src="LOGO" class="size-10 rounded-md" alt="" />
          <div>
            <div class="text-base-medium text-ink-gray-9">Rental Management</div>
            <div class="text-sm text-ink-gray-5">Equipment, units, movements and maintenance for event rental.</div>
          </div>
        </div>
    </Dialog>

    <!-- Mobile Scanner Modal -->
    <MobileScannerModal v-model="mobileScannerOpen" />
  </div>
</template>

<script setup>
import { computed, h, inject, onBeforeUnmount, onMounted, provide, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Breadcrumbs,
  Button,
  Dialog,
  Sidebar,
  SidebarCollapseToggle,
  SidebarHeader,
  SidebarItem,
  SidebarLabel,
  call,
  createResource,
  useTheme,
} from 'frappe-ui'
import Icon from './Icon.vue'
import MobileScannerModal from './MobileScannerModal.vue'
import ScanBox from './ScanBox.vue'
import { NAV } from '../router'
import { bulkFirst, currentWorkspace, workspaces } from '../workspace'

const { summary, chooseWorkspace } = inject('rental')
const route = useRoute()
const router = useRouter()

const LOGO = '/assets/rental_management/images/rental.svg'
const userLabel = window.user_fullname || window.user || 'You'
const drawerOpen = ref(false)
const mobileScannerOpen = ref(false)
const aboutOpen = ref(false)
const gettingStartedOpen = ref(false)
const isMobile = ref(false)
// Tablets start on the icon rail; the collapse toggle changes it after that.
const collapsed = ref(window.innerWidth < 1100)

function check() {
  isMobile.value = window.innerWidth < 768
}
onMounted(() => {
  check()
  window.addEventListener('resize', check)
})
onBeforeUnmount(() => window.removeEventListener('resize', check))

// Quantity-first workspaces have no serial units to browse.
const navItems = computed(() => NAV.filter((item) => !(bulkFirst.value && item.name === 'units')))
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

const pageTitle = ref('')
provide('pageTitle', pageTitle)

const crumbs = computed(() => {
  const parent = NAV.find((item) => item.name === route.meta.parent)
  if (!parent) return [{ label: route.meta.title || 'Rental', route: route.fullPath }]
  const leaf = route.name === 'movement-new' ? 'New movement' : pageTitle.value || route.params.name
  return [
    { label: parent.label, route: parent.path },
    { label: leaf, route: route.fullPath },
  ]
})

function badge(item) {
  if (item.name === 'maintenance') return summary.value?.tickets?.length || ''
  return ''
}

// Theme is shared with Desk: start from the user's Desk theme and save changes back to it.
const DESK_THEME = { light: 'Light', dark: 'Dark', system: 'Automatic' }
const { currentTheme, setTheme } = useTheme()
setTheme({ Light: 'light', Dark: 'dark', Automatic: 'system' }[window.desk_theme] || currentTheme.value)
const theme = computed({
  get: () => currentTheme.value,
  set: (value) => {
    setTheme(value)
    call('frappe.core.doctype.user.user.switch_theme', { theme: DESK_THEME[value] })
  },
})

const GETTING_STARTED = [
  { label: 'Add equipment to the catalog', hint: 'Create the item your team rents out.', icon: 'lucide-package-plus', to: { name: 'catalog' } },
  { label: 'Create units', hint: 'Give every physical piece its own barcode.', icon: 'lucide-barcode', to: { name: 'units' } },
  { label: 'Check out for an event', hint: 'Scan what leaves the warehouse.', icon: 'lucide-log-out', to: { name: 'movement-new', query: { type: 'CHECK_OUT' } } },
  { label: 'Check in after the event', hint: 'Scan what comes back.', icon: 'lucide-log-in', to: { name: 'movement-new', query: { type: 'CHECK_IN' } } },
  { label: 'Report a problem', hint: 'Send broken equipment to maintenance.', icon: 'lucide-wrench', to: { name: 'maintenance', query: { flag: '1' } } },
]

// Same source as the Frappe apps screen, so the switcher lists what this user can open.
const apps = createResource({ url: 'frappe.apps.get_apps', auto: true, initialData: [] })
const appIcon = (src) => () => h('img', { src, class: 'size-4 rounded-sm object-cover', alt: '' })

const appMenu = computed(() => [
  {
    group: 'App',
    hideLabel: true,
    options: [
      {
        label: 'Apps',
        icon: 'lucide-layout-grid',
        submenu: [
          { label: 'Desk', icon: 'lucide-box', onClick: () => (window.location.href = '/desk') },
          ...apps.data.map((app) => ({
            label: app.title,
            icon: app.logo ? appIcon(app.logo) : 'lucide-box',
            onClick: () => (window.location.href = app.route),
          })),
        ],
      },
      // Only users with more than one workspace (usually managers) see the switcher.
      ...(workspaces.value.length > 1
        ? [
            {
              label: 'Switch workspace',
              icon: 'lucide-building-2',
              submenu: workspaces.value.map((w) => ({
                label: w.name,
                icon: w.name === currentWorkspace.value?.name ? 'lucide-check' : 'lucide-building',
                onClick: () => chooseWorkspace(w.name),
              })),
            },
          ]
        : []),
      { label: 'Toggle Theme', icon: currentTheme.value === 'dark' ? 'lucide-sun' : 'lucide-moon', onClick: () => (theme.value = currentTheme.value === 'dark' ? 'light' : 'dark') },
      // Placeholder until the app has settings of its own.
      { label: 'Settings', icon: 'lucide-settings', disabled: true },
    ],
  },
  {
    group: 'Help',
    hideLabel: true,
    options: [
      {
        label: 'Help',
        icon: 'lucide-circle-help',
        submenu: [
          { label: 'About', icon: 'lucide-info', onClick: () => (aboutOpen.value = true) },
          ...(window.help_links || []).map((link) => ({
            label: link.label,
            icon: 'lucide-external-link',
            onClick: () => window.open(link.route, '_blank'),
          })),
        ],
      },
    ],
  },
  {
    group: 'Account',
    hideLabel: true,
    options: [{ label: 'Log out', icon: 'lucide-log-out', onClick: logout }],
  },
])

async function logout() {
  await call('logout')
  window.location.href = '/login'
}

provide('scanner', {
  openScanner: () => {
    mobileScannerOpen.value = true
  },
})
</script>
