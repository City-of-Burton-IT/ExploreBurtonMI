# ExploreBurtonMI Comprehensive Security Audit

**Date:** 2026-07-17

**Repository:** `City-of-Burton-IT/ExploreBurtonMI`

**Reviewed revision:** `f032bbbcf1449fbf1225f231c5e9463e18520251` (`main`)

**Disposition:** Audit and remediation plan only; no application or repository settings changed

## Executive decision

No confirmed Critical or High-severity vulnerability was found in the reviewed code or published data. The application has a sound static-site security posture: no server-side application runtime, no resident authentication, HTTPS-enforced Pages hosting, an enforced meta CSP, output escaping around map data, local-only reverse geocoding, dependency scanning with no known vulnerable packages, and clean secret-scanning results after false-positive validation.

Refactoring should not begin until the four Medium findings below are either remediated or explicitly accepted by the project owner. They concern change control and accidental publication, not a demonstrated compromise:

1. `main` has no branch protection or repository ruleset.
2. Add-new listing candidates enter the public repository before the stated manual-vetting step.
3. GitHub Actions dependencies use mutable version tags rather than immutable commit SHAs.
4. The local pin editor can include unrelated, previously staged files in its publish commit.

## Scope and method

The review covered all 275 tracked files at the reviewed revision, including:

- Svelte/TypeScript application code, HTML templates, PWA configuration, public configuration, and generated resident data.
- Leaflet map rendering, popups, deep links, saved places, location handling, reports, suggestions, status tracking, push messages, and the Resident Guide HTML path.
- Python pipeline, data fetchers/builders, listing-request synchronization, and the local Flask pin editor.
- Android and iOS wrappers, Android widget network access, app links, backup settings, and file-provider configuration.
- All seven GitHub Actions workflows and live repository security/settings APIs.
- Current live response headers at `https://explore.burtonmi.gov`.
- Full Git history secret scan, package vulnerability scans, static analysis, targeted Python security analysis, and the complete test/build baseline.

The audit used adversarial validation: every scanner result was traced to its call site and trust boundary before it was retained. Clean-looking areas were challenged with alternate hypotheses, including stored/reflected XSS, unsafe URL schemes, directory traversal, SSRF, XML/ZIP bombs, shell injection, CSRF, leaked secrets, weak tokens, unreviewed PII publication, malicious workflow payloads, and native deep-link abuse.

## Trust boundaries

| Boundary | Trusted side | Untrusted or less-trusted side | Principal control |
|---|---|---|---|
| Public SPA | Versioned build and committed JSON | Resident browser, URL/hash, search/filter input | Svelte escaping, explicit HTML escaping, URL allowlists, CSP |
| Public forms | Resident-entered report/listing data | Power Automate/SharePoint intake | Client bounds/length checks; server controls require external verification |
| Data pipeline | City-curated/open/consented inputs | Third-party APIs and operator-supplied exports | Timeouts, schema validation, output allowlists, manual review |
| GitHub automation | Reviewed workflow and protected credentials | Dispatch payloads and upstream Actions | Payload serialization, least-privilege token settings, WIF; branch protection missing |
| Pin editor | Local IT operator on `127.0.0.1` | Imported workbook and working-tree state | CSRF token, localhost binding, subprocess argument arrays |
| Native app | Capacitor app and verified site host | Push/deep-link payloads and network | HTTPS, host equality check, topic allowlist, platform trust store |

## Findings summary

| ID | Severity | Finding | Disposition |
|---|---:|---|---|
| SEC-01 | Medium | `main` has no protection/ruleset despite direct deployment from `main` | Remediate before refactor |
| SEC-02 | Medium | Unvetted add-new listing candidates are committed to the public repository | Remediate before refactor |
| SEC-03 | Medium | GitHub Actions use mutable major-version tags | Remediate before refactor |
| SEC-04 | Medium | Pin-editor publish can commit unrelated pre-staged files | Remediate before refactor |
| SEC-05 | Low | Two build workflows omit explicit token permissions | Remediate with SEC-03 |
| SEC-06 | Low | Cloudflare CSP header remains report-only | Complete rollout after report review |
| SEC-07 | Low | Local workbook imports have no explicit size/decompression ceiling | Harden in maintenance phase |
| SEC-08 | Low | Android app backup is enabled although saved places are resident preference data | Decide and document; default to disabling |
| PRIV-01 | Decision | Citywide address list is intentionally public but lacks a current, explicit data-governance decision | Resolve before broad launch |

