/**
 * Mobile scanner utilities: Web Audio beep, haptic vibration, and camera barcode detection.
 */

let audioCtx = null

function getAudioContext() {
  if (!audioCtx && typeof window !== 'undefined') {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext
    if (AudioContextClass) {
      audioCtx = new AudioContextClass()
    }
  }
  if (audioCtx && audioCtx.state === 'suspended') {
    audioCtx.resume().catch(() => {})
  }
  return audioCtx
}

/**
 * Play a high-pitched double chime for successful scan.
 */
export function playScanSuccessBeep() {
  try {
    const ctx = getAudioContext()
    if (!ctx) return

    const now = ctx.currentTime
    const osc1 = ctx.createOscillator()
    const osc2 = ctx.createOscillator()
    const gain = ctx.createGain()

    osc1.type = 'sine'
    osc1.frequency.setValueAtTime(880, now) // A5
    osc2.type = 'sine'
    osc2.frequency.setValueAtTime(1760, now + 0.07) // A6

    gain.gain.setValueAtTime(0.2, now)
    gain.gain.exponentialRampToValueAtTime(0.01, now + 0.18)

    osc1.connect(gain)
    osc2.connect(gain)
    gain.connect(ctx.destination)

    osc1.start(now)
    osc1.stop(now + 0.07)
    osc2.start(now + 0.07)
    osc2.stop(now + 0.18)
  } catch (err) {
    console.debug('Audio error', err)
  }
}

/**
 * Play a low buzz tone for scan failure/error.
 */
export function playScanErrorBeep() {
  try {
    const ctx = getAudioContext()
    if (!ctx) return

    const now = ctx.currentTime
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()

    osc.type = 'sawtooth'
    osc.frequency.setValueAtTime(180, now)
    gain.gain.setValueAtTime(0.25, now)
    gain.gain.exponentialRampToValueAtTime(0.01, now + 0.22)

    osc.connect(gain)
    gain.connect(ctx.destination)

    osc.start(now)
    osc.stop(now + 0.22)
  } catch (err) {
    console.debug('Audio error', err)
  }
}

/**
 * Trigger haptic vibration on mobile devices.
 */
export function triggerHaptic(type = 'success') {
  if (typeof navigator !== 'undefined' && navigator.vibrate) {
    try {
      if (type === 'success') {
        navigator.vibrate([40])
      } else if (type === 'error') {
        navigator.vibrate([60, 40, 60])
      } else {
        navigator.vibrate([25])
      }
    } catch {
      // Ignore vibration errors if blocked by browser
    }
  }
}

/**
 * Check if the browser supports BarcodeDetector natively.
 */
export function hasBarcodeDetector() {
  return typeof window !== 'undefined' && 'BarcodeDetector' in window
}

/**
 * Create a BarcodeDetector instance if supported.
 */
export async function createBarcodeDetector() {
  if (!hasBarcodeDetector()) return null
  try {
    const formats = await window.BarcodeDetector.getSupportedFormats()
    return new window.BarcodeDetector({ formats })
  } catch (err) {
    console.debug('BarcodeDetector init error:', err)
    return null
  }
}
