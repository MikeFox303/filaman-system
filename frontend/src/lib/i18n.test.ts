// @vitest-environment happy-dom

import { afterEach, describe, expect, it } from 'vitest'

import { getLang, setLang, t } from './i18n'

afterEach(() => {
  setLang('en')
})

describe('i18n language selection', () => {
  it('selects Russian and exposes Russian interface text', () => {
    setLang('ru')

    expect(getLang()).toBe('ru')
    expect(document.documentElement.lang).toBe('ru')
    expect(t('settings.langRu')).toBe('Русский')
    expect(t('nav.dashboard')).toBe('Обзор')
    expect(t('dashboard.totalSpools')).toBe('Всего катушек')
    expect(t('dashboard.lowStockSpools')).toBe('Катушки с низким остатком')
    expect(t('dashboard.noData')).toBe('Нет данных')
  })
})
