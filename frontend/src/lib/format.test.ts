// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { formatPrice } from './format'

beforeEach(() => {
  const values = new Map<string, string>()
  vi.stubGlobal('localStorage', {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    clear: () => values.clear(),
  })
})

afterEach(() => vi.unstubAllGlobals())

describe('formatPrice', () => {
  it('formats UAH with the Ukrainian locale and hryvnia sign', () => {
    localStorage.setItem('lang', 'uk')

    const formatted = formatPrice(1234.5, 'UAH')

    expect(formatted).toContain('₴')
    expect(formatted).toContain('1 234,50')
  })
})
