import { describe, expect, it } from 'vitest'
import {
  hasBarcodeDetector,
  playScanErrorBeep,
  playScanSuccessBeep,
  triggerHaptic,
} from './scannerUtils'

describe('scannerUtils', () => {
  it('should check BarcodeDetector availability without throwing', () => {
    const supported = hasBarcodeDetector()
    expect(typeof supported).toBe('boolean')
  })

  it('should run audio beeps safely in mock environment', () => {
    expect(() => playScanSuccessBeep()).not.toThrow()
    expect(() => playScanErrorBeep()).not.toThrow()
  })

  it('should trigger haptics safely without error', () => {
    expect(() => triggerHaptic('success')).not.toThrow()
    expect(() => triggerHaptic('error')).not.toThrow()
    expect(() => triggerHaptic('light')).not.toThrow()
  })
})
