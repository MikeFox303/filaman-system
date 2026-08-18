import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const root = new URL('../src/i18n/', import.meta.url)
const languages = ['de', 'ru']

function flatten(value, prefix = '', entries = new Map()) {
  for (const [key, child] of Object.entries(value)) {
    const path = prefix ? `${prefix}.${key}` : key
    if (typeof child === 'string') entries.set(path, child)
    else if (child && typeof child === 'object' && !Array.isArray(child)) flatten(child, path, entries)
    else throw new Error(`${path} must be a string or object`)
  }
  return entries
}

function placeholders(text) {
  return [...text.matchAll(/\{([A-Za-z0-9_]+)\}/g)].map((match) => match[1]).sort()
}

async function dictionary(language) {
  const file = fileURLToPath(new URL(`${language}.json`, root))
  return flatten(JSON.parse(await readFile(file, 'utf8')))
}

const canonical = await dictionary('en')
let failed = false
for (const language of languages) {
  const translated = await dictionary(language)
  for (const key of canonical.keys()) if (!translated.has(key)) { console.error(`${language}: missing key ${key}`); failed = true }
  for (const key of translated.keys()) if (!canonical.has(key)) { console.error(`${language}: extra key ${key}`); failed = true }
  for (const [key, source] of canonical) {
    const target = translated.get(key)
    if (target !== undefined && JSON.stringify(placeholders(source)) !== JSON.stringify(placeholders(target))) {
      console.error(`${language}: placeholder mismatch for ${key}`)
      failed = true
    }
  }
}
if (failed) process.exitCode = 1
else console.log(`i18n parity passed for ${canonical.size} keys`)
