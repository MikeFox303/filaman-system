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
  })
})
