# Upstream baseline

- Upstream repository: `https://github.com/Fire-Devils/filaman-system`
- Commit: `5fef37dabb9b167453ae09d27f242b519c6b0133`
- Version: `1.2.47`
- Captured: `2026-08-29`
- Integration branch: `main`

`Fire-Devils/filaman-system` is the maintained technical core. Downstream changes should stay thin and focused on Russian/Ukrainian localization, the i18n parity guard, managed Bambuddy integration, X2D-specific compatibility that is not already upstream, and Umbrel/release packaging.

Do not maintain a parallel implementation of upstream core behavior when upstream already provides the fix. In particular, primary-worker proxy and printer-driver lifecycle routing are owned by upstream from this baseline onward.

The scheduled `Sync upstream` workflow must stage upstream changes for review and must never publish a conflicted or untranslated update automatically.

Run `npm run check:i18n` after every upstream update; newly added English keys must be translated explicitly into Russian and Ukrainian before the update is merged.
