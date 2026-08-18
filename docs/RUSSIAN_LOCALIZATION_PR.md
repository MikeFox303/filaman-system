# Upstream pull request draft

## Title

`feat(i18n): add Russian localization`

## Description

Adds Russian (`ru`) as a supported FilaMan interface language. The change includes the Russian dictionary, UI selector entry, server-side language validation, and an automated parity check for dictionary keys and interpolation placeholders.

## Tests performed

- `npm run check:i18n`
- `npm test`
- `npm run check`
- `npm run build`
- Backend language validation tests

## Screens to attach

- Login page
- Dashboard
- Settings language selector
- Spools and Filaments lists
- Label Designer
- Mobile Settings view

This PR intentionally excludes Docker publishing, Umbrel packaging, credentials, and any user database.
