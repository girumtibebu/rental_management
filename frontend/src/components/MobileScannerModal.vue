<template>
  <div v-if="modelValue" class="fixed inset-0 z-50 flex flex-col bg-black/80 backdrop-blur-sm">
    <!-- Top Header Bar -->
    <div class="flex items-center justify-between border-b border-white/10 bg-surface-gray-9/90 px-4 py-3 text-white">
      <div class="flex items-center gap-2">
        <span class="flex h-7 w-7 items-center justify-center rounded-lg bg-surface-blue-6 text-white">
          <Icon name="scan" :size="16" />
        </span>
        <div>
          <div class="text-sm font-semibold leading-tight">Mobile Scanner</div>
          <div class="text-[11px] text-white/60">Scan serial or equipment barcode</div>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <button
          v-if="hasTorch"
          class="flex h-8 w-8 items-center justify-center rounded-full border border-white/20 transition-colors"
          :class="torchOn ? 'bg-amber-400 text-black' : 'bg-white/10 text-white'"
          title="Toggle Flashlight"
          @click="toggleTorch"
        >
          <Icon name="flash" :size="15" />
        </button>
        <button
          class="flex h-8 w-8 items-center justify-center rounded-full bg-white/10 text-white hover:bg-white/20"
          title="Close scanner"
          @click="close"
        >
          <Icon name="close" :size="16" />
        </button>
      </div>
    </div>

    <!-- Main Scanner Body -->
    <div class="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <!-- Camera Viewport / Reticle -->
      <div class="relative flex flex-col items-center justify-center bg-black min-h-[220px] sm:min-h-[280px] overflow-hidden">
        <video
          v-show="cameraActive"
          ref="videoRef"
          autoplay
          playsinline
          muted
          class="h-full max-h-[360px] w-full object-cover"
        />

        <!-- Camera off / Permission prompt placeholder -->
        <div v-if="!cameraActive" class="flex flex-col items-center justify-center px-4 py-8 text-center text-white/70">
          <Icon name="camera" :size="40" class="mb-2 text-white/40" />
          <p class="text-sm font-medium">{{ cameraError || 'Camera scanner standby' }}</p>
          <p class="mt-1 max-w-xs text-xs text-white/50">
            {{ cameraError ? 'You can type or use a hardware scanner below.' : 'Enable live camera to scan barcodes and QR codes directly.' }}
          </p>
          <button
            class="mt-3 flex items-center gap-1.5 rounded-lg bg-surface-blue-6 px-4 py-2 text-xs font-medium text-white shadow-md active:scale-95"
            @click="startCamera"
          >
            <Icon name="camera" :size="14" /> Start camera
          </button>
        </div>

        <!-- Scanning Viewfinder Reticle Overlay -->
        <div v-if="cameraActive" class="pointer-events-none absolute inset-0 flex items-center justify-center p-6">
          <div class="relative h-48 w-64 max-w-[80vw] rounded-xl border-2 border-dashed border-white/50 shadow-2xl">
            <!-- Corner Accents -->
            <span class="absolute -left-1 -top-1 h-5 w-5 border-l-4 border-t-4 border-surface-blue-5 rounded-tl" />
            <span class="absolute -right-1 -top-1 h-5 w-5 border-r-4 border-t-4 border-surface-blue-5 rounded-tr" />
            <span class="absolute -bottom-1 -left-1 h-5 w-5 border-b-4 border-l-4 border-surface-blue-5 rounded-bl" />
            <span class="absolute -bottom-1 -right-1 h-5 w-5 border-b-4 border-r-4 border-surface-blue-5 rounded-br" />

            <!-- Animated Laser Scan Line -->
            <div class="scan-laser absolute inset-x-2 h-0.5 bg-gradient-to-r from-transparent via-red-500 to-transparent shadow-[0_0_8px_rgba(239,68,68,0.8)]" />

            <div class="absolute inset-x-0 bottom-2 text-center text-[10px] font-medium tracking-wider uppercase text-white/80 drop-shadow">
              Align Barcode
            </div>
          </div>
        </div>

        <!-- Camera Toolbar Overlay -->
        <div v-if="cameraActive" class="absolute bottom-2 inset-x-0 flex justify-center gap-2">
          <button
            class="rounded-full bg-black/60 px-3 py-1 text-xs text-white backdrop-blur border border-white/20 active:bg-black/80"
            @click="stopCamera"
          >
            Pause Camera
          </button>
        </div>
      </div>

      <!-- Quick Manual / Hardware Scan Input -->
      <div class="border-b border-outline-gray-2 bg-surface-white p-3.5 shadow-sm">
        <div class="flex items-center gap-2">
          <div class="relative flex-1">
            <Icon name="barcode" :size="16" class="pointer-events-none absolute left-3 top-3 text-ink-gray-5" />
            <input
              ref="inputRef"
              v-model="inputCode"
              class="h-10 w-full rounded-lg border border-outline-gray-3 bg-surface-white pl-9 pr-8 font-mono text-base outline-none focus:border-outline-blue-4"
              placeholder="Type or hardware scan serial…"
              autocomplete="off"
              enterkeyhint="search"
              :disabled="loading"
              @keydown.enter.prevent="lookupCode(inputCode)"
            />
            <button
              v-if="inputCode"
              class="absolute right-2.5 top-2.5 text-ink-gray-4 hover:text-ink-gray-7"
              @click="inputCode = ''"
            >
              <Icon name="close" :size="15" />
            </button>
          </div>
          <button
            class="h-10 shrink-0 rounded-lg bg-surface-gray-9 px-4 text-sm font-medium text-white shadow-sm active:scale-95 disabled:opacity-50"
            :disabled="!inputCode.trim() || loading"
            @click="lookupCode(inputCode)"
          >
            {{ loading ? 'Finding…' : 'Find' }}
          </button>
        </div>
        <p class="mt-1.5 text-[11px] text-ink-gray-5">
          Hardware USB / Bluetooth barcode scanners will automatically submit.
        </p>
      </div>

      <!-- Result Card (Found Unit) -->
      <div v-if="unitResult" class="p-4 bg-surface-gray-1">
        <div class="overflow-hidden rounded-xl border border-outline-gray-3 bg-surface-white shadow-sm">
          <div class="flex items-center justify-between border-b border-outline-gray-1 bg-surface-gray-1 px-4 py-2.5">
            <span class="font-mono text-sm font-bold text-ink-gray-9">{{ unitResult.serial_no }}</span>
            <div class="flex items-center gap-1.5">
              <StatusBadge :value="unitResult.status" />
              <StatusBadge :value="unitResult.condition" kind="condition" />
            </div>
          </div>

          <div class="p-4">
            <h3 class="text-base font-semibold text-ink-gray-9">{{ unitResult.item_name }}</h3>
            <div class="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-gray-6">
              <div><span class="text-ink-gray-4">Location:</span> {{ unitResult.location || 'Warehouse' }}</div>
              <div v-if="unitResult.storage"><span class="text-ink-gray-4">Storage:</span> {{ unitResult.storage }}</div>
              <div v-if="unitResult.parent_box"><span class="text-ink-gray-4">In Box:</span> {{ unitResult.parent_box }}</div>
            </div>

            <!-- Quick Action Buttons -->
            <div class="mt-4 grid grid-cols-2 gap-2">
              <button
                class="flex items-center justify-center gap-1.5 rounded-lg border border-outline-blue-3 bg-surface-blue-2 py-2.5 text-xs font-semibold text-ink-blue-8 active:scale-95"
                @click="goToMovement('CHECK_OUT')"
              >
                <Icon name="out" :size="14" /> Check Out
              </button>
              <button
                class="flex items-center justify-center gap-1.5 rounded-lg border border-outline-green-3 bg-surface-green-2 py-2.5 text-xs font-semibold text-ink-green-8 active:scale-95"
                @click="goToMovement('CHECK_IN')"
              >
                <Icon name="in" :size="14" /> Check In
              </button>
              <button
                class="flex items-center justify-center gap-1.5 rounded-lg border border-outline-gray-2 bg-surface-white py-2 text-xs font-medium text-ink-gray-8 hover:bg-surface-gray-1 active:scale-95"
                @click="goToUnit"
              >
                <Icon name="layers" :size="13" /> View Details
              </button>
              <button
                class="flex items-center justify-center gap-1.5 rounded-lg border border-outline-gray-2 bg-surface-white py-2 text-xs font-medium text-ink-amber-8 hover:bg-surface-gray-1 active:scale-95"
                @click="reportProblem"
              >
                <Icon name="alert" :size="13" /> Report Problem
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Not Found Error Alert -->
      <div v-else-if="notFoundCode" class="p-4 bg-surface-gray-1">
        <div class="rounded-xl border border-outline-red-3 bg-surface-red-2 p-4 text-center">
          <Icon name="alert" :size="24" class="mx-auto mb-1.5 text-ink-red-6" />
          <div class="text-sm font-semibold text-ink-red-8">No unit found</div>
          <div class="mt-0.5 font-mono text-xs text-ink-red-6">"{{ notFoundCode }}"</div>
          <p class="mt-2 text-xs text-ink-red-7">Check the serial number or confirm the barcode was registered in the catalog.</p>
        </div>
      </div>

      <!-- Recent Scans History -->
      <div v-if="recentScans.length" class="mt-auto border-t border-outline-gray-2 bg-surface-white p-3.5">
        <div class="mb-2 flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-ink-gray-5">
          <span>Recent Scans</span>
          <button class="text-[11px] font-normal lowercase text-ink-blue-6" @click="recentScans = []">Clear</button>
        </div>
        <div class="flex flex-col gap-1.5">
          <button
            v-for="item in recentScans"
            :key="item.serial_no"
            class="flex items-center justify-between rounded-lg border border-outline-gray-2 bg-surface-gray-1 px-3 py-2 text-left text-xs hover:border-outline-gray-4"
            @click="selectRecent(item)"
          >
            <div class="min-w-0 flex-1">
              <span class="font-mono font-medium text-ink-gray-9">{{ item.serial_no }}</span>
              <span class="ml-2 truncate text-ink-gray-6">{{ item.item_name }}</span>
            </div>
            <StatusBadge :value="item.status" size="sm" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'frappe-ui'
