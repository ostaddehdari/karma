# KARMA 1.6.0 — Security and stabilization

This release implements the first production-hardening phase:

- Central project RBAC with owner/admin/manager/member/viewer policies.
- Viewer accounts are read-only; inactive workspace members lose project access.
- Private authenticated download endpoints for chat, documents, letters and notes.
- Upload extension, size, count and magic-byte validation with UUID storage names.
- Production-safe defaults: DEBUG off, required secret key, secure cookies, HSTS and HTTPS redirect.
- Atomic timer start with row locking and a conditional database uniqueness constraint.
- Project detail GET no longer recalculates/writes progress.
- Database indexes and integrity constraints for common project, task, message, notification and time queries.
- Security/integration tests for RBAC, private files, invalid uploads and GET purity.
- Daily PostgreSQL/media backup and verified restore scripts with SHA-256 manifests.

## Upgrade

1. Back up the current database and media directory.
2. Install the updated requirements.
3. Run `python manage.py migrate --noinput`.
4. Run `python manage.py check --deploy` with production environment variables.
5. Replace the Nginx snippet; `/karma/media/` must return 404 because files are served through authorized Django endpoints.
6. Install and enable `scripts/karma-backup.timer` or run `deploy-ubuntu-24.04.sh`.

Demo data is disabled by default. Set `KARMA_SEED_DEMO=1` only in a demo environment.
