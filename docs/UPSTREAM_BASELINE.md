# Upstream baseline

- Upstream repository: `https://github.com/Fire-Devils/filaman-system`
- Commit: `ebc0bcc83e34665bc699a0a259489f7d21d03a80`
- Version: `1.2.42`
- Captured: `2026-08-18`
- Integration branch: `main`

The scheduled `Sync upstream` workflow merges `upstream/main` into `sync/upstream` and opens a pull request against `main`. It never publishes a conflicted or untranslated update automatically.

Run `npm run check:i18n` after every upstream update; newly added English keys must be translated explicitly into Russian and Ukrainian before the pull request is merged.