import Icon from './Icon.vue'
import StatusBadge from './StatusBadge.vue'
import { api, readError } from '../api'
import {
  createBarcodeDetector,
  hasBarcodeDetector,
  playScanErrorBeep,
  playScanSuccessBeep,
  triggerHaptic,
} from '../scannerUtils'

const props = defineProps({
  modelValue: Boolean,
})
const emit = defineEmits(['update:modelValue', 'scanned'])

const router = useRouter()
const videoRef = ref(null)
const inputRef = ref(null)
const inputCode = ref('')
const loading = ref(false)
const unitResult = ref(null)
const notFoundCode = ref('')
const recentScans = ref([])

const cameraActive = ref(false)
const cameraError = ref('')
const hasTorch = ref(false)
const torchOn = ref(false)

let stream = null
let track = null
let detector = null
let detectTimer = null
let lastScannedRaw = ''
let lastScanTime = 0

watch(() => props.modelValue, (isOpen) => {
  if (isOpen) {
    unitResult.value = null
    notFoundCode.value = ''
    inputCode.value = ''
    nextTick(() => {
      inputRef.value?.focus()
      startCamera()
    })
  } else {
    stopCamera()
  }
})

async function startCamera() {
  if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
    cameraError.value = 'Camera not supported in this browser'
    return
  }
  cameraError.value = ''
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: { ideal: 'environment' },
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
      audio: false,
    })
    if (videoRef.value) {
      videoRef.value.srcObject = stream
      await videoRef.value.play().catch(() => {})
    }
    cameraActive.value = true

    track = stream.getVideoTracks()[0]
    if (track && track.getCapabilities) {
      const capabilities = track.getCapabilities()
      hasTorch.value = Boolean(capabilities.torch)
    }

    if (hasBarcodeDetector()) {
      detector = await createBarcodeDetector()
      startDetectionLoop()
    }
  } catch (err) {
    console.warn('Camera stream error:', err)
    cameraError.value = 'Camera permission denied or camera in use'
    cameraActive.value = false
  }
}