## Detailed findings

### SEC-01 — Unprotected production branch

**Evidence:** The GitHub API returned `404 Branch not protected` for `main`, and the repository rulesets API returned an empty list. GitHub Pages deploys through a workflow sourced from `main`. `.github/workflows/apply-listing.yml` also has `contents: write` and commits/pushes approved changes directly to `main`.

**Impact:** A mistaken direct push, compromised maintainer session, or compromised write-capable workflow can change the public civic site without required review or passing checks. Secret scanning push protection reduces one failure mode but does not enforce code review or CI.

**Remediation plan:**

1. Add a repository ruleset for `main` requiring pull requests, at least one approval, and the frontend/Python CI checks.
2. Block force pushes and deletion; require conversation resolution.
3. Give automation the narrowest bypass possible. Prefer having `apply-listing.yml` open a PR instead of pushing directly.
4. Retain the existing read-only default workflow permission and `can_approve_pull_request_reviews: false`.
5. Test the listing automation against a temporary branch before enabling enforcement.

**Acceptance:** Direct maintainer pushes are rejected; a representative PR cannot merge with a failing required check; the listing path creates a reviewable change without a broad bypass.

### SEC-02 — Manual-vetting boundary occurs after public disclosure

**Evidence:** `tools/sync_listing_requests.py:125-194` converts an approved add-new request into `tools/pending-additions.json` for later manual vetting. `.github/workflows/apply-listing.yml:65-73` stages that candidate file and commits it to this public repository.

The transform does not copy the requester's contact fields, which is good. It can still publish a submitted business name, street address, telephone number, website, hours, and category before the repository-side vetting described by the tool.

**Impact:** An inappropriate, inaccurate, residential, or otherwise non-publishable candidate can become public in Git history even if it is never added to `facilities.geojson`. Deleting the current file would not remove the historical disclosure.

**Remediation plan:** Keep pending candidates in the approved SharePoint item, a private workflow artifact with short retention, or a private review repository. Only a vetted final listing should enter this public repository. Add a CI assertion that `tools/pending-additions.json` is never tracked or staged.

**Acceptance:** A test add-new request remains outside the public repository and Git history until an IT reviewer approves the final public fields.

### SEC-03 — Mutable GitHub Actions dependencies

**Evidence:** Workflows use references such as `actions/checkout@v5`, `android-actions/setup-android@v4`, and `google-github-actions/auth@v3`. GitHub CodeQL currently reports four open `actions/unpinned-tag` alerts (alerts 11–13 and 15), including both WIF authentication workflows.

**Impact:** If an upstream tag is moved or an upstream Action is compromised, a future run can execute different code with repository, artifact, Pages, or OIDC access.

**Remediation plan:** Pin every external `uses:` entry to a verified full commit SHA and retain a readable version comment. Enable Dependabot updates for `github-actions` so SHA updates arrive as reviewable PRs. Prioritize Actions in jobs with `contents: write`, `pages: write`, or `id-token: write`.

**Acceptance:** A repository-wide check finds no `uses: owner/action@vN` entries; CodeQL's four unpinned-tag alerts close after the next scan.

### SEC-04 — Pin-editor commit scope is wider than its staged scope

**Evidence:** `apps/pin-editor/store.py:202-208` runs `git add -- <four intended paths>` and then `git commit -m <message>`. A normal `git commit` includes every file already staged in the index, not only the paths staged by this function.

**Impact:** A local IT operator can unknowingly publish an unrelated staged secret, private export, or unfinished change when clicking Publish. Localhost binding and CSRF protection do not address working-tree/index state.

**Remediation plan:** Before publish, inspect `git diff --cached --name-only` and fail closed if any staged path is outside the allowlist. Commit with an explicit path-limited mechanism, then run a secret/PII preflight on the exact staged diff. Display the exact file list in the confirmation UI and add regression tests for an unrelated pre-staged file.

**Acceptance:** The publish endpoint refuses or excludes a staged canary file outside the four public-data paths, and the canary remains uncommitted.

### SEC-05 — Missing explicit permissions in two workflows

