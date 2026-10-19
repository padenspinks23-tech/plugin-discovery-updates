# Mandatory release gates

1. Source must be explicitly authorized for automated access on hosted runners.
   GitHub-hosted attempts previously encountered OpenAI HTTP 403. Do not bypass
   blocks, use login cookies, or copy the owner's Codex authentication.
2. Source redistributability must be reviewed and documented. Public visibility
   is not, by itself, a blanket license to redistribute text or metadata.
3. Verify public listing scope for every record. An authenticated account-visible
   catalog is not evidence that entries are publicly listed.
4. Implement a bounded, rate-limited collector, input validation, daily coverage
   counts, provenance and stable canonical links, without extracting user data.
5. Reject malformed/truncated results. Preserve last-good on failure and enforce
   minimum coverage and maximum-drop constraints.
6. Implement staging plus checksum verification and rollback for Cloudflare D1.
7. Confirm real GitHub Actions hosted collection twice, first permitted
   publication, live ChatGPT MCP searches, source coverage, and free-tier quota.
8. Obtain explicit owner approval before enabling scheduled updates, public
   publication, paid infrastructure, auth scopes, or deployment.

This repository does not presently meet these gates. A status JSON field or
repository variable is never sufficient evidence of source rights.
