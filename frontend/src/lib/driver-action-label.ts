export function driverSyncActionLabel(action: any, lang: string): string {
  const localized = action?.labelByLocale?.[lang]
  if (typeof localized === 'string' && localized.trim()) return localized
  if (lang === 'de' && typeof action?.label_de === 'string' && action.label_de.trim()) return action.label_de
  return typeof action?.label === 'string' ? action.label : ''
}
