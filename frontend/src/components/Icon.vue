<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 16 16"
    fill="none"
    stroke="currentColor"
    :stroke-width="strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path :d="PATHS[name] || ''" />
  </svg>
</template>

<script setup>
defineProps({ name: String, size: { type: Number, default: 16 }, strokeWidth: { type: Number, default: 1.6 } })

const PATHS = {
  home: 'M2.5 7.5 8 2.5l5.5 5M3.5 7v6h9V7',
  box: 'M2.5 5 8 2.5 13.5 5v6L8 13.5 2.5 11zM2.5 5 8 7.5 13.5 5M8 7.5v6',
  layers: 'M8 2.5 13.5 5.5 8 8.5 2.5 5.5zM2.5 8 8 11l5.5-3M2.5 10.5 8 13.5l5.5-3',
  truck: 'M2 4.5h7v6H2zM9 6.5h3l2 2v2H9zM4.5 12.5a1 1 0 1 0 0-2 1 1 0 0 0 0 2ZM11.5 12.5a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z',
  wrench: 'M10.5 2.5a3 3 0 0 0-2.8 4L2.8 11.4a1.3 1.3 0 0 0 1.8 1.8L9.5 8.3a3 3 0 0 0 4-2.8L11.7 7.3 9.2 6.8 8.7 4.3z',
  scan: 'M2.5 5V3.5a1 1 0 0 1 1-1H5M11 2.5h1.5a1 1 0 0 1 1 1V5M13.5 11v1.5a1 1 0 0 1-1 1H11M5 13.5H3.5a1 1 0 0 1-1-1V11M5 8h6',
  search: 'M7 2.5a4.5 4.5 0 1 1 0 9 4.5 4.5 0 0 1 0-9ZM10.5 10.5l3 3',
  plus: 'M8 3v10M3 8h10',
  close: 'M4 4l8 8M12 4l-8 8',
  check: 'M3 8.5 6.5 12 13 4',
  alert: 'M8 2.5 14 13H2zM8 6.5v3M8 11.3h.01',
  back: 'M13 8H3M7 4 3 8l4 4',
  chevright: 'M6 4l4 4-4 4',
  chevdown: 'M4 6l4 4 4-4',
  arrow: 'M3 8h10M9 4l4 4-4 4',
  out: 'M6 3.5H3.5v9H6M10 5.5 12.5 8 10 10.5M12.5 8H6.5',
  in: 'M10 3.5h2.5v9H10M6 5.5 3.5 8 6 10.5M3.5 8h6',
  pin: 'M8 14s4.5-4 4.5-7.5a4.5 4.5 0 1 0-9 0C3.5 10 8 14 8 14ZM8 8.3a1.8 1.8 0 1 0 0-3.6 1.8 1.8 0 0 0 0 3.6Z',
  clock: 'M8 13.5a5.5 5.5 0 1 0 0-11 5.5 5.5 0 0 0 0 11ZM8 5v3.5L10 10',
  user: 'M8 8.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5ZM3 13c.5-2 2.5-3 5-3s4.5 1 5 3',
  dots: 'M3.5 8h.01M8 8h.01M12.5 8h.01',
  external: 'M9 3h4v4M13 3 7.5 8.5M11 9.5V13H3V5h3.5',
  menu: 'M2 4h12M2 8h12M2 12h12',
  tag: 'M2.5 8.5v-5h5l6 6-5 5zM5.2 5.2h.01',
  image: 'M2.5 3.5h11v9h-11zM2.5 10 6 7l3 2.5L11 8l2.5 2',
  refresh: 'M13 5.5A5.5 5.5 0 0 0 3.2 7M3 2.5V7h4.5M3 10.5A5.5 5.5 0 0 0 12.8 9M13 13.5V9H8.5',
  filter: 'M2.5 3.5h11l-4 5v4l-3-1.5v-2.5z',
  camera: 'M2.5 5h2.2l1-2h4.6l1 2h2.2a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1h-11a1 1 0 0 1-1-1v-7a1 1 0 0 1 1-1ZM8 12.2a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z',
  flash: 'M8.5 2 3.5 9h4.5l-1 5 6-7.5H8.5z',
  barcode: 'M2 3.5v9M4 3.5v9M6.5 3.5v9M8.5 3.5v9M11 3.5v9M13.5 3.5v9',
  sparkle: 'M8 1.5l1.5 4 4 1.5-4 1.5-1.5 4-1.5-4-4-1.5 4-1.5z',
}
</script>
