import { describe, expect, it } from 'vitest'
import { driverSyncActionLabel } from './driver-action-label'

describe('driverSyncActionLabel', () => {
  const action = {
    label: 'Sync Now',
    label_de: 'Jetzt synchronisieren',
    labelByLocale: { ru: 'Синхронизировать', uk: 'Синхронізувати' },
  }

  it('uses the requested localized plugin label', () => {
    expect(driverSyncActionLabel(action, 'ru')).toBe('Синхронизировать')
    expect(driverSyncActionLabel(action, 'uk')).toBe('Синхронізувати')
  })

  it('keeps the legacy German fallback', () => {
    expect(driverSyncActionLabel(action, 'de')).toBe('Jetzt synchronisieren')
  })

  it('falls back to the default label', () => {
    expect(driverSyncActionLabel(action, 'en')).toBe('Sync Now')
    expect(driverSyncActionLabel({ label: 'Full Resync' }, 'ru')).toBe('Full Resync')
  })
})