function stopCamera() {
  cameraActive.value = false
  torchOn.value = false
  if (detectTimer) {
    clearInterval(detectTimer)
    detectTimer = null
  }
  if (stream) {
    stream.getTracks().forEach((t) => t.stop())
    stream = null
    track = null
  }
  if (videoRef.value) {
    videoRef.value.srcObject = null
  }
}

async function toggleTorch() {
  if (!track || !hasTorch.value) return
  torchOn.value = !torchOn.value
  try {
    await track.applyConstraints({
      advanced: [{ torch: torchOn.value }],
    })
  } catch (err) {
    console.debug('Torch error:', err)
  }
}

function startDetectionLoop() {
  if (detectTimer) clearInterval(detectTimer)
  detectTimer = setInterval(async () => {
    if (!cameraActive.value || !detector || !videoRef.value || videoRef.value.readyState < 2) return

    try {
      const barcodes = await detector.detect(videoRef.value)
      if (barcodes && barcodes.length > 0) {
        const raw = barcodes[0].rawValue?.trim()
        const now = Date.now()
        if (raw && (raw !== lastScannedRaw || now - lastScanTime > 2000)) {
          lastScannedRaw = raw
          lastScanTime = now
          lookupCode(raw)
        }
      }
    } catch {
      // Detection frame error; ignore and retry next interval
    }
  }, 250)
}

