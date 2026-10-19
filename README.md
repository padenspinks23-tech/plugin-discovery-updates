# Plugin Discovery — public update runner (pre-release)

A proposed GitHub-hosted, read-only update runner for a searchable catalog of
**publicly listed** ChatGPT apps/plugins. This repository contains no private
account snapshots, source credentials, imported catalog, or proprietary project
history. It is separate from the private development repository.

## Current status

**Scaffolding only. Not acquiring, publishing, or deploying data.** The
directory source and reuse rights are not approved, and a prior GitHub runner
received an HTTP 403 when attempting to collect from OpenAI. Creating a new
GitHub account will not fix that upstream response.

- Test workflow: Python standard-library unit checks; no credentials.
- Daily workflow: scheduled for 12:17 UTC, **job disabled by default** using a
  repository variable. Its only implemented action is checking release gates.
- No network collector, Cloudflare credentials, or database writer is included.
- A previously created private Codex app/list snapshot must **never** be
  copied, committed or served through this repository.

## Enabling collection and publication

See [release gates](docs/RELEASE_GATES.md). An owner must first establish
authorized public-only source acquisition and valid metadata reuse permission,
then implement and verify end-to-end collecting, staged import, quality checks,
rollback and live MCP search. **Do not set PUBLIC_CATALOG_UPDATES_ENABLED=true**
until all acceptance steps pass; the current guarded job will fail closed.

## Local checks

    python3 -m unittest discover -s tests -v
    python3 scripts/check_release.py --config config/release.json

The second command intentionally fails until an approved release configuration
exists. No external accounts, data, or network requests are needed for tests.
