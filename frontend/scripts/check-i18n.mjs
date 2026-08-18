import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const root = new URL('../src/i18n/', import.meta.url)
const languages = ['de', 'ru', 'uk']
const untranslatedAllowlist = new Set([
  'app.name',
  'login.heading',
  'settings.langDe',
  'settings.langRu',
  'settings.langUk',
  'spools.id',
  'spools.rfidUid',
  'spools.slotGroupTrays',
  'printers.incoming',
  'printers.outgoing',
  'printers.backfillWillChangeModel',
  'printers.profilePickerModelResolved',
  'locations.identifier',
  'manufacturers.url',
  'admin.fieldType_url',
  'admin.apiInfoTitle',
  'admin.oidc',
  'admin.rfidProtocolOpenspool',
  'admin.rfidProtocolFilaman',
])
const englishUiWordAllowlist = new Set([
  'filaments.shopUrlPlaceholder',
  'spools.externalIdPlaceholder',
  'spools.dsSyntaxTokenDesc',
  'spools.dsSyntaxTokenEg',
  'spools.dsSyntaxDateEg',
  'spools.dsSyntaxWrapEg',
  'spools.dsSyntaxSwatchDesc',
  'spools.dsSyntaxSizeEg',
  'spools.dsSyntaxNestedEgPrefix',
  'printers.slotLabel',
])
const englishUiWords = /\b(?:the|click|add|create|select|manage|save|delete|no|back|system|settings|manufacturer|filament|spool|printer|location|color|search|all|found|failed|load|new|cancel|edit|roles|permissions|devices|application|database|backup|restore|users|installed|available|documentation|danger|zone|import|summary|target|preview|columns|remaining|driver|online|slots|check|killswitch)\b/i
const forbiddenTerminology = {
  ru: /(?<![А-Яа-яЁё])(?:нить|нити|нитей|нитью|волокно|волокна|волокну|спул|спула|спулу|спулы|спулов|золотник)(?![А-Яа-яЁё])/iu,
  uk: /(?<![А-Яа-яІіЇїЄєҐґ])(?:нитка|нитки|нитку|ниткою|ниток|спул|спула|спулу|спули|спулів|спулі|шпуля|шпулі|шпуль|золотник|розжарення)(?![А-Яа-яІіЇїЄєҐґ])/iu,
}

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

function visibleText(text) {
  return text
    .replace(/<code>[\s\S]*?<\/code>/gi, '')
    .replace(/https?:\/\/\S+/gi, '')
    .replace(/\{[^}]+\}/g, '')
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
    if ((language === 'ru' || language === 'uk') && target === source && !untranslatedAllowlist.has(key)) {
      console.error(`${language}: untranslated value for ${key}`)
      failed = true
    }
    if ((language === 'ru' || language === 'uk') && target !== undefined && target.trim() === '') {
      console.error(`${language}: empty value for ${key}`)
      failed = true
    }
    if ((language === 'ru' || language === 'uk') && target !== undefined && forbiddenTerminology[language].test(target)) {
      console.error(`${language}: inconsistent terminology for ${key}`)
      failed = true
    }
    if ((language === 'ru' || language === 'uk') && target !== undefined && englishUiWords.test(visibleText(target)) && !englishUiWordAllowlist.has(key)) {
      console.error(`${language}: probable English UI text for ${key}`)
      failed = true
    }
  }
}
if (failed) process.exitCode = 1
else console.log(`i18n parity passed for ${canonical.size} keys`)
