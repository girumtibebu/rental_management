import { createRouter, createWebHistory } from 'vue-router'

export const NAV = [
  { name: 'dashboard', path: '/', label: 'Dashboard', icon: 'home' },
  { name: 'catalog', path: '/catalog', label: 'Catalog', icon: 'box' },
  { name: 'units', path: '/units', label: 'Units', icon: 'layers' },
  { name: 'movements', path: '/movements', label: 'Movements', icon: 'truck' },
  { name: 'maintenance', path: '/maintenance', label: 'Maintenance', icon: 'wrench' },
]

export default createRouter({
  history: createWebHistory('/rental'),
  routes: [
    { path: '/', name: 'dashboard', component: () => import('./pages/DashboardPage.vue'), meta: { title: 'Dashboard' } },
    { path: '/catalog', name: 'catalog', component: () => import('./pages/CatalogPage.vue'), meta: { title: 'Catalog' } },
    { path: '/catalog/:name', name: 'template', component: () => import('./pages/TemplatePage.vue'), meta: { title: 'Catalog', parent: 'catalog' } },
    { path: '/units', name: 'units', component: () => import('./pages/UnitsPage.vue'), meta: { title: 'Units' } },
    { path: '/units/:name', name: 'unit', component: () => import('./pages/UnitPage.vue'), meta: { title: 'Units', parent: 'units' } },
    { path: '/movements', name: 'movements', component: () => import('./pages/MovementsPage.vue'), meta: { title: 'Movements' } },
    { path: '/movements/new', name: 'movement-new', component: () => import('./pages/MovementNewPage.vue'), meta: { title: 'New movement', parent: 'movements' } },
    { path: '/movements/:name', name: 'movement', component: () => import('./pages/MovementPage.vue'), meta: { title: 'Movements', parent: 'movements' } },
    { path: '/maintenance', name: 'maintenance', component: () => import('./pages/MaintenancePage.vue'), meta: { title: 'Maintenance' } },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})
