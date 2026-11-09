<template>
  <div class="flex h-full items-center justify-center bg-surface-gray-1 p-4">
    <div class="w-full max-w-sm rounded-xl border border-outline-gray-1 bg-surface-base p-5 shadow-sm">
      <h1 class="text-lg-semibold text-ink-gray-9">Choose a workspace</h1>
      <p class="mt-1 text-p-sm text-ink-gray-6">You can switch later from the menu at the top left.</p>
      <div class="mt-4 flex flex-col gap-2">
        <button
          v-for="w in workspaces"
          :key="w.name"
          class="flex items-center justify-between rounded-lg border border-outline-gray-2 px-3 py-2.5 text-left hover:bg-surface-gray-2"
          @click="$emit('choose', w.name)"
        >
          <span>
            <span class="block text-base-medium text-ink-gray-9">{{ w.name }}</span>
            <span class="block text-sm text-ink-gray-6">{{ w.company }} · {{ w.mode || 'Serial First' }}</span>
          </span>
          <Icon name="chevright" :size="14" class="text-ink-gray-5" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import Icon from './Icon.vue'

defineProps({ workspaces: { type: Array, required: true } })
defineEmits(['choose'])
</script>
