<template>
  <div class="flex min-h-0 flex-1 flex-col overflow-y-auto">
    <div class="flex flex-1 flex-col gap-3.5 sm:gap-4 p-3.5 sm:p-5 pb-20 sm:pb-6" :class="narrow ? 'mx-auto w-full max-w-5xl' : ''">
      <div v-if="subtitle || $slots.actions" class="flex flex-wrap items-center justify-between gap-2.5 sm:gap-3">
        <p class="min-w-0 flex-1 truncate text-sm text-ink-gray-5">{{ subtitle }}</p>
        <div class="flex flex-wrap items-center gap-1.5 sm:gap-2"><slot name="actions" /></div>
      </div>
      <slot />
    </div>
  </div>
</template>

<script setup>
import { inject, onBeforeUnmount, watchEffect } from 'vue'

const props = defineProps({
  title: String,
  subtitle: String,
  backTo: [String, Object],
  backLabel: String,
  narrow: Boolean,
})

// Hand the title to the header breadcrumbs (AppShell) instead of repeating it on the page.
const pageTitle = inject('pageTitle', null)
if (pageTitle) {
  watchEffect(() => (pageTitle.value = props.title || ''))
  onBeforeUnmount(() => {
    if (pageTitle.value === (props.title || '')) pageTitle.value = ''
  })
}
</script>