**Evidence:** `android-debug.yml` and `ios-build.yml` contain no `permissions` block. The live repository default is currently `read`, so this is not an active write-token exposure. CodeQL alerts 9 and 10 remain open because the least-privilege contract is implicit.

**Remediation plan:** Add `permissions: contents: read` to both workflows. Review each other workflow at job level while pinning Actions.

**Acceptance:** Every workflow declares permissions; CodeQL alerts 9 and 10 close.

### SEC-06 — Edge CSP rollout is incomplete

**Evidence:** Live responses include HSTS, `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`, and enforced `X-Frame-Options: SAMEORIGIN`. The Cloudflare header is still `Content-Security-Policy-Report-Only`. `index.html` has an enforced CSP meta policy, so scripts/resources are constrained, and X-Frame-Options currently blocks cross-origin framing.

**Impact:** This is policy drift rather than a demonstrated bypass. Header-only directives and future pages that omit the meta element would not receive a fully enforced CSP.

**Remediation plan:** Review report-only violations, reconcile the header with the built meta policy, then change the edge header to enforced CSP. Keep one canonical policy source and add a deployed-header smoke check.

**Acceptance:** The production response has an enforced `Content-Security-Policy` header with no required resource regressions; the report-only header is absent or intentionally retained as a separate stricter trial policy.

### SEC-07 — Local workbook ingestion lacks resource ceilings

**Evidence:** `tools/extract_waste_schedule.py:20-44` parses XML entries read from a ZIP/XLSX with the standard ElementTree parser. The pin editor's `/api/import` accepts a workbook without an explicit Flask `MAX_CONTENT_LENGTH`. Both paths are local IT tooling and the reviewed files are operator-selected; there is no public upload route.

**Impact:** A malicious or badly corrupted workbook could consume excessive memory/CPU and interrupt an operator session. The exposure is local and does not affect the public static site directly.

**Remediation plan:** Apply upload/file-size limits, inspect ZIP entry sizes/compression ratios before parsing, and use a hardened XML parser or a bounded XLSX reader. Return a generic user error while logging diagnostic detail locally.

**Acceptance:** Oversized and high-compression-ratio fixtures are rejected quickly and covered by tests.

### SEC-08 — Android backup includes local resident preferences

**Evidence:** `android/app/src/main/AndroidManifest.xml:4` sets `android:allowBackup="true"`. The app intentionally stores saved-place IDs, theme settings, and related local preferences. No account credentials or submitted report content were found in app-owned storage.

**Impact:** The current data is low sensitivity, but saved places can reveal resident interests and there is no product requirement for restoring them across devices.

**Remediation plan:** Default to `allowBackup="false"`, or add explicit modern and legacy backup rules that exclude saved-place and messaging/device-token preferences. Document the decision.

**Acceptance:** Backup behavior is explicit, tested on a release build, and CodeQL alert 3 is closed or dismissed with the documented rationale.

## Privacy decision

### PRIV-01 — Formalize the address-point publication basis

`public/address-points.json` contains 12,767 `[latitude, longitude, address]` tuples used only for on-device nearest-address lookup. The reviewed file contains no owner name, parcel ID, tax value, email, or other owner field, and `privacy.html` discloses that a bundled City address list is used locally. The current builder comments identify the operational source as a BS&A Assessing situs-address export, while older planning material referred to county/open address points.

Before broad public launch, record a data-owner decision covering source authority, license/permission, public-record basis, necessity, update cadence, retention, and whether exact point precision is required. If that basis is not approved, replace it with an explicitly open address-point source or coarsen/remove the feature. This is a governance decision, not evidence that owner PII is currently present.

## Scanner and control results

| Check | Result |
|---|---|
| `npm audit --json` | 0 known vulnerabilities across 920 packages |
| `pip-audit` for pipeline, tools, and pin editor | 0 known vulnerabilities in all three requirement sets |
| Gitleaks, full 254-commit history | 2 hits, both validated as the intentionally public Cloudflare Web Analytics beacon token |
| Semgrep `p/security-audit` + `p/secrets` | 6 alerts; 5 URL findings refuted by fixed/operator-controlled endpoints, 1 local workbook hardening issue retained as SEC-07 |
| Bandit, 57 production Python files / 7,474 LOC | 0 High; subprocess and assertion alerts manually refuted; workbook issue retained |
| GitHub secret scanning | Enabled; 0 open alerts |
| Secret scanning push protection | Enabled |
| Dependabot security updates | Enabled; 0 open Dependabot alerts |
| GitHub code scanning | 8 open alerts: 4 Action pinning, 2 workflow permissions, 1 Android backup, 1 Android certificate pinning |
| Pages | Public custom domain verified; HTTPS enforced |
| Workflow default token permission | Read-only; workflows cannot approve PR reviews |
| Public GeoJSON scan | 1,134 features; only expected public fields; no unsafe URL schemes or HTML-like values; 0 unknown categories |

