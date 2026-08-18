# Upstream baseline

- Upstream repository: `https://github.com/Fire-Devils/filaman-system`
- Commit: `ebc0bcc83e34665bc699a0a259489f7d21d03a80`
- Version: `1.2.42`
- Captured: `2026-08-18`
- Working branch: `feat/russian-localization`

Update procedure: `git fetch upstream` followed by `git rebase upstream/main`.
Run `npm run check:i18n` after every upstream update; newly added English keys must be translated explicitly.
