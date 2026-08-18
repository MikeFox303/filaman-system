import { readdirSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

function findTestFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const path = join(directory, entry.name)
    if (entry.isDirectory()) return findTestFiles(path)
    return entry.name.endsWith('.test.ts') ? [path] : []
  })
}

describe('test file placement', () => {
  it('keeps Vitest files out of Astro route directories', () => {
    expect(findTestFiles(resolve(process.cwd(), 'src/pages'))).toEqual([])
  })
})