## Refuted or accepted scanner leads

- **Dynamic `urlopen`/SSRF:** shared HTTP helpers are called with fixed data-source URLs; listing sync uses fixed Microsoft login and Graph URL prefixes. No resident input reaches the destination host.
- **Subprocess injection:** reviewed subprocess calls use argument arrays with `shell=False`; executables and operational arguments are fixed. The pin-editor commit message is one argument, not shell text.
- **Guide `{@html}` XSS:** HTML is generated at build time from tracked, trusted Markdown. Links are scheme-validated, and repository write access already permits arbitrary application code. The Resident Guide plan still adds a stricter content contract before authoring expands.
- **Map popup XSS:** dynamic map and overlay values are escaped before Leaflet HTML insertion. External links use explicit safe URL helpers.
- **Push/deep-link abuse:** only `explore.burtonmi.gov` is accepted for native routing; notification topics are allowlisted; JSON construction is safe. Dispatch authorization remains the trust boundary.
- **Android certificate pinning:** CodeQL alert 14 is not retained as a vulnerability. The widget fetches public, non-sensitive City status data over HTTPS; platform CA validation is appropriate, while pinning adds outage/rotation risk. Dismiss the alert with this rationale unless a future authenticated/sensitive API is introduced.
- **Soft-launch gate:** the bundled phrase/query mechanism is intentionally a visibility gate, not authentication or access control. It must never protect confidential content.
- **Public form endpoint URLs:** public write-only endpoints are expected to be discoverable. Their server-side method, size, content, throttling, and downstream escaping controls must be verified outside this repository.

## Required remediation sequence

1. **Contain public-change risk:** resolve SEC-02 and SEC-04; rotate the already-planned temporary PAT before broad launch.
2. **Enforce review:** implement SEC-01 and convert the listing workflow to a PR-based path.
3. **Harden automation:** resolve SEC-03 and SEC-05; clear or document all eight current CodeQL alerts.
4. **Close launch controls:** resolve PRIV-01, verify form/WAF controls, and finish the CSP rollout.
5. **Maintenance hardening:** resolve SEC-07 and SEC-08.
6. **Begin UI refactors:** execute the map, dashboard, and Resident Guide plans independently, with a green baseline between each area.

## External controls not provable from this repository

The following must be verified in their owning consoles before calling the full system audit closed:

- Cloudflare WAF/bot bypass for the native app, rate limits, CSP reports, and transform-rule scope.
- Power Automate/SharePoint method restrictions, input size/type limits, HTML encoding, retention, reviewer authorization, and abuse throttling.
- Azure/Graph app permissions, SAS scope/expiry, WIF subject/audience restrictions, and credential rotation evidence.
- GitHub organization MFA/2FA enforcement, team membership, environment reviewers, audit-log alerts, and recovery ownership.
- Google Play signing, release-track permissions, Firebase messaging IAM, and iOS signing/publication controls.

## Verified regression baseline

- `npm run check`: 0 errors, 0 warnings.
- `npm test`: 34 files, 279 tests passed.
- `npm run build`: production and PWA build passed; only existing ineffective-dynamic-import warnings were reported.
- `pytest pipeline/test tools -q`: 229 passed in a disposable environment built from checked-in requirements.
- `pytest apps/pin-editor/test -q`: 38 passed in a disposable environment built from checked-in requirements.

The documented `.venv` was not present in this checkout; disposable `uv` environments were used instead. No source file was changed by verification.

## Related refactor plans

- [Map refactor plan](./2026-07-17-map-refactor-plan.md)
- [Dashboard refactor plan](./2026-07-17-dashboard-refactor-plan.md)
- [Resident Guide refactor plan](./2026-07-17-resident-guide-refactor-plan.md)