async function lookupCode(raw) {
  const value = String(raw || '').trim()
  if (!value) return
  loading.value = true
  notFoundCode.value = ''
  unitResult.value = null

  try {
    const unit = await api.findUnit(value)
    if (unit) {
      playScanSuccessBeep()
      triggerHaptic('success')
      unitResult.value = unit
      inputCode.value = ''
      emit('scanned', unit)

      // Add to recent scans if not already at the top
      if (!recentScans.value.some((item) => item.serial_no === unit.serial_no)) {
        recentScans.value.unshift(unit)
        if (recentScans.value.length > 6) recentScans.value.pop()
      }
    } else {
      playScanErrorBeep()
      triggerHaptic('error')
      notFoundCode.value = value
    }
  } catch (err) {
    playScanErrorBeep()
    triggerHaptic('error')
    toast.error(readError(err))
  } finally {
    loading.value = false
  }
}

function selectRecent(item) {
  unitResult.value = item
  notFoundCode.value = ''
}

function goToMovement(type) {
  if (!unitResult.value) return
  const serial = unitResult.value.serial_no
  close()
  router.push({ name: 'movement-new', query: { type, unit: serial } })
}

function goToUnit() {
  if (!unitResult.value) return
  const name = unitResult.value.name
  close()
  router.push({ name: 'unit', params: { name } })
}

function reportProblem() {
  if (!unitResult.value) return
  const serial = unitResult.value.serial_no
  close()
  router.push({ name: 'maintenance', query: { flag: '1', unit: serial } })
}

function close() {
  stopCamera()
  emit('update:modelValue', false)
}

onBeforeUnmount(() => {
  stopCamera()
})
</script>

<style scoped>
@keyframes scanLaser {
  0% {
    top: 10%;
  }
  50% {
    top: 85%;
  }
  100% {
    top: 10%;
  }
}

.scan-laser {
  animation: scanLaser 2s ease-in-out infinite;
}
</style>
