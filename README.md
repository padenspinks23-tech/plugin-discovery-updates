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

## Manual offline snapshot staging

The scaffold now includes an offline validator/stager; it still has no source
adapter, collector or publisher. Only supply a local export after independently
establishing permission to obtain and process it:

    python3 scripts/stage_snapshot.py --input /path/to/export.json --output /path/to/staging.json

The output directory must already exist. Exit 0 means structural validation and
atomic staging succeeded; exit 2 means rejection or an I/O failure. Diagnostics
never echo record contents. Nothing contacts a network or changes release gates.
Do not commit input exports or staged catalog artifacts.

The strict version-1 input contract is:

- `format`: exactly `public-chatgpt-directory-export`; `version`: integer `1`.
- `source_type`: exactly `official_public_chatgpt_directory`. Private account
  lists, Codex app/list, MCPTop and third-party scrapes are unsupported.
- `issued_at`: valid UTC timestamp in `YYYY-MM-DDTHH:MM:SSZ` form.
- `terms_ref` and `verification_proof_ref`: nonempty strings, at most 1,024
  characters each, referencing the terms/document review and external source,
  public-scope and reuse verification. They are **unverified references**, not
  evidence or permission. No approval flags are accepted.
- `records`: 0–10,000 objects, each with `id`, `name`, `verified_public` (literal
  `true`), `source_url`, and optionally `description`. IDs must match
  `[A-Za-z0-9_~]{6,120}` and be unique. The link must be exactly
  `https://chatgpt.com/plugins/{id}`, with no query, fragment, credentials or suffix.
  Names are bounded to 200 characters; descriptions to 4,000. Present descriptions
  cannot be empty. Unknown fields at either level are rejected, including auth
  and private metadata. Text rejects Unicode control/format/surrogate characters,
  normalizes to NFC and trims surrounding whitespace.

Input is UTF-8 JSON, at most 8 MiB. Duplicate JSON keys and nonstandard constants
are rejected. Any invalid record rejects the whole export before output changes.
No sample directory entries are shipped outside tests.

The staging format is `public-chatgpt-directory-staging`, version `1`, containing
`source` metadata, sanitized `entries` sorted by ID, `counts` (`entries` and
`with_description`), `publication_authorized: false`, and `sha256`. Source metadata
always includes `verification_status: "unverified_claims"`. Canonical bytes are
UTF-8 JSON with sorted keys, compact separators, literal Unicode and no trailing
newline. The digest is SHA-256 over those canonical bytes **with the top-level
`sha256` field omitted**; it is not a hash of the file containing its own digest.
The CLI prints only counts, that digest and the blocked publication indication.
The complete artifact is flushed and fsynced to a temporary file in the destination
directory before atomic replacement; failures before replacement preserve the
previous artifact. This is atomic replacement, not a power-loss durability promise.

A future official-source adapter must independently verify authorization,
redistribution rights, record public scope, and the actual official ID/link
contract before using this staging schema. The validator checks declarations and
URL shape only; it cannot authenticate an export or verify that a link exists.
Empty staging is permitted for inspection and is not acceptable coverage evidence
by itself. Coverage/drop checks, verified ingestion, rollback, hosted acceptance
and explicit owner approval remain mandatory under the release gates. No workflow
runs this staging command automatically.
