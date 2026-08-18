import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const readPage = (path: string) => readFileSync(resolve(process.cwd(), path), 'utf8')

describe('table layout contracts', () => {
  it('keeps spool-log headings in a dedicated scrollable table with column classes', () => {
    const page = readPage('src/pages/spool-log.astro')

    expect(page).toContain('<div class="fm-table-scroll">')
    expect(page).toContain('class="fm-table spool-log-table"')

    for (const column of [
      'spool-id',
      'mfr-color',
      'manufacturer',
      'material',
      'event-type',
      'event-date',
      'event-weight',
      'event-note',
    ]) {
      expect(page).toContain(`col-${column}`)
    }
  })

  it('keeps the wide filaments table inside the dedicated scroll container', () => {
    const page = readPage('src/pages/filaments/index.astro')

    expect(page).toContain('<div class="fm-table-scroll">')
  })
})
