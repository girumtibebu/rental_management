<template>
  <div class="flex min-h-0 flex-1 flex-col overflow-y-auto">
    <div class="flex flex-1 flex-col gap-3.5 sm:gap-4 p-3.5 sm:p-5 pb-20 sm:pb-6" :class="narrow ? 'mx-auto w-full max-w-5xl' : ''">
      <div v-if="title" class="flex flex-wrap items-center justify-between gap-2.5 sm:gap-3">
        <div class="min-w-0 flex-1">
          <router-link v-if="backTo" :to="backTo" class="mb-1 inline-flex items-center gap-1 text-xs text-ink-gray-5 hover:text-ink-gray-8">
            <Icon name="back" :size="11" /> {{ backLabel }}
          </router-link>
          <h1 class="truncate text-base sm:text-lg font-bold text-ink-gray-9">{{ title }}</h1>
          <p v-if="subtitle" class="truncate text-xs text-ink-gray-5">{{ subtitle }}</p>
        </div>
        <div class="flex flex-wrap items-center gap-1.5 sm:gap-2"><slot name="actions" /></div>
      </div>
      <slot />
    </div>
  </div>
</template>

<script setup>
import Icon from './Icon.vue'

defineProps({
  title: String,
  subtitle: String,
  backTo: [String, Object],
  backLabel: String,
  narrow: Boolean,
})
</script>
