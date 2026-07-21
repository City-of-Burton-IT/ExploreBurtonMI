# Project State

> Read this first at session start. Update at session end.

## Current Handoff

**Status:** Comparison approved and pushed on `feature/dashboard-clarity-comparison`. The branch
contains the dashboard clarity and property-tax changes on top of `origin/main`: all
dashboards are easier to scan, explain scope/status/data dates in plain language, link
official sources, and give Property Taxes a detailed City millage estimator. Nothing
from this comparison branch has been merged or published, and no pull request has been opened yet.

**Last touched:** 2026-07-21. The user approved the completed comparison and requested
that the branch be pushed. Property Taxes now displays the
City rate provisionally as 13.4 mills, backed by the last supported exact 13.44 rate,
until the current L-4029 is available. At the user's direction, the estimator now
shows the Approved Budget's General 4.0000, aggregate Police 8.3159, and Fire 0.9789
service rows. Because those total 13.2948, a separate 0.1452-mill `Unassigned
difference` row reconciles the table to 13.44 without inventing a service allocation.
Final Android-width review is complete in light and dark modes: the page and header
have no horizontal overflow, every exact mill value stays on one line, and the revised
table stays inside its card. Captures and measurements are in
`planning/comparison/dashboard-clarity-review.md`. Fresh gates passed: Svelte/TypeScript
0 errors and 0 warnings; 509 Vitest, 251 pipeline/tools, 44 pin-editor, and 12
repository-security tests; production/PWA build; and `py_compile` for the changed
property-tax generator. The build retains only the three known ineffective
dynamic-import warnings.

**Current phase:** **Dashboard clarity comparison -- APPROVED; AWAITING PROTECTED PR.**
The unchanged baseline runs at port 4173 and the verified comparison runs at port 43820.

**Open work:** Open a ready protected pull request from the approved comparison branch
and wait for the required remote checks. Obtain the current L-4029 and replace the
provisional City rate with its certified levy details when available.
Issue #101 is closed by the semantic-token dashboard-summary fix now on `origin/main`. Keep
[issue #94](https://github.com/City-of-Burton-IT/ExploreBurtonMI/issues/94) open and
explicitly deferred; do not alter branch protections.

**Blockers:** None for opening the protected pull request. The current L-4029 remains a
source follow-up, so the City rate is explicitly provisional. The local `gh`
credential is expired, but the authenticated GitHub connector confirmed issue #101
closed and issue #94 still open.

**Property-tax source decision:** Pending the current L-4029, the public-facing City
rate is provisional: use the last supported exact 13.44-mill rate for calculations and
display it as 13.4 mills. Do not describe 13.2948 as rounding to 13.4. The FY2026-27
Approved Budget lists General Operating 4.0000 mills, aggregate Police Levies 8.3159,
and Fire 0.9789, totaling 13.2948. The estimator shows those as clearly labeled budget
references plus a 0.1452-mill unassigned reconciliation row; it must not imply that the
difference belongs to General, Police, or Fire. The historical chart retains the
audited-financial-statement series, including 13.44 for FY2022-FY2026. When the current
L-4029 arrives, replace the provisional rate and reconciliation row with only the levy
detail that the official form supports. Do not split the aggregate Police line into
individual ballot levies without another official source.

**Public summary:** Explore Burton's clearer public civic dashboards and resident-focused
property-tax estimator were approved in comparison and pushed to a feature branch;
publication remains pending the protected pull-request workflow.

## Historical Session Log

**Historical public summary:** A public, static "Explore Burton" site (Vite + Svelte + Leaflet)
at explore.burtonmi.gov: a searchable map of city businesses, government facilities,
and services on a State of Michigan aerial basemap, 21 registered in-app data dashboards grouped
into themed categories (People & Housing, Money & Taxes, Health & Environment,
Public Safety, Infrastructure) -- including an adopted capital-plan dashboard whose funded
road projects also highlight on the map -- each with a plain-language "What this means for you"
callout -- and an interactive Resident Guide with typed callouts, section icons, a photo
lightbox, and a privacy-first click-to-load video tour. Dashboards include multi-year
trend lines (some comparing Burton with the state), a Genesee County cities comparison,
and downloadable data tables. Installable as a PWA with offline support and a "Near me"
locator; privacy-first cookieless analytics. A native Android app (Capacitor) is in
Google Play internal testing with automated, keyless releases. The public site is behind
a lightweight "coming soon" soft-launch gate (the native app is exempt). Backed by a
Python data pipeline. Residents can suggest listing edits and report issues (pothole/
blight) through M365-moderated in-app forms, see road-closure alerts, and (in the app)
opt in to push notifications and a home-screen widget; a Settings panel controls
appearance and notifications.
**Historical phase:** LAUNCHED (soft-launch gate on the public web) + **INTERNAL PREVIEW LIVE** (staff-only
mirror + docs + announcement, admin-greenlit 2026-07-16) -- map + dashboards +
Resident Guide live; installable PWA + analytics shipped; **Android app live on Play
internal testing** (keyless CI release). iOS wrapper compiles in CI, not published.
**Historical entry:** 2026-07-17 -- **SECURITY REMEDIATION IMPLEMENTED AND VERIFIED ON `security/remediate-audit-2026-07-17`.** Repository changes close SEC-02 through SEC-05 and SEC-07/08: add-new dispatches no longer write public candidates; listing automation pushes a review branch and uses an optional scoped `LISTING_PR_TOKEN`; Actions are SHA-pinned, least-privilege, non-persistent, concurrency-limited, and Dependabot-managed; pin-editor commits only allowlisted paths after gitleaks/PII preflight; XLSX/ZIP ceilings and generic errors are enforced; Android backup is disabled. PRIV-01 is accepted in ADR-0002 with a tested three-value public schema and explicit privacy provenance. Live GitHub: CodeQL certificate-pinning alert 14 dismissed with rationale; `main` now requires PRs, strict `web`/`python`/`pin-editor` checks bound to GitHub Actions app 15368, admin enforcement, conversation resolution, linear history, and no force-push/delete. Approval count is temporarily zero because GitHub reports only one write-capable collaborator; add a second reviewer before requiring one approval. **External remaining:** sign in to Cloudflare and promote the edge CSP from Report-Only to enforced after report review; update the Power Automate listing flow so add-new rows stay Approved/private; configure an expiring fine-grained `LISTING_PR_TOKEN` or manually open the compare-link PR. Verification: zizmor pedantic clean; Svelte check 0/0; 279 Vitest, 243 pipeline/tools pytest, and 44 pin-editor pytest passed; production/PWA build passed; modified Python compiled; the real 435-row Waste Schedule workbook parsed below both resource ceilings. Plans remain in `planning/specs/2026-07-17-*.md`. **Prior milestone:** 2026-07-16 -- **INTERNAL PREVIEW ROLLOUT BUILT** (admin greenlight; dept heads +
content operators, NOT council). Spec `planning/specs/2026-07-16-internal-preview-rollout.md`. Built:
(1) internal mirror scripts at `planning/internal-mirror/` (gitignored) -- Provision (DNS CNAME via DC +
enterprise-CA cert enrolled locally, PFX pushed to appservices; -SelfSigned fallback) | Setup (IIS
HTTPS site `explore.burton.local` + port-80 redirect site) piped, run from workstation, single-hop
remoting only; Deploy (VITE_INTERNAL_PREVIEW=1 build -> strip CF beacon + inject INTERNAL PREVIEW
ribbon -> web.config MIME maps -> robocopy -> curl verify). SOURCE CHANGE on main (uncommitted):
comingSoon.ts COMING_SOON_ENABLED now reads VITE_INTERNAL_PREVIEW (public build unaffected; probe
verified: gate tests fail with env set, full suite 279 green without). (2) Docs regenerated via
pandoc+ref-burton: FEATURES-OVERVIEW.md refreshed (July, + plain-language "Where the data comes from"
section) -> Features Overview.docx; NEW EXPLORE-GUIDE.md -> Quick Tour.docx (screenshot placeholders,
capture after mirror live); NEW OPERATOR-GUIDE.md -> Content Operator Guide.docx. (3) Email draft
`planning/ANNOUNCEMENT-EMAIL.md` (one email both audiences; FILL: feedback deadline). **MIRROR DEPLOYED + LIVE same session** (comingSoon.ts committed 92bca64 local/unpushed; cert = enterprise
CA BurtonWebServer template -- user granted APPSERVICES$ Enroll, enrolled via one-shot SYSTEM scheduled
task on appservices [Get-Certificate in a remoted user session dies on the AD template-lookup double-hop,
0x800704dc]; thumbprint 2450AAD7...4047, expires 2028-07-15; DEPLOY OK, 200 + ribbon verified). Real
screenshots captured from the live mirror (Playwright scratch venv + channel=msedge headless,
ignore_https_errors; planning/images/01-04) and embedded in Quick Tour docx (8.5 MB). **PENDING USER:
push main (92bca64); fill feedback deadline in ANNOUNCEMENT-EMAIL.md; send email w/ 3 docx.** Forms on
mirror are LIVE (TEST-prefix etiquette in docs).
**Prior:** 2026-07-06 (cont. 3) -- **#84 CLOSED: tools/lib migration COMPLETE.** The final 9 scripts
(extract_crashes/paser/school_districts/transit/waste_schedule/overture + apply_dupe_overrides/find_dupes/
sync_listing_requests) migrated in 3 verified batches on `refactor/tools-lib-finish`, FF-merged to main
(33058b7/eb8c5e0/6aa3994), branch deleted. Verification: regenerated outputs byte-identical to committed
(one known stale nit NOT committed: committed info-roads.json has "compares," where the unchanged script
emits "compares:", same family as the info-zoning nit); dupe tools verified by identical pre/post report
output; sync via pytest + a no-op --payload-file run. sync_listing_requests' Graph client deliberately
stays on urllib (form-encoded token grant; authorized PATCH where blind retry is unwanted). Gates green
per commit (svelte-check 0/0, vitest 279, build clean, pytest 229). **Dependabot alerts 17-20 all
state=fixed after the rescan; 0 open alerts.**
**Same session, deferred plan items decided + done (merged to main 66f07d1 + bf3931d, pushed):**
4.1 boot payload -- finding was STALE: address-points.json is already lazy (fetched only on
Report-an-issue pin-drop; SW precache excludes .json), no change; data.geojson field-stripping left
open. 3.5 -- pin-editor MOVED `tools/pin-editor/` -> `apps/pin-editor/` (git mv; ci.yml paths updated,
pytest --ignore dropped; 38 tests pass from the new home; pytest cmd is now
`pipeline/.venv/Scripts/python.exe -m pytest pipeline/test tools apps/pin-editor/test -q`). 4.5 CSP --
meta tag committed in index.html (browser-verified via vite preview: boot/map/#capital/#guide, ZERO
CSP violations; only the known localhost Cloudflare-RUM noise) + `docs/csp-cloudflare.md` (internal)
holds the matching Cloudflare Transform Rule policy w/ frame-ancestors + host inventory + SAS-URL
accepted-risk note. **Cloudflare half DEPLOYED same session:** explore CNAME flipped DNS-only -> Proxied (zone SSL=Full,
fine for Pages) + the Transform Rule live as Content-Security-Policy-Report-Only -- header verified
on the live site via curl AND a real-browser load (app renders, zero violations). **PENDING USER:
(1) after a clean Report-Only period rename the header to Content-Security-Policy; (2) add the WAF
skip rule for explore (Hostname eq explore.burtonmi.gov -> Skip Security Level / Browser Integrity
Check / Bot Fight Mode) -- proxying means bot challenges now apply, and the NATIVE app only fetch()es
JSON from this host and cannot solve a challenge; (3) device-check the Android app.** Native-app gotcha encoded in both: 'self' in the WebView is
`https://localhost`, so explore.burtonmi.gov stays explicit in connect-src/img-src.
**Prior (cont. 2):** **REFACTOR BRANCH MERGED TO MAIN (fast-forward, 29 commits)
and `refactor/codebase-review` deleted (remote + local). Main now carries the whole refactor: shared
Modal/Icon/forms.css, Map + InfoView decomposition, dashboards.ts split, tools/lib (all 11 fetch_* +
all 7 build_* + capital_roads_link migrated; httpio post_json / get_bytes / custom headers;
shapecheck guard in build_address_points), new ci.yml PR gate, optimized images, SPEC.md deleted.
Dependabot handled: waitress 3.0.1 (critical/high) and pytest 9.0.3 merged via PRs #77/#75; flask
3.1.3 and requests 2.33.0 applied manually on main (PRs #74/#76 conflicted -- adjacent-line pins on
a stale base); pin-editor's 38 tests verified on the bumped set pre-merge; also floored
tools/requirements requests>=2.33. Post-merge the graph rescanned and 4 NEW alerts (17-20) appeared against
tools/requirements.txt, incl. phantom flask/pytest entries the file does not contain -- rescan was
in flight at session end, check they cleared. Remaining for #84 (fresh session): extract_crashes /
overture / paser / school_districts / transit / waste_schedule + apply_dupe_overrides, find_dupes,
sync_listing_requests -- same regenerate-and-diff verification, work on a NEW branch off main.
Master plan: docs/REFACTORING_PLAN.md (gitignored).**
**#71 DATA NOW BUILT (no longer user-gated):** pulled the situs addresses directly from BS&A Assessing via the
read-only `bsa_readonly` login (the user confirmed using the SQL account). Internal extract
`C:\utils\Extract-BurtonAddressPoints.ps1` (NOT in the public repo -- names BURBSA01\BSA; parse-checked) reads
`D001City Of Burton 2026`.`ParcelMaster` (`propstreetcombined`/`propcity`/`propstate`/`propzip`; situs, not
owner; whole roll is Burton so NO city filter -- propcity is just the POSTAL city) -> 16,524 rows ->
`pipeline/data/address-points-source.csv` (gitignored). `tools/build_address_points.py` deduped to 13,487
unique -> Census BATCH forward-geocode -> 12,767 points (94.7%; 719 misses are non-addresses/no-number
streets/TIGER gaps -> manual fallback; 1 clipped outside boundary) -> `public/address-points.json` (524 KB,
title-cased). **BROWSER E2E:** dropped a pin at 43.00369,-83.63308 -> Address auto-filled "2104 S Center Rd"
(confirmed the TRUE nearest, 143 m) + "Nearest address filled in" hint. **REFRESH:** re-run the C:\utils
extract against the current-year D001 DB, re-run the Python builder, commit the JSON.
**#71 reverse-geocode dropped pin -> nearest address (LOCAL, not committed; client done, data pending):**
Decision (user-chosen): a **city-owned committed address table + on-device nearest-neighbour**, NOT a
third-party geocoder -- so the resident's dropped-pin coords NEVER leave the device pre-submission.
Ruled out: Census geocoder (returns geographies not addresses), Genesee County GCRC (parcel/address
FeatureServers are token-protected, error 499 -- only their PASER/roads/townships folder is public),
Google (terms + billing), Nominatim/Esri (third-party call + leaks coords). Built: `src/lib/reverseGeocode.ts`
(pure `haversineMeters` + `nearestAddress` w/ 250 m reject cap + `parseAddressPoints` + cached `loadAddressPoints`;
12 vitest), wired into `ReportIssue.svelte` (on pin-drop: lazy-load table -> nearest -> fill Address, never
clobbers a typed address [tracked via `addressAutoFilled` + `oninput`], silent no-op offline/out-of-range;
"Looking up..."/"Nearest address filled in" hints). Config key `addressPoints.source` + EMPTY placeholder
`public/address-points.json` (inert until real data) + PWA cache regex extended + privacy.html note. Gates:
**vitest 198, svelte-check 0/0, build clean.** Data builder `tools/build_address_points.py` written (Assessing
export CSV -> Census BATCH forward-geocode [free/no-key/<=10k] -> clip to boundary [PIP self-tested] -> compact
`{updated, points:[[lat,lng,addr]]}`); py_compile clean, requests in pipeline/.venv. Column mapping CONFIRMED
against the real Assessing schema (see the cont.9 data block above). All changes LOCAL/uncommitted -- review +
commit on a branch (new files: src/lib/reverseGeocode.ts, test/reverseGeocode.test.ts, tools/build_address_points.py,
public/address-points.json; edits: ReportIssue.svelte, types.ts, config.json, vite.config.ts, privacy.html, .gitignore).
**Capital Projects dashboard (#31 CLOSED, PR #79 merged 2026-06-17):** new Money & Taxes
dashboard from a curated CSV (`pipeline/data/capital-projects.csv`) built by
`tools/build_capitalprojects.py` -> `public/info-capital.json` (InfoView `capital`, added to
`DASHBOARD_GROUPS`). Data transcribed from the adopted FY2026-27 budget book (OneDrive
`ExploreBurton App/1-FINAL BUDGET BOOK.pdf`, Major Streets fund 202 + Local Streets 203 dept-451
construction, reconciled to printed totals via pdfplumber x-position parsing) + the Capital Asset
Requests sheet. Shows by-category donut, how-it-is-funded bars, largest projects, project table,
**per-resident ($469)**, and a **multi-year road/street capital trend** (FY24-25 $3.3M ->
FY25-26 $2.5M -> FY26-27 $10.5M, documented constants `STREET_CAPITAL_HISTORY`). **Roads tie-in**
(`tools/capital_roads_link.py`, called from BOTH build_capitalprojects + extract_paser, idempotent):
an **Improvement column** on the Roads PASER table flags funded federal-aid roads + a #capital link,
and a **"Funded road projects" map overlay** (`public/capital-roads.geojson`, dataLayer in
config.json) highlights each project **clipped to its named section** (cross-street->cross-street,
or city boundary), dropping unresolvable/unsectioned projects rather than whole-roading them. 21+14
pytest, svelte-check 0, build clean. **Refresh recipe:** edit the CSV, run build_capitalprojects.py
(regenerates dashboard + roads flag + overlay together). **Capital follow-ups (minor, not blocking):**
water/sewer had no discrete capital this year; deeper multi-year history needs prior budget books;
per-project federal-aid split not itemized in the book (kept Act 51 + a note).
**Pin Editor + Excel I/O (NEW local tool, MERGED PRs #73 #78):** a
local single-user Flask + Leaflet map tool at `tools/pin-editor/` (URL `http://pins.local`,
local single-user Flask + Leaflet map tool at `tools/pin-editor/` (URL `http://pins.local`,
binds 127.0.0.1:80) to add/move/delete/field-edit every business pin, write the pipeline's
SOURCE files, regenerate `public/data.geojson`, show a git diff, and Publish (commit+push).
Edit routing by id prefix (pure, tested in `edits.py`): curated (`burton:`/new `manual:`) ->
`facilities.geojson`; discovered (`osm:`/`overture:`) -> `overrides.json` (coordinates/field/
`hidden`). `store.py` preserves each source file's newline style (facilities=LF, overrides=
CRLF) AND keeps facilities geometry INLINE so unchanged features don't churn the diff (a
no-op-feature rewrite went from 136 -> 12 diff lines after that fix). Flask `app.py`:
/api/data,save,regenerate,diff,publish,boundary + a CSRF token + global-fetch-wrapper guard;
waitress; Leaflet vendored (no CDN). 24 pytest green (`test_edits.py` 19 + `test_store.py` 5);
**E2E verified** via the test client (edit a discovered website override + move city-hall +
add a `manual:` cafe -> save -> source files carry all three -> regenerate 1144->1145 ->
data.geojson carries the add; reverted). Spec: `planning/specs/2026-06-16-pin-editor.md`;
README in the tool dir. **NOT committed yet** (new files on master -- review + commit on a
branch). **Pre-existing finding (NOT tool-caused):** a no-edit `python run.py` regenerate
already drifts the committed `public/data.geojson` by ONE swapped USPS Manor Dr record
(`osm:node/12078958475` vs `osm:way/1304318386` -- the proximity-dedup picks the other one);
the first real pin-editor publish would carry that drift, so commit a fresh regenerated
baseline (or look at the dedup determinism) before/with the first publish.
**Unified messaging push half (NEW, 2026-06-16):** the existing "send push" flow
(`49bcb0ab-62e9-4af7-9653-6e149d558fa2`) was rebuilt via the Flow API into the unified
**"Explore Burton -- city messages (banner + push)"** flow: two independent top-level
If-branches off the on-create trigger -- **`Banner_channel`** (If ShowBanner -> IT
approval -> BannerStatus=Approved/Rejected) and **`Push_channel`** (If SendPush -> freq
gate [emergency-exempt via `Level='emergency'`] -> Mayor -> IT -> repository_dispatch ->
PushStatus=Sent, reject branches set PushStatus=Rejected). Added 3 list columns: SendPush
(yes/no), PushTopic (choice alerts/service/meetings), PushStatus (choice). **VERIFIED E2E
LIVE:** banner row -> IT approve -> BannerStatus=Approved -> live banner endpoint returned
it (then cleared); emergency SendPush row -> Mayor+IT approve (user confirmed 2 real
approvals) -> Send_push 204 -> PushStatus=Sent -> **push received on the user's Pixel**.
Flow def clean (no designer Apply-to-each mangling). **Reuses the OLD GitHub PAT for now
(read in-memory from the live flow) -- user will fully rotate before go-live; Mayor
approval still routes to r.bertram.** New helpers in C:\utils: explore-burton-add-push-columns.js,
explore-burton-messages-flow.json (the unified template), explore-burton-build-messages-flow.js
(read-live-PAT + PATCH), explore-burton-inspect-flow.js, explore-burton-flow-runs.js,
explore-burton-run-detail.js, explore-burton-patch-row.js, explore-burton-delete-row.js.
Form authoring guide (`planning/specs/2026-06-16-messages-form-authoring-guide.md`) updated
with the SendPush/PushTopic fields + the new "what happens after submit" flow description.
**#72 REMAINING (user):** author the Forms-for-Lists form in the SP UI (banner+push fields,
spec in the guide); rotate the PAT + set the real Mayor email before go-live. Issue left OPEN.
**PRIOR -- 2026-06-15 (cont. 6) -- #69 STATUS TRACKING + UNIFIED CITY MESSAGING (banner half).**
**Unified messaging (NEW, brainstormed -> specced -> banner half BUILT + LIVE):** decided to unify the
alert banner + push behind one staff-authored message (design spec
`planning/specs/2026-06-15-unified-city-messaging-design.md`). Banner half shipped: renamed the
SharePoint list "Explore Burton Push Requests" -> "Explore Burton Messages" + added banner columns
(Level, ShowBanner, BannerStart/End, BannerStatus); created a read-only banner flow
`8628952c-2af6-4ece-ac2f-79b5b5f36633` (GET, returns approved banner messages, CORS *); `AlertBanner`
now reads LIVE from `config.alerts.url` (normalizing the flat shape into CityAlert via tested
`loadAlerts`/`normalizeAlert`), falling back to committed `alerts.json` offline. Browser E2E: an
approved row rendered as a live amber banner; test row cleaned up. Gates green (svelte-check 0/176,
vitest 184, build clean). Commit `61299e0` (local). **Front-end:** uses native SharePoint
**Forms-for-Lists** (confirmed available in our GCC tenant) -- the form is USER-authored in the SP UI
(no API); I supply the field spec. **REMAINING (push half + form):** add SendPush/PushTopic/PushStatus
columns; extend the existing push flow into the unified approval+fanout flow (banner=IT, push=Mayor->IT,
emergency-exempt) -- gated on the same pending push items (PAT rotation, real Mayor email); user authors
the Forms-for-Lists form. New helpers: explore-burton-extend-messages-list.js,
explore-burton-create-banner-flow.js, explore-burton-create-message-row.js (+ messages list added to
explore-burton-patch-fields.js). **Form authoring guide** written for the user:
`planning/specs/2026-06-16-messages-form-authoring-guide.md` (banner fields; user builds the
Forms-for-Lists form in the SP UI; banner approval is a manual BannerStatus=Approved edit until the
push-half flow lands). **Widget refresh button (#65, commit `bfcc055`):** root-caused "widget shows
yesterday's meeting" to updatePeriodMillis (30 min) being deferred during Doze -- added a header
refresh icon that broadcasts WIDGET_REFRESH -> immediate re-fetch (+ "Updating..." feedback). Java +
res compile clean via local Gradle (JDK 21 at `C:\Program Files\Java\jdk-21.0.11`; the Bash shell's
JAVA_HOME is unset/Java 8 -- set it explicitly). DEVICE-VERIFY after the next Android release.
**CONT (2026-06-16):** JDK fixed (`JAVA_HOME` -> jdk-21.0.11 in user settings.json env; Bash shell's
was empty -> Java 8). v1.15 (vc24) shipped to Play internal + installed on the Pixel (cleared a
**Private Space** leftover debug build, user 10, that blocked the Play install -- `pm uninstall --user
10`). **Widget refresh button CONFIRMED WORKING on-device** (the "unavailable" was a transient
first-fetch; tapping refresh re-fetches + populates -- working as designed). **Report form (#14)
bundle 1+2 DONE** (commit `5e46b1b`, LOCAL/unpushed): Streetlight -> "Trash pickup" (city doesn't do
streetlights, does do missed-trash), and a typed **Address** field as an alternative to a pin
(location = in-city pin OR address). Live infra updated + curl-verified all 5 cases: #14 flow
whitelist + location `or(pin,address)` logic + Address in Create_item; SharePoint Category choices +
new Address column. **Bug found+fixed live:** `float(null)` threw on address-only (no pin) -> guarded
Latitude/Longitude to write null; and the validate emptiness checks now `string()`-coerce so a numeric
lat/lng doesn't break `empty()`. Reverse-geocode (pin->nearest address) filed as **#71** (needs a
geocoder decision; Google works but its terms restrict non-Google-basemap use + needs billing/key;
Android's native Geocoder is free but native-only). New helpers: explore-burton-edit-report-flow.js,
explore-burton-update-report-list.js, explore-burton-create-message-row.js.
**MISMATCH RESOLVED:** `5e46b1b` pushed (Pages deploy synced the web form) + **v1.16 (vc25) shipped
to Play internal** (run 27629519294, success) so the native form matches the flow too. All session
commits pushed; tree clean. **Stakeholder doc:** `planning/FEATURES-OVERVIEW.md` (+ Burton-branded
`planning/Explore Burton - Features Overview.docx` via pandoc + `planning/ref-burton.docx` reusable
reference doc) -- high-level feature/issue overview for brainstorming. JDK fix: `JAVA_HOME` added to
`~/.claude/settings.json` env (applies next session).
**PRIOR same session -- #69 RESIDENT STATUS TRACKING (magic link) BUILT + LIVE END TO END.** Implemented the TDD plan: `track.ts` (newToken/stageFor/fetchStatus/trackUrl,
9 vitest), `StatusPage.svelte` + `#status` route (fixed `viewFromHash` to handle the `?token`
suffix), both intake forms now mint a 128-bit token, send `trackToken`, and show the canonical
tracking link + Copy on success. LIVE infra (Flow API + Graph): added `TrackToken` (indexed) +
`PublicNote` columns to both intake lists; edited BOTH live intake flows (#3, #14) to store the
token + email the tracking link when the contact field contains '@' (verified: rows carry the
token, intake unbroken, tracking emails received); created the read-status flow
`c14ab909-a175-44ac-a29b-276bbd77a3fd` (read-only, queries both lists by token, OData-quote-escaped,
sanitized response, CORS *) and wired its URL into `public/config.json`. Full browser E2E passed
("Approved & published" + PublicNote + updatedAt). Gates green (svelte-check 0/176, vitest 175,
build clean). **Task 9 (weekly abuse-digest) DEFERRED** -- per-lookup SP writes on a public endpoint
are a write-amplification anti-pattern, and a run-history digest needs a Flow Management connection
not provisionable non-interactively; abuse visibility is covered by the read flow's built-in run
history for now. **#69 left OPEN** pending the digest decision. **PENDING USER:** push `main`
(6 commits, local); decide on the digest; note the tracking emails send FROM r.bertram's mailbox
(office365 conn owner) -- swap to a shared/noreply mailbox for production; the PAT rotation +
apply flow (issue 66) from cont.5 are still pending (unrelated to #69). New helpers in C:\utils:
explore-burton-add-tracking-columns.js, explore-burton-add-tracking-to-intake.js,
explore-burton-create-readstatus-flow.js, explore-burton-show-tracking.js, explore-burton-patch-fields.js.
**Prior (cont. 5):** **PUSH NOTIFICATIONS WORK END TO END (proven on a real
device) + notification UX polish.** Shipped v1.9 (vc18) through **v1.14 (vc23)** to Play internal.
Tested the approval flow live and fixed 2 Power Automate bugs (basic-approval reads `['response']`
NOT `['outcome']`; the maker designer wrapped UpdateItem actions in empty Apply-to-each -> edit
API-built flows via the Flow API only, never the designer). Root-caused the dead push to the
**Capacitor plugin-proxy thenable trap** (awaiting the proxy hits its `.then` -> phantom native
call -> hangs forever, silently); fix = synchronous `loadMessaging()`, never await the proxy
(v1.13). Polish (v1.14): default notification channel, in-app foreground `PushBanner`,
tap-to-deep-link. Cracked it via **on-device adb + Chrome DevTools Protocol** after ~5 blind
release cycles; local Gradle builds now work on this box. Vault note
[[Explore Burton - Submission & Push Pipelines]] updated (architecture + gotchas + debug recipe).
**Pending user:** uninstall the local debug build + reinstall v1.14 from Play; **rotate the GitHub
PAT** (it appeared in logs when reading the flow def); the Mayor approval still points at r.bertram
(set the real Mayor email via the Flow API for production). See "## Latest session -- 2026-06-15
(cont. 5)" below for detail. **Prior (same day):** v1.8 SHIPPED (versionCode 17): settings cog, notification
opt-in + working keyless push, home-screen widget, edge-to-edge fix, dash cleanup. Push
(#64) was proven end-to-end (Firebase on the .gov `exploreburton` project, GCP FCM grant done,
push-send Action + repository_dispatch both smoke-tested with real FCM message ids, a test push
sent). **Power Automate approval flow CREATED** ("Explore Burton -- send push",
49bcb0ab-...); USER must edit 2 placeholders in the portal (PAT in the HTTP action + Mayor's
approval email) then test. SharePoint "Push Requests" list created. #16/#32/#30/#67/#68 CLOSED
earlier today. See the FOLLOW-UP entries below for full detail. **Pending user:** wire the flow's
2 fields; delete the personal `explore-burton` Firebase project; device-verify push+widget+edge-
to-edge on 1.8; cut 1.9 for the widget board-name + the app quick-row tweak (web already live).
History of this date's earlier work follows. **Prior -- 2026-06-12 (cont. 2):** v1.5 CONFIRMED on
Play internal (run 27427660596); #21 Dependabot RESOLVED + CLOSED (0 open alerts); CI workflows
bumped to Node-24 action majors,
verified green.** See "Latest session -- 2026-06-12 (cont. 2)" below. Earlier same day: **UI/UX
Phase 4 + map fixes SHIPPED & pushed.** `main` is pushed (origin up to date). Closed this session: #54-#59 (Phase 3, in v1.4), #15
(installable-app epic done), #53 (canonical share URL), #30 (real Android edge-to-edge), #60
(semantic tokens), #61 (dark mode), #62 (saved places), #63 (Open Data page). **#61 dark mode** =
opt-in System/Light/Dark toggle in About > Appearance, defaults LIGHT (surfaces tokenized across
app.css + 22 components; accent buttons AA-verified; theme-aware native status bar). Three map fixes
also shipped: removed bogus "Crossway cafe" + moved Harmony Baptist Church (overrides.json ->
data.geojson, 1145->1144), loosened pan bounds (viscosity 0.5 / pad 0.3 -- edge-centring no longer
snaps back), and cluster preview (hover tooltip + tap popup of places in a bubble; cluster.ts tested).
**Verified in-browser via Playwright** -- dark mode across guide/map/charts/open-data, cluster
hover+tap, the data fix; only console noise was Cloudflare-RUM CORS on localhost. **v1.5 Android
release SUCCEEDED** (run 27427660596, after the styles.xml `--`-in-XML-comment fix `c872f65`; the
first attempt 27426847511 failed on it) -- dark mode + edge-to-edge + map fixes now on the internal track.
**STILL NEEDS on-device check:** #30 edge-to-edge (status-bar icon contrast light/dark; nothing
clipped under notch/gesture bar) -- rollback = re-add windowOptOutEdgeToEdgeEnforcement to styles.xml.
Once happy with dark, flip theme default to 'system' in theme.ts loadThemePref. **#64 push: SCOPED**
(Mayor authorizes -> IT final approval; non-emergency <1/week; needs Firebase + scope/Android-first
confirm). **#65 widget: DEFERRED** (native, own session). New vault notes: "Explore Burton --
Submission & Push Pipelines" (Applications) + "M365 Automation (Power Automate, Forms)" (Reference). **Prior -- 2026-06-11 (cont. 3):** **UI/UX Phase 3 code-complete.** Shipped to LOCAL main
(4 commits, NOT yet pushed -- user runs `git push origin main`): **#54** Android hardware
back-button (priority chain: overlay -> About -> Detail -> map -> exit; pure `backDecision` + 6
tests; `@capacitor/app` added + `cap sync`), **#59** native first-run onboarding (already reused
the #36 welcome modal; locked the show-once contract behind a tested `welcomeDismissed` helper),
**#58** offline badge (reactive `ui.online` + `OfflineBadge` on the Guide + CivicClerk meetings +
waste lookup; web + native), **#57** native quick-actions row (Near me/Waste/Meetings/Contact,
`QuickActions.svelte` native-only; Near me reuses the map's geolocation via a store nonce; guide-
section targets guard-tested). **#55 deep links + #56 launcher shortcuts now MERGED to local main**
(blocker cleared): autoVerify intent-filter + `appUrlOpen`/`getLaunchUrl` handler (`deepLinks.ts`,
`routeFromUrl` 7 tests) + `res/xml/shortcuts.xml` (3 shortcuts + vector icons). Real Play
App-signing + Upload cert SHA-256s are now in `public/.well-known/assetlinks.json` (from Play
Console -> App integrity; see `docs/assetlinks-setup.md`). So local main is the FULL Phase 3
(8 commits, unpushed). **All native work reaches devices only after a new Android release is cut**
(Actions -> "Android release (Play internal)"); device verification pending (no SDK/device this
session). Gates green throughout: svelte-check 0/159, vitest 108, build clean. Issues #54/#57/#58/#59
auto-close on push; #55/#56 close on the held-branch merge.
**Prior -- 2026-06-11 (cont. 2):** **Fable UI/UX review -> Phase 1 + Phase 2 SHIPPED + deployed
(web + Android v1.3).** Read the review (`planning/UI-UX-REVIEW-2026-06.md`), filed its backlog as
GitHub issues (milestones "UI/UX Phase 1" & "Phase 2"), implemented both, FF-merged to main, closed
all 16. **Phase 1** (#35/36/37/39/40/41/42/43): data-freshness "Data as of" line + committed
`freshness.json` overlay (18 dashboards dated; parks/trails undated; zoning honestly 2017-12),
first-visit **welcome MODAL** (was an inline strip, reworked on review), a11y (Detail Escape+focus,
disabled-facet contrast, guide 48px targets, search helper), per-dashboard descriptions + menu
sub-lines, "report outdated information" link -> `explore@burtonmi.gov` (mailbox created).
**#38** city-approved renames: "Access & Equity"->**Affordability & Access**, "Fiscal Health"->
**Financial Health**, map layer "Road conditions (PASER)"->"...(pavement rating)". **Phase 2**
(#45-#52): sortable/sticky/**CSV-export tables** (new `csv.ts`+`tableSort.ts`), **CVD-aware chart
palette** + greyscale-distinct CompareBars, **place permalinks + share** (`hash.ts`, `#map/place/<id>`,
native share / clipboard), **trend deltas** (`seriesDelta`), **methodology** cards, dashboard
**group + prev/next** nav, desktop **mega-menu** (right-aligned to avoid overflow). ~18 new vitest
(csv/tableSort/hash/seriesDelta + #33/34/35 helpers). **Android v1.3 (versionCode 9)** cut to Play
internal w/ changelog. **Zoning:** investigated the Dec-2023 map PDF (vector but NOT a GeoPDF -- no
CRS; area metrics furniture-contaminated) -> filed **#44** to refresh the overlay from the source
DWG/shapefile (overlay stays 2017 until then). FD logo wired. Gates throughout: svelte-check 0/151,
vitest 89, build clean. Logged obs + ran a skill review. **Then filed the remaining
backlog as issues:** share-URL **bug #53** (share button resolves a localhost/`capacitor://`
URL -- should use the canonical explore.burtonmi.gov base), **UI/UX Phase 3** milestone
(#54-#59: Android back-button, deep links + assetlinks, app shortcuts, native quick-actions
row, offline badge, native onboarding) and **Phase 4** (#60-#65: semantic tokens, dark mode,
saved places, open-data downloads page, push notifications [HITL], home-screen widget). Dev
server stopped. **Open backlog (25 issues):** `gh issue list --state open`; next-up = #53
(quick bug) or Phase 3 (#54 back-button is the easiest start). Still pending elsewhere: zoning
overlay refresh **#44** (needs the DPW DWG/shapefile), dependabot **#21**.
**Prior (2026-06-11 cont.) -- #33 City Alerts banner + #34 Seasonal Ops Status
shipped to main** (commit `f4f2d98`, Pages deploying) + a **status-authoring pipeline spec**.
Both **#33/#34 CLOSED**. Gates green (svelte-check 0/145, vitest 56, build clean). Authoring
model decided: **SharePoint -> Power Automate -> auto-commit JSON** (city has premium PA +
Power Apps licensing); UI front-end (list form vs Power App) is the one open build choice.
Logged obs #252; vault note + memory updated. **Then cut Android v1.2 to Play internal**
(versionCode 8, keyless WIF upload confirmed end-to-end) carrying #33/#34 + a real changelog,
after fixing the release workflow to attach release notes. See the latest-session section below.
**Prior (2026-06-11) -- Large feature + spec session, all pushed + deployed green.**
Shipped: a native-exempt **coming-soon soft-launch gate** (phrase/`?unlock=` bypass, noindex);
**nav cleanup** (Resident Guide label fix, Home pill removed, uniform pill heights);
**#26** Environment good-air-days trend, **#27** Community Health ACS uninsured trend,
**#28** Genesee county-cities compare toggle (all closed); **#16 Part A** polish (data-table
fallback + CSV download on every chart, stat benchmarks, Population sparkline); **Community
Health cities view** (collaborative framing) + reusable **chart upgrades** (annotated trend
markers, multi-line trends Burton-vs-Michigan, CSV export); **Resident Guide enhancements**
(`:::` callouts, Lucide section icons, scroll-reveal, image lightbox, eLocalLink video tour
via privacy facade); and a PII-safe **Fire call-volume map overlay** (proportional symbols by
station). Logged observations #248-250. Wrote 6 parked specs in planning/specs/ (see Open Work).
**Prior (2026-06-10, finance + education expansion, all deployed to main):** Built
on the controller's-office reports (ACFR FY2025, debt schedule, Form 5572 pension/OPEB) the
user dropped in OneDrive `ExploreBurton App/`. Shipped this session (each FF-merged to main +
pushed): **Fiscal Health** dashboard (per-resident debt/pension, statewide percentile ranks,
debt-by-purpose donut [water/sewer 91% vs fire 9%], pension/OPEB assets-vs-owed from FY2025
actuarials -- pension 65% / OPEB 62% funded, reconciles to $29,271,921 = state F-65 = ACFR
govt $2.74M + business-type $26.53M); **Senior Center** dashboard (2025 activity, hardcoded
from staff Excel exports); **Property Taxes** dashboard (city levies only 13.44 mills ~29% of
a bill; County 17.46 is largest; totals-by-district for all 7 districts; 10-yr flat city
millage). Renamed Finances -> **City Finances** (added revenue-by-source from ACFR + budgeting
explainer), moved **Jobs -> People & Housing**, group "Money & Jobs" -> "Money & Taxes". Added
a reusable **"What this means for you"** callout to EVERY dashboard (4 embedded in tools, 15 via
a committed `public/summaries.json` overlaid at load in `App.svelte`) and an interactive
**"How city budgeting works"** explainer (7 concept cards, `InfoExplainer` type) on City
Finances. New types: `InfoSummary`, `InfoExplainer`. Tools: `fetch_fiscalhealth.py`,
`build_seniorcenter.py`, `build_propertytax.py`; enhanced `fetch_finances.py`. Dedup honored:
each figure on exactly one dashboard (millage->Property Taxes, pension/OPEB->Fiscal Health,
budget $->City Finances). Pending: parcel-exact per-authority tax split needs the County
**L-4029** (user can't find a filled-out form). Excel-reading utility venv at `C:/utils/xls-venv`.
**Prior (2026-06-09, cont. 3):** Bridges #20: map overlay (`d6167e2`) + dashboard
enrichment (per-bridge table + state/local comparison, `c68a04f`), both built + browser-verified
on `feature/bridges-map-overlay`, **NOT pushed**. Part A enrichment was already live. See the top
"Latest session" entry below.
**Last touched:** 2026-06-04 (Session: repo cleanup + history scrub) -- Untracked
internal docs (`planning/`, `docs/`) from the public repo and dropped the dead AtoZ
converter. Then scrubbed the GitHub history: the licensed/PII AtoZ data lived in a
**merged PR** (which a force-push cannot remove), so collapsed the repo to a single
clean orphan commit (verified byte-identical tree) and, rather than force-push +
GitHub Support GC, **recreated the remote**: made the old repo private + renamed it
`ExploreBurtonMI-old` (pending user deletion at desk), created a fresh public
`ExploreBurtonMI`, pushed the one clean commit, re-enabled Pages (workflow source) +
custom domain + HTTPS. Site re-verified live (200, cert approved). Recreated the open
tracking issue (now **#1**). Documented the AGOL parcels PII fix in the Obsidian vault
(`Infrastructure/GIS - ArcGIS Online.md`); user opened a service ticket for it.
Local backup: `../eb-history-backup.bundle` (holds pre-scrub history; delete after
old repo is gone).
**Prior (2026-06-04, Overture layer):** Replaced the reverted AtoZ import with an
**Overture Maps business layer (now ~1,208 listings)** and shipped map polish.
Built the Approach-C ingest (out-of-band `tools/extract_overture.py` -> committed
`pipeline/data/overture_places.geojson`; pure-Python normalize + category map,
validated against real data). Filters: home-prone residential categories,
120 m cross-source dedup, and a civic-category exclusion (Overture does NOT supply
Government/Public Safety/Public Works -- the curated layer owns those). Added the
Davison Rd post office to curated facilities and labeled the OSM Manor Dr post
office (both USPS locations kept). Added a gold **city-limits outline + locked
view** to the viewer (pipeline publishes `public/boundary.geojson`; verified in a
real browser). Overture attribution added (CDLA-required). Commits 820e757 (civic),
ccac06d (boundary), 4e882a5 (post office) are **unpushed** as of this note.
**OPEN -- needs user decision:** the residential category filter (`overture.exclude_categories`)
has false positives -- it drops legit child-care centers (Overture files daycares
under `home_service`), commercial roofers, and supply stores. Full excluded list at
`C:\utils\overture-excluded.csv`. Recommend trimming or disabling the filter; see
Next Up.
**Earlier 2026-06-04:** Reverted an AtoZdatabases import that had been pushed live
(1,549 commercial records, over the vendor's 1,000-record export cap, exposing 88
home-based addresses). AtoZ license is personal-use-only and forbids
reproduction/redistribution -- cannot be published on a public .gov site, not even
as a re-verified seed list. Took it down (3a0e3e3); recorded the sourcing rule in
docs/adr/ADR-0001 (publish only city-owned, open-licensed, or consent data).
**Prior touch:** 2026-06-04 -- Public launch. Enabled GitHub Issues + filed 8 tracking issues (Public launch milestone). Verified/corrected all curated facilities vs burtonmi.gov + Nominatim + OSM building footprints (fixed wrong fire-station addresses, HQ label, library name/street, a 6 km-off park, phantom "Memorial Park", DPW/library/senior phones+hours; added Settlement Park; hid 4 OSM duplicates). Added a merge.py proximity-dedup pass (TDD; 175 features). Added a GitHub Actions build->Pages workflow. Replaced CARTO (not free for public .gov) with State of Michigan public aerial imagery + Esri reference overlays. Pushed; set custom domain; switched Cloudflare explore CNAME to DNS-only + enforced HTTPS. Verified live: <https://explore.burtonmi.gov> returns 200 (GitHub origin), serves the built app + 175-feature data.geojson.

## Latest session -- 2026-07-06 -- Codebase refactor: branch rename + Claude-scrub, plan items 1.2/1.4/1.5, tools/lib (3.1 started)

All work on branch `refactor/codebase-review` (pushed; 23 commits ahead of main, every commit verified
with `npm run check` 0/0 + vitest + build, and pytest for Python changes). Master plan
`docs/REFACTORING_PLAN.md` (gitignored internal doc) -- read it first next session.

**Branch rename + attribution scrub (user-requested):** the old `claude/codebase-review-refactor-y3vsrr`
branch was renamed to `refactor/codebase-review` and its 16 commits rewritten (git-history-surgery skill:
bundle backup in `C:\utils\repo-backups\`, `filter-branch --msg-filter` stripped the Co-Authored-By/
Claude-Session trailers, `--env-filter` fixed author+committer to Ryan Bertram). Tree hash byte-identical;
0 claude/anthropic refs remain in the branch history; old remote branch deleted. Repo-local git identity
set so new commits author correctly.

Completed plan items this session:

- **1.2 Map.svelte decomposition (913 -> 564 lines):** extracted `src/lib/map/clusterPreview.ts`,
  `map/geolocation.ts` (createGeolocation factory), `map/dataLayers.ts` (addConfigOverlays),
  `map/html.ts` (escapeHtml), `map/clip.ts` (boundaryClipPath, leaflet-free so it is unit-testable
  -- vitest env is node, leaflet modules cannot be imported in tests). Overlay geojson was fetched
  eagerly on mount -- now LAZY on first layer-control toggle (L.layerGroup 'add' event; failed fetch
  resets the guard so re-toggle retries). Two intended behavior deltas: overlay layers appear in the
  control in config order (was fetch-completion order), and a failed layer still shows in the control
  (empty) instead of never appearing.
- **1.4 InfoView decomposition (616 -> 445 lines):** extracted `InfoHeader.svelte`,
  `InfoExplainer.svelte` (generic disclosure w/ children snippet; open state per instance),
  `DashboardNav.svelte`. Inner explainer content styles (.ex-*) stay in InfoView (snippet markup
  keeps parent scoping).
- **1.5 shared helpers (3 commits):** `loadJson.svelte.ts` (loadAsync/loadJson runes; migrated Guide,
  WasteSchedule, OpsStatus, CivicClerkMeetings -- fetch now starts at component init instead of onMount,
  equivalent for these components), `charts/chartHover.svelte.ts` (createChartHover, generic over the
  active key; Bars/Donut use an index, TrendLine a [line,dot] tuple), `persisted.svelte.ts`
  (persistedFlag/persistedString/persistedStringSet; migrated InstallPrompt, WelcomeModal,
  ClosureBanner, AlertBanner).
- **3.1 tools/lib STARTED:** created `tools/lib/` (httpio.get_json retry/backoff promoted from
  fetch_schools, arcgis.paged_query, geo.round_coords, paths, iox atomic write_geojson/write_json,
  shapecheck.assert_shape) + `tools/test_lib.py` (13 tests). Migrated the six ArcGIS extract scripts
  (flood, zoning, parks, trails, precincts, access). VERIFIED by regenerating all seven outputs against
  the live APIs: byte-identical to committed. NOTE: only flood + zoning actually had paging loops; the
  other four were single-shot fetches and now just gain retry.

Known nit found: committed `public/info-zoning.json` is stale vs the script (subtitle punctuation `,`
vs `:`) -- predates this refactor; regenerating will produce that one-line diff.

Remaining 3.1 work (UPDATE cont. session: fetch_/build_ families DONE in 4 verified batches, commits
659094a/b35c47e/bbaffc8/270bb27): only extract_crashes/overture/paser/school_districts/transit/
waste_schedule + apply_dupe_overrides/find_dupes/sync_listing_requests remain.
Deferred by user choice (need input before starting): 4.1 boot-payload trimming, 4.5 CSP,
pin-editor relocation. Python venv for tests: `pipeline/.venv/Scripts/python.exe -m pytest
pipeline/test tools -q --ignore=tools/pin-editor` (no repo-root venv; `python3` shim not installed).

## Latest session -- 2026-06-15 (cont. 5) -- Push WORKS end to end + notification polish (v1.9 -> v1.14)

- **Releases:** v1.9 (vc18, widget board-name + Android quick-row tweak) -> v1.10/1.11/1.12
  (push-fix attempts + diagnostics) -> **v1.13 (vc22) = the working push** -> **v1.14 (vc23) =
  notification UX polish.** All keyless WIF uploads to Play internal.
- **Push flow tested live + fixed (two real PA bugs):**
  - Basic-approval ("Start and wait", `/basic/$subscriptions`) returns the decision in
    `body('X')?['response']`, NOT `['outcome']`. The original conditions used `['outcome']` ->
    always-false -> every approval fell through to reject -> nothing sent. Fixed both
    Mayor_approved + IT_approved conditions.
  - The Power Automate **maker designer mangles API-authored flows on save**: it wrapped
    Mark_sent/Reject_* `UpdateItem` actions in an `Apply to each` over an empty `GetItems`
    result, so the status writes never ran. **Edit API-built flows via the Flow API only.**
    Repaired by re-PATCHing the clean definition (`C:\utils\explore-burton-fix-push-flow.js`,
    reads the live PAT, re-PUTs). Flow's Mayor approval is currently `r.bertram` (was set for
    testing); set the real Mayor email via the API for production.
  - Verified the full chain: SP row (Emergency=Yes) -> approvals -> repository_dispatch ->
    push-send Action (real FCM message id) -> row `Sent`. Test rows cleaned up.
- **The dead push -- ROOT CAUSE (found on-device, not from logs):** the Capacitor plugin object
  is a Proxy that turns ANY property access into a native call, INCLUDING `.then`. Returning it
  from an `async` fn or `await`ing it made the Promise machinery probe `.then`, treat the proxy
  as a thenable, and call `proxy.then(resolve,reject)` -> a phantom native call that never
  resolves -> `await loadMessaging()` hung forever (silent). The native plugin was healthy the
  whole time (`checkPermissions()` returned instantly over the bridge). **Fix (commit `2406f3b`,
  v1.13):** `loadMessaging()` is synchronous; the proxy is never awaited -- only real method
  results are. This is the general rule for ALL Capacitor plugins.
  - Earlier red herrings, now also fixed: the plugin was loaded via a type-erased
    `/* @vite-ignore */` dynamic import that never bundled (v1.8-1.10), then a literal dynamic
    import that produced a lazy chunk the WebView would not load -> switched to a **static
    import** so `registerPlugin` lands in the always-loaded main entry.
- **Notification polish (commit `592e979`, v1.14), verified on a local debug build:**
  - **Default channel** `city_updates` (manifest `default_notification_channel_id` +
    `createChannel` in `initPushRuntime()`) -- silences "Missing Default Notification Channel".
  - **Foreground in-app banner** (`PushBanner.svelte`): a `notificationReceived` listener shows
    a toast when a push lands while the app is open (Android suppresses the tray then). Caught
    live in the DOM.
  - **Tap-to-deep-link**: a `notificationActionPerformed` listener routes the message `url`
    through the existing #55 deep-link router (`applyRoute` now exported from deepLinks.ts).
  - Settings now shows an **app-version + push-diagnostics footer** (platform/native/plugin/
    available/permission) so device state is readable, not inferred.
- **On-device debug tooling set up (the thing that cracked it):** standalone `adb` at
  `C:\utils\platform-tools`; CDP probe scripts `C:\utils\eb-cdp*.js` / `eb-verify.js` (node 21+
  global fetch+WebSocket -> `Runtime.evaluate` on the live WebView); LOCAL Gradle builds now work
  (`JAVA_HOME`=JDK 21, SDK at `%LOCALAPPDATA%\Android\Sdk`). Release builds hide the JS layer
  (no WebView debug, no console in logcat) -> use a DEBUG build to inspect. **PWA service-worker
  serves stale assets across `adb install -r`** -> full uninstall (or `pm clear`) to force fresh
  JS. Vault note [[Explore Burton - Submission & Push Pipelines]] has the full recipe.
- **PENDING USER:** uninstall the local debug build + reinstall **v1.14 (vc23)** from Play (signed
  track); **rotate the GitHub fine-grained PAT** (it appeared in this session's logs when reading
  the flow definition; re-paste the new value into the PA `Send_push` action via the Flow API);
  set the real Mayor approval email (Flow API). Obs #267-274 logged.
- **#66 approval-triggered apply -- CODE HALF DONE + VERIFIED (issue still OPEN for the flow).**
  New `apply-listing.yml` Action + a `--payload-file` mode in `sync_listing_requests.py` (reuses
  the pure transforms, no Graph): repository_dispatch(apply-listing) -> apply -> `pipeline/run.py`
  -> commit (GITHUB_TOKEN) -> **dispatch the Pages deploy** (a GITHUB_TOKEN push does NOT auto-
  trigger workflows -- obs #274). Verified via a real dispatch (committed 23a0cfa, deploy run
  27558834914), test override removed (7387917). Add-new rows -> pending-additions.json candidates
  only. Closed #64 (push) + #65 (widget) this session. **Flow REMAINING:** create script staged at
  `C:\utils\explore-burton-create-apply-flow.js` (Flow API; SharePoint trigger Status=Approved ->
  HTTP dispatch -> mark Applied; injects the PAT from the live push flow). GATED on the PAT
  rotation -- rotate first, then create the flow + re-point push so both carry the new PAT, then
  live-test (set one row Approved). NOTE: verify the SharePoint "created or modified" trigger
  operationId (`GetOnUpdatedItems`/`onupdateditems`) + the ChangeType/NewCategory choice-vs-text
  field shapes during the live test.
- **NEW: resident status tracking BRAINSTORMED -> SPECCED -> PLANNED (not built).** User asked for
  "accounts" (track submitted reports/listing updates; owners claim a business). Decomposed: Phase 1
  = **status tracking via magic link, NO accounts** (per-submission 128-bit token stored on the
  intake row; sanitized read-only PA endpoint; `#status` page; on-screen + emailed link; pull-only;
  weekly digest flow for abuse visibility) -> filed **#69**. Phase 2 = **business owner claim +
  real accounts** (needs identity + ownership verification; Entra External ID / Power Pages) ->
  filed **#70** (do after Phase 1). Design + step-by-step TDD plan written LOCAL (gitignored, carry
  flow/list ids): `planning/specs/2026-06-15-status-tracking-magic-link-{design,plan}.md`. Next
  session implements #69 from the plan (start: `track.ts` TDD, Task 1). Obs #275-276 logged.

## Latest session -- 2026-06-12 (cont. 4) -- #14 SHIPPED: Report-an-issue (pin + photo -> DPW queue) + apply shortcut

- **#14 CLOSED (commit `d23efea`, deployed behind the gate).** In-app "Report an issue":
  a warning-icon Leaflet control (next to Near-me) -> `openReport()` modal -> "Tap the map to
  drop a pin" hides the modal into **pin mode** (map click -> `setReportPin` -> modal returns
  with coords; clicks on markers/clusters do NOT count -- they swallow the event, users must
  tap an empty spot, hint text says so) -> category (Pothole/Sign/Drainage/Streetlight/Other) +
  optional description/photo/contact -> POST (text/plain, same CORS trick) -> **flow
  "Explore Burton issue report intake"** (id `423fe4eb-466c-4c11-a527-e7c0d63cd1ad`, created
  via the GCC Flow API) -> row + **photo as native attachment** in SP list **"Explore Burton
  Issue Reports"** (id `a043e86a-1624-4967-bd8c-4d7d6b5ae0e7`, /sites/ITDepartment, private,
  Status New/In progress/Closed) -> **email notify r.bertram** (swap to DPW at full launch:
  edit the flow's Notify_IT step). Server gate: category whitelist, **pin inside the city
  bbox** (42.85..43.15 / -83.85..-83.40), honeypot, ~2MB photo cap. Photos client-resized
  <=1600px JPEG (createImageBitmap+canvas) before upload. Reports NEVER published.
- New: `src/lib/report.ts` (+9 vitest), `ReportIssue.svelte`, store `ui.report` + pin-mode
  helpers, Map control + click handler + hint, config.json `report.url` (public SAS by
  design, same as #3), privacy.html "Issue reports" section. Gates: svelte-check 0/168,
  vitest 151 (24 files), build clean. **E2E:** curl (200 w/ real JPEG attachment; 400
  out-of-city; 400 honeypot) + Playwright (pin-drop, photo-resize path via DataTransfer,
  2 real submits) -- queue rows 1-3 all test rows, **marked Closed**; notify emails received.
- **Deviation from the vault design (deliberate, user-chosen):** direct-to-flow, NO
  Turnstile Worker (consistent with #3; layer it later if spam appears). The vault's
  "pothole can't reuse the #3 intake" constraint was Forms-specific -- dissolved by the
  in-app HTTP intake. Update the vault note when convenient.
- **Desktop shortcut for the #3 apply loop:** "Apply Explore Burton Requests" on the
  Desktop -> `C:\utils\apply-explore-burton-requests.cmd` (sync -> pipeline -> show diff ->
  y/N confirm -> commit+push). Smoke-tested.
- **Flow-API token gotcha (fixed in the helper):** token-manager's `getFlowAccessToken`
  returns null whenever the GRAPH token is expired even if the flow token is valid --
  `explore-burton-flow-api.js` now reads the token store directly.
- **FOLLOW-UP 16 (2026-06-15) -- v1.8 SHIPPED + push flow BUILT.** **v1.8 = versionCode 17**
  on Play internal (run 27519840041) -- first release with the widget Java + Firebase plugin;
  "Restore the Firebase config" + bundleRelease both green, release notes attached. Carries:
  settings cog, notifications opt-in, widget, dash cleanup, edge-to-edge. **Push flow CREATED
  via the GCC Flow API** (id `49bcb0ab-62e9-4af7-9653-6e149d558fa2`, "Explore Burton -- send
  push", state Started): SharePoint new-item trigger on the Push Requests list -> frequency
  gate (Emergency exempt) -> Mayor approval -> IT approval (r.bertram) -> HTTP
  repository_dispatch -> Mark Sent/SentAt, with reject branches. Reused connection refs
  (sharepointonline 900d24aaa..., approvals shared-approvals-9c9633d0...). **USER must edit 2
  placeholders in the portal:** `Send_push` HTTP Authorization `Bearer REPLACE_WITH_GITHUB_PAT`
  -> the PAT (+ Secure Inputs ON), and `Mayor_approval` assignedTo
  `REPLACE_WITH_MAYOR_EMAIL@burtonmi.gov` -> the real Mayor email. Then test (Emergency=Yes row
  skips the cap). Flow def saved C:\utils\explore-burton-push-flow.json. REMAINING: user edits
  the 2 fields + tests the flow; deletes the personal Firebase project; device-verifies push +
  widget + edge-to-edge on v1.8.
- **FOLLOW-UP 15 (2026-06-15) -- push send path PROVEN + flow specced.** Firebase was
  redone under the .gov identity on the EXISTING `exploreburton` Play project (the personal
  `explore-burton` project is to be DELETED by the user). New google-services.json
  (project_id `exploreburton`) in place; secret re-set; `push-send.yml` FCM_PROJECT =
  exploreburton (commit `1bfc8e8`). GCP: FCM API enabled + `play-publisher@exploreburton`
  granted **Firebase Cloud Messaging API Admin** at PROJECT level (user did it; first attempt
  was on the SA resource -- corrected to IAM project grant). **Smoke tests PASSED**: manual
  workflow_dispatch -> `Sent to topic 'alerts'`, and a **repository_dispatch** (the exact PA
  path) -> `Sent to topic 'service'` -- both returned real FCM message ids (keyless WIF chain
  fully proven). **PAT:** user created a fine-grained PAT (org-owned, ExploreBurtonMI only,
  Contents: Read/write) -- parked in Credential Manager, goes in the PA HTTP action only
  (NOT a repo/GitHub secret). **SharePoint list CREATED:** "Explore Burton Push Requests" on
  /sites/ITDepartment (id `bf0787e8-5def-4be1-9072-81d1ef015bbd`; Title/Body/Topic/LinkUrl/
  Emergency/Status/SentAt/ReviewNotes). **Flow build guide:**
  `planning/specs/2026-06-15-push-flow-build.md` (trigger on item create -> validate ->
  weekly frequency gate [Emergency exempt] -> Mayor approve -> IT approve -> HTTP
  repository_dispatch [204=success] -> Status=Sent/SentAt). HTTP step: POST
  api.github.com/repos/City-of-Burton-IT/ExploreBurtonMI/dispatches, Bearer PAT (Secure
  Inputs on), event_type send-push + client_payload. **No APK change needed for the flow.**
  REMAINING: user builds the flow in make.gov.powerautomate.us; deletes the personal Firebase
  project; ships 1.8 for real device delivery.
- **FOLLOW-UP 14 (2026-06-15, commit `34a2317`) -- Firebase WIRED (push now buildable).**
  User created Firebase project **`explore-burton`** (standalone, not nested under the
  `exploreburton` Play GCP project -- fine for FCM) and placed `android/app/google-services.json`
  (validated: client config, package matches, no service-account markers). Wiring done:
  `npm i @capacitor-firebase/messaging@8.3.0 firebase@12`; `npx cap sync` (3 native plugins now);
  the google-services Gradle classpath + conditional apply were ALREADY in Capacitor's template.
  **Security:** `google-services.json` is GITIGNORED (carries a restricted client API key; public
  repo + security.md) and injected in CI from secret **`GOOGLE_SERVICES_JSON_B64`** (now SET via
  gh, value never hit the transcript) -- decode steps added to android-release.yml + android-debug.yml,
  tolerant of an unset secret (build stays inert). Web build unaffected (precache 659 KiB, firebase
  NOT in the bundle -- push.ts type-erased import keeps it out). 166 vitest, svelte-check 0, build clean.
  **REMAINING: cut release 1.8 (APK still HELD pending user) -> on-device, opt in via Settings ->
  Notifications -> grant the OS prompt -> send a test push from the Firebase console to topic
  `alerts`.** Send path (Part D: function/Worker, PA can't sign FCM) still to build.
- **FOLLOW-UP 13 (2026-06-15) -- Settings cog + Firebase guide + push toggles unhidden.**
  - **Firebase setup GUIDE written** for the user (first-timer): `planning/specs/
    2026-06-15-firebase-setup-guide.md`. Path: add Firebase to existing GCP `exploreburton`,
    register Android app `gov.burtonmi.explore`, download `google-services.json` ->
    `android/app/`, Claude wires npm+Gradle+sync, user cuts 1.8; test receive via the
    Firebase console (send to topic `alerts`), no send-path needed. Open Q for user:
    commit google-services.json (recommended; it's a client config not a secret) vs CI-inject.
    Send path = Part D (needs a function/Worker; PA can't sign FCM token).
  - **Push toggles UNHIDDEN on native** (commit `2436b1b`): `NotificationSettings` now shows
    whenever `isPushSupported()` (native), not only when wired -- so internal-testing builds
    can set prefs pre-Firebase (saved, applied once live; "turns on in an upcoming update"
    note). Hidden on web (push is native-only).
  - **Settings cog SHIPPED** (commit `8392206`, deployed web): new `Settings.svelte` modal
    (cog icon, far-right in the header nav, all platforms) holding **Appearance + Notifications**,
    both MOVED OUT of About (About now = credits/privacy/feedback only). `ui.settingsOpen` +
    openSettings/closeSettings in the store; Android-back via registerOverlay. **Quick-actions
    row: Waste pickup REPLACED by a bell "Notifications" -> openSettings** (row now Near me /
    Notifications / Meetings / Contact / Report; waste still in the Guide). Browser-verified
    desktop + 390px (cog opens Settings, theme toggles from there, notifications hidden on web,
    About has no Appearance, quick swap works). 166 vitest, build clean. **APK still HELD.**
- **FOLLOW-UP 12 (2026-06-14, commit `8355f1a`) -- #65 Android home-screen widget BUILT
  (native, untested -- ships on next release).** AppWidgetProvider
  `ExploreWidgetProvider.java` + `res/layout/widget_explore.xml` +
  `res/xml/widget_explore_info.xml` + `widget_bg.xml`, registered in AndroidManifest,
  strings added. Shows the active city alert (fetches `alerts.json`, same start<=today<=end
  rule) + the next CivicClerk meeting (fetches the Events API, `$top=1 $orderby=startDateTime
  asc $filter=startDateTime ge <nowUTC>`). Network on a background thread via `goAsync()`;
  defensive fallbacks ("No active alerts" / "Meetings unavailable"), never crashes. Whole
  card opens the app; meeting row deep-links `#guide/meetings` (reuses #55). Source is
  ASCII-only (⚠/· escapes) for javac-encoding safety. ALL touched XML expat-parsed
  (the android/-gates gotcha). **CANNOT compile/verify here (no SDK; APK held) -- device-verify
  after the next release: add widget to home screen, confirm alert+meeting render, taps open
  the app.** updatePeriodMillis 30min (Android min).
- **FOLLOW-UP 11 (2026-06-14, commit `9788d02`) -- #64 push CLIENT SCAFFOLD (inert).**
  Decisions confirmed: topics alerts+service+**meetings**, Android-first, opt-in/anonymous.
  `src/lib/push.ts` (topic prefs pure+tested, permission+subscribe via type-erased lazy
  import of `@capacitor-firebase/messaging` so it's a NO-OP until the plugin exists) +
  `NotificationSettings.svelte` in About (per-topic toggles, HIDDEN until `isPushAvailable()`).
  Nothing in the web bundle; web/APK builds unaffected. **Firebase-later steps (in the spec):
  create Firebase project + `google-services.json` + google-services Gradle plugin; `npm i
  @capacitor-firebase/messaging firebase`; `cap sync`; then build the send path (Power
  Automate -> FCM HTTP v1 behind the Mayor->IT approval gate).** Send path NOT built (needs
  the FCM project). 166 vitest.
- **APK HELD (user request 2026-06-14):** do NOT cut a release. Last shipped = v1.7.2
  (versionCode 16). Pending for the next release: the dash-text cleanup (cc154ad), the #65
  widget, and -- once Firebase exists -- push. The dvh mobile-web fix (efbc687) is already
  live on web.
- **FOLLOW-UP 10 (commits `b16bcce`+`b548f72`, **v1.7.2 = versionCode 16** on internal) --
  #30 DIRECTION DECIDED: the app sits fully ABOVE the nav bar.** v1.7 on-device (Pixel 6
  Pro, WebView 149, screenshots via OneDrive `ExploreBurton App/`) showed insets working
  EXCEPT the custom `.map-credit` (c) About button (not a Leaflet control -> missed by the
  leaflet-bottom lift). Spot-fixed in v1.7.1 (vc 15), then the user chose NO under-bar
  drawing at all ("why would we want it under the nav bar?") -> `.app` now pads BOTTOM with
  the inset var (matching top) and the per-element lifts were REVERTED (map-credit, zoning
  legend, leaflet-bottom margin, locate-msg, List ul, Detail sheet). Safe-area math remains
  ONLY on .app + position:fixed overlays (modals, InstallPrompt). Web unchanged (all 0).
  **Device-verify v1.7.2, then close #30.**
- **FOLLOW-UP 9 (same session, commit `02de0cd`, v1.7 = versionCode 14 on internal) --
  #30 ATTEMPT 2 (real root cause) + phone UX:** v1.6's var() CSS was right but the vars
  never got real values: theme code called the LEGACY `@capacitor/status-bar`
  `setOverlaysWebView(true)` every launch, which sets DEPRECATED
  SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN flags (verified in plugin source) that fight Capacitor
  8's core **SystemBars** plugin (the thing that pads the WebView on old Chromium / passes
  env() through on 140+ and injects the `--safe-area-inset-*` vars). Fix: status-bar
  plugin REMOVED from the project; theme now drives core `SystemBars.setStyle` (styles
  nav-bar icons too). **Verify on v1.7; if still broken, get the device's Android System
  WebView version.** Also (user request): Near-me/Report map buttons are now DESKTOP-ONLY
  (never created on native, CSS-hidden <=860px) and the **quick-actions row now shows in
  mobile browsers too** (native + <=860px web; Report included) -- browser-verified both
  widths. android/ diff = generated gradle files only (plugin dereg, no XML).
- **FOLLOW-UP 8 (same session) -- v1.6 RELEASED to Play internal** (run 27445659863,
  **versionCode 13**, status completed, release notes attached -- runtime log verified).
  Carries ALL of today's work to devices: #3 + #14 forms (suggest-edit / report-an-issue
  incl. Blight + the native Report quick-action), #32 road closures, #16 ethnicity charts,
  #68 labeled map buttons + Open Data menu move, and the **#30 bottom-inset fix -- verify
  edge-to-edge on the Play build directly** (list last row / Detail sheet / forms clear the
  bar in BOTH 3-button and gesture nav), then close #30. This run also live-verified
  **auth@v3** (the last unexercised Node-24 action bump) -- the whole CI action-bump set
  is now confirmed green in production paths.
- **FOLLOW-UP 7 (same session, commit `9670d46`) -- #32 CLOSED: Road closures.** Per the
  approved spec `2026-06-11-road-closures.md`: `closures.ts` (local-clock active filter,
  inclusive dates, set signature, status-coloured GeoJSON; 8 vitest), `ClosureBanner.svelte`
  (dismissal keyed to the active-set signature -- returns when the set changes; MDOT MiDrive
  deep link, no client MDOT fetch possible/CORS), always-on Map layer (overlayMarkers pane,
  full=red `#d93025` / partial=amber `#f29900`, escaped popups), `public/road-closures.json`
  ships EMPTY w/ authoring comment (city populates; `updated` stamp), PWA cache regex
  extended. Browser-verified via route-mocked closures (all spec checklist items incl.
  set-change re-show + 390px). MDOT text-list ingestion stays a documented future upgrade.
- **FOLLOW-UP 6 (same session, commits `99da16b` + `ed7cb6c`) -- #16 VERIFIED + CLOSED:**
  audit confirmed all plan items shipped (benchmarks, value labels + table fallback,
  sparkline, freshness) and the last gap -- **Race & ethnicity over time** -- was built:
  decennial 2000 sf1 P004 / 2010 sf1 P5 / 2020 pl P2 + ACS B03002 endpoint (codes verified
  against each dataset's groups JSON). White 90.9->79.5, Black 3.5->9.5, Hispanic 2.3->4.5,
  Two+ 1.8->5.3 (%). Multi-line trend chart + caveat note.
- **FOLLOW-UP 5 (same session, commit `99da16b`) -- #16 slice: Race & ethnicity donut on
  Demographics.** ACS **B03002** (the standard mutually-exclusive partition: Hispanic/Latino
  any race; all other groups non-Hispanic alone; AIAN/NHPI/some-other -> "Other" at <1%
  each). Burton 2023 5-yr: White 79.5 / Black 9.5 / Two+ 5.3 / Hispanic 4.5 / Asian 0.6 /
  Other 0.5; **partition sums exactly to the 29,529 population stat** (validation).
  Category-definition note in the panel; pytest 10 (census), browser-verified (NOTE: a
  pre-regen stale in-memory panel needed a reload before the new chart appeared -- not a
  bug). #16 stays OPEN (multi-decade trends etc. remain). Deploy green.
- **FOLLOW-UP 4 (same session, commit `977aa05`) -- #30 FIX PUSHED, awaiting device verify:**
  Root cause of the bottom-inset bug: **Capacitor 8's SystemBars core plugin injects
  `--safe-area-inset-*` CSS vars by DEFAULT** (insetsHandling "css") because Android WebViews
  < Chromium 140 report `env(safe-area-inset-*)` as 0 in edge-to-edge -- the app's CSS only
  ever referenced `env()`. Fix = pure CSS, no android/ changes: all 8 safe-area usages now
  use `var(--safe-area-inset-X, env(safe-area-inset-X, 0px))` (app top pad, List bottom,
  Detail sheet, SuggestEdit + ReportIssue modals, InstallPrompt, map toast, NEW Leaflet
  `.leaflet-bottom` lift). Verified: web 0px regression-free + simulated var injection
  (32/48px) applied correctly in-browser. **Debug APK built (run 27443753262, artifact
  explore-burton-debug-apk) -- user sideloads + checks list/sheet/forms clear the bar in
  BOTH 3-button and gesture nav, then cut v1.6 + close #30.**
- **FOLLOW-UP 3 (same session, commit `5f59846`) -- #67 CLOSED:** Blight is now a report
  category -- all THREE sync points updated together: `report.ts` REPORT_CATEGORIES (sync
  warning comment added), the flow's createArray whitelist (PATCHed via the Flow API --
  trigger URL/sig survived the PATCH, config.json untouched), and the list's Category
  choice column (Graph PATCH, `C:\utils\explore-burton-add-blight.js`). Verified: Blight
  POST 200 (test row 4 Closed), unlisted "Graffiti" 400, dropdown shows all 6 in-browser,
  vitest 152. Native quick-actions row gained a **Report** button (triangle-alert icon ->
  `openReport()`) -- native-only, so device verification rides the next Android release
  (v1.6). Notify still goes to r.bertram for ALL categories; split blight to a different
  department later by branching the flow's Notify_IT on category if wanted.
- **FOLLOW-UP 2 (same session, commit `1da17f9`) -- #68 CLOSED:** Open Data moved off the
  top nav into the dashboards menu as a trailing "Data" group (`#opendata` hash links still
  work; trigger shows "Open Data" when active; DashboardMenu.choose widened to AppView).
  The Near-me + Report map controls became labeled pills ("◎ Near me" / "⚠ Report an
  issue") instead of bare glyph squares. Browser-verified desktop + 390px (menu entry, hash
  route, labels visible, layers toggle reachable). Deploy green.
- **FOLLOW-UP (same session, commit `3195e25`, pushed):** pin mode now REMOVES the business
  cluster + hides point-overlay/tooltip panes + the layers box, and makes polygon overlays
  click-through -- a dead-center tap (previously cluster-swallowed) drops the pin, verified
  in-browser; all restored on exit. Layers box gained an explicit **minimize toggle**
  ("–" -> a "Layers" pill, state persisted in localStorage `eb-layers-min`) that works the
  same on desktop/mobile/Android (kept `collapsed: false` for discoverability). **Issues
  filed/updated:** **#67** blight category via the same pipeline + Android quick-actions
  "Report" button (3 sync points listed: report.ts whitelist, flow Validate expression,
  list Category column); **#68** UX -- move Open Data under the dashboards menu + make the
  Near-me/Report map buttons self-explanatory (labeled pills); **#30 REOPENED** -- on-device
  v1.5 shows the TOP inset respected but the BOTTOM hidden under the 3-button nav bar
  (suspects in the issue: decor-fits-system-windows / inset listener / the capawesome
  edge-to-edge plugin; test BOTH gesture + 3-button nav).

## Latest session -- 2026-06-12 (cont. 3) -- #3 INTAKE LIVE: M365 access + moderated in-app listing-request form

- **M365 automation access unlocked (the session's infrastructure half):** Burton tenant is
  **GCC** (see memory `burton-tenant-gcc`) -- Power Platform = .us endpoints; commercial flow API
  returns HTTP 200 + empty (silent wrong-cloud failure). outlook-mcp now GCC-configured + has
  `auth/acquire-flow-token.js` (re-run when the ~70-min Flow token lapses). GCC Flow SP is
  invisible in the Entra API picker -> consent granted via a dynamic-consent authorize URL
  (dead localhost redirect is fine; consent records pre-redirect). Scopes: Flow User/Manage/
  Read/Activity + Graph Sites.Manage.All. **outlook-mcp repo moved**: private
  `City-of-Burton-IT/outlook-mcp`, upstream (ryaker) fully disconnected, never pushed to.
- **#3 intake pipeline BUILT + SHIPPED (commit `8574182`, deployed behind the gate):**
  - **SharePoint moderation list** "Explore Burton Listing Requests" on /sites/ITDepartment
    (id `f5b45cd8-c582-414b-b330-582cde0c304f`, 16 columns, Status defaults New). Created via
    Graph (`C:\utils\explore-burton-provision-list.js`, idempotent). Site choice = USER decision
    (IT Department site, not a dedicated app site).
  - **Power Automate flow** "Explore Burton listing request intake"
    (id `97d46497-41a2-4738-880d-746feab28a5f`) created ENTIRELY VIA THE GCC FLOW API
    (`C:\utils\explore-burton-flow-api.js` + `explore-burton-intake-flow.json`): HTTP Request
    trigger -> server-side validation (required fields, changeType whitelist, honeypot `hp`,
    8k size cap) -> SP Create item -> Response w/ `Access-Control-Allow-Origin: *`. SharePoint
    connectionRef lifted from the user's existing approval flow (`900d24aaa43a41238162af716e03fa8a`).
    **CORS trick: the client POSTs `text/plain`** (simple request, no preflight -- the trigger
    can't answer OPTIONS); flow parses `json(string(triggerBody()))`.
  - **In-app form (replaces the MS-Forms plan -- user choice):** `src/lib/suggest.ts` (payload/
    validation/submit, 10 vitest) + `SuggestEdit.svelte` (modal, WelcomeModal mechanics,
    conditional fields by change type, honeypot, privacy note). Entry points: Detail panel
    "Something wrong? Suggest an edit" (prefills name + listingId) + search empty-state
    "Business not listed? Ask us to add it". Config: `AppConfig.submit.url` in config.json --
    the SAS trigger URL is **public by design** (static app can't hide it; same exposure as an
    anonymous form link; the moderation list is the gate; rotate = regenerate trigger sig).
  - **privacy.html updated** (new "Listing change requests" section -- contact PII verification-
    only, never published; "no names/emails" bullet reworded).
  - **VERIFIED:** curl E2E (200 happy / 400 missing-fields / 400 honeypot) + Playwright browser
    E2E (modal open/prefill, client validation, real submit -> SP row id 2 w/ real listingId,
    add-new via empty state, Escape close). Gates: svelte-check 0/166, vitest 142 (23 files),
    build clean. Console = only the known CF-RUM localhost noise. **Two test rows (id 1, 2) sit
    in the list -- mark Rejected when first reviewing the queue.**
- **APPLY PATH SHIPPED (follow-up same session) -- #3 CLOSED (commit `b64128c`).** User chose
  "both, phased": on-demand now, approval-triggered later (**#66** filed). On-demand =
  `tools/sync_listing_requests.py` (stdlib-only, 12 pytest): reads Status=Approved rows via
  Graph (delegated outlook-mcp token, refresh-grant, no new app registration), folds Fix/
  Closed/Moved into `pipeline/data/overrides.json` (PII never copied; _why carries the row
  number only; Moved-without-pin gets a NEEDS-COORDINATES `_todo` since the pipeline does not
  re-geocode overridden records), routes **Add-my-business to `tools/pending-additions.json`
  candidates for manual vetting** (geometry null = pipeline geocodes by address), then PATCHes
  applied rows Status=Applied. Operating procedure: approve rows -> run the tool ->
  `python pipeline/run.py` -> review diff -> commit + push. **E2E-verified live** (row 2
  approved -> override written -> row Applied; then reverted + both test rows marked Rejected;
  helper `C:\utils\explore-burton-set-status.js`). The tool's pure transforms
  (`row_to_override`/`row_to_candidate`) are the engine **#66** will reuse from a
  repository_dispatch Action (PA flow on Status=Approved pushes row fields; needs a
  fine-grained PAT from the user; NO cloud-side Graph credential needed).
- Blueprint spec `2026-06-12-listing-intake-form-blueprint.md` marked SUPERSEDED (in-app form
  chosen over MS Forms; list section still authoritative).

## Latest session -- 2026-06-12 (cont. 2) -- v1.5 confirmed + #21 Dependabot resolved + CI Node-24 bumps

- **v1.5 Android release CONFIRMED on Play internal** (run 27427660596, success in 3m29s; the prior
  attempt failed on a `--` inside an XML comment, fixed in `c872f65`). **Still pending on-device
  (user):** #30 edge-to-edge check (status-bar icon contrast light/dark; nothing clipped under
  notch/gesture bar; rollback = re-add windowOptOutEdgeToEdgeEnforcement to styles.xml) and the
  dark-mode feel check -- if good, flip the theme default to 'system' in `src/lib/theme.ts`
  (`loadThemePref`).
- **#21 Dependabot RESOLVED + CLOSED** (commit `7346775`). All 7 high alerts were transitive DEV
  deps under `@capacitor/assets@3.0.5` (already latest; no upstream fix): tar<=7.5.10 (6 alerts, via
  its bundled old @capacitor/cli@5.7.8) + minimatch<3.1.3 ReDoS (via @trapezedev/project->replace).
  Fixed with package.json `overrides` (same pattern as the existing uuid override): global
  `"tar": "^7.5.11"` (nested 6.2.1 -> 7.5.16) + scoped `"replace": { "minimatch": "^3.1.3" }`
  (a GLOBAL minimatch override would have downgraded the 10.x copies -- scope it). `npm audit` 0,
  GitHub open alerts 0. Gates green after: svelte-check 0/164, vitest 132/132 (22 files), build +
  PWA clean. Residual risk (accepted, noted): @capacitor/assets' bundled cli@5 now resolves tar 7
  -- only exercised by icon generation, untested.
- **CI: all 4 workflows bumped to Node-24-ready action majors** (commit `c00cf04`) ahead of
  GitHub's **June 16, 2026** forced Node-24 default: checkout@v5, setup-node@v5 (no `packageManager`
  field in package.json, so its new auto-cache behavior is inert), setup-java@v5,
  android-actions/setup-android@v4 (new cmdline-tools 20.0 default), **upload-artifact@v6** (v5
  announced Node-24 support but still declares `runs.using: node20` -- verified each major's
  action.yml via gh api; release-note titles mislead), google-github-actions/auth@v3 (all 5 WIF
  inputs confirmed present in v3), upload-pages-artifact@v5, deploy-pages@v5.
- **Bumps verified LIVE:** Pages deploy green on push (exercises checkout/setup-node/
  upload-pages-artifact/deploy-pages) + dispatched `android-debug.yml` green in 2m42s (exercises
  setup-java@v5, setup-android@v4, upload-artifact@v6, debug APK built + uploaded). **Only
  auth@v3 not yet exercised** (runs only in a real release) -- inputs schema-verified; watch the
  auth step on the next v1.6 cut.
- Obs #264 logged (verify `runs.using` per tag; smoke-test action bumps via the debug workflow).
  **Next up:** user device-verify #30 + dark mode (then theme default flip), then backlog -- #64
  push (needs user scope/Android-first confirm + Firebase project), #14 pothole / #3 business
  updates (designed; #3 lowest-effort pure M365), #65 widget (own session).

## Latest session -- 2026-06-11 (cont.) -- #33 City Alerts banner + #34 Seasonal Ops Status (SHIPPED) + authoring-pipeline spec

- **#33 City Alerts banner -- SHIPPED to main** (`f4f2d98`). Dismissible site-wide banner mounted
  above the app shell in `App.svelte` (the coming-soon gate in `main.ts` sits in front, so it never
  shows on the holding page). Levels emergency(red)/warning(amber)/info(civic blue), active when
  `start <= today <= end` (today = local clock), dismissal remembered per alert `id` in localStorage.
  New: `src/lib/alerts.ts` (pure `activeAlerts(alerts, today, dismissed)` -- ISO string compare, no
  Date parsing), `src/lib/AlertBanner.svelte` (inline Lucide level icons), `public/alerts.json`
  (ships `alerts: []` -> shows nothing), `test/alerts.test.ts` (7 tests).
- **#34 Seasonal Ops Status -- SHIPPED to main** (`f4f2d98`). A new **`ops-status` component guide
  section** ("City Services Status"), same pattern as `WasteSchedule`. Lists only `active: true`
  services with a status colour/icon (in-progress/scheduled/complete/standby), detail, optional link,
  "Updated ..." stamp; all-inactive -> friendly empty state. New: `src/lib/guide/opsStatus.ts`
  (`activeOpsItems` + `statusMeta`), `src/lib/guide/OpsStatus.svelte`, `public/ops-status.json`
  (4 services, all inactive), `test/opsStatus.test.ts` (5 tests). 5-touch wire-up: `index.json`,
  `build_guide.mjs` (no-body component type), `types.ts` (`GuideSectionMeta` union), `GuideSection.svelte`,
  plus an `ops-status` icon (`clipboard-list`) via the regenerated `icons.ts` (verified 20 icons, no drops).
- **Both JSON files added to the PWA runtime-cache regex** in `vite.config.ts` (offline). Native app
  picks them up automatically from the live origin (no app release).
- **Gates ALL GREEN:** `npm run check` 0 errors/0 warnings (145 files), **vitest 56** (8 files, +12),
  build clean (PWA precache 19 entries). **Browser pixels NOT captured** -- no chrome-devtools/playwright
  MCP connected this session; desktop/390px verification falls to the user's dev-server review.
- **Authoring pipeline -- SPECCED, not built:** `planning/specs/2026-06-11-status-authoring-pipeline.md`.
  Decided model: **SharePoint list (DPW edits) -> Power Automate flow -> auto-commit JSON to GitHub**
  (GET sha -> PUT, full-file regen). Bridge = Power Automate (city confirmed **premium PA licensing**, so
  the premium GitHub/HTTP connectors are usable; fallback = scheduled Graph-pull-and-commit on appservices).
  The frontend is decoupled (components just `dataFetch` the JSON), so the UI shipped now and the pipeline
  layers on later. Mandatory **validation gate** in the flow (commits to main = live, no human review).
  **One open build choice:** editing UI = SharePoint list form (free, start here) vs a **Power App** canvas
  form (guided; city has a Power Apps license) -- both write the same list, swappable.
- **Issues #33 + #34 CLOSED** (commented w/ commit + spec ref). **Obs #252** logged (static-site
  delegated-authoring pattern -> brainstorming + planned public-web-map skill it-ops#48). Vault note
  `Applications/Explore Burton.md` updated; memory `reference_m365_automation_licensing` added.
- **NEXT (pipeline build, when greenlit):** create the 2 SharePoint lists + columns (maps in the spec),
  scoped GitHub credential in the PA connection, build the flow + validation gate, test happy-path +
  rejected-row, optional Power App form, hand DPW a one-pager.

**FOLLOW-UP (same session) -- Android v1.2 -> Play internal + release-notes workflow fix:**

- **Diagnosed a stale release:** the previously-run v1.1 was built BEFORE the #33/#34 push (`f4f2d98`), so
  that internal build did NOT contain the new features -- the binary, not the metadata, was the real gap.
  (The user's "changelog + description didn't change" was three separate things: the binary DID update via a
  new versionCode; the **description** = Main store listing [manual, release-independent]; the **public**
  "What's new" = production track, and v1.2 is internal-only.)
- **Fixed `.github/workflows/android-release.yml`** (commit `09cd0bf`): the internal-track assignment sent
  NO `releaseNotes`, so every upload published an empty "What's new". Added an optional `releaseNotes`
  workflow_dispatch input + inject it into the track payload via `jq` (safe JSON escaping; field omitted
  when blank). YAML validated (15 steps, 3 inputs).
- **Re-ran the workflow from `main` HEAD (`09cd0bf`) -> SUCCESS.** Built the AAB WITH #33/#34 + the changelog;
  **versionCode 8** uploaded to the internal track, status completed; log confirms the runtime line
  `Release notes (en-US): New: a city alerts banner...`. **Keyless WIF auto-upload confirmed end-to-end**
  (auth -> upload -> track -> commit) -- closes that open ops item.
- **Still manual / by design:** the store **description** (Main store listing -- paste from OneDrive
  `STORE_LISTING.md` in the console) and the **public** "What's new" (changes only on a production
  promotion). On-device check of #33/#34 + the changelog is the user's (no device access from here).

## Latest session -- 2026-06-10 (cont. 10) -- #29 Fire Chief workbooks -> multi-year trend charts

**FOLLOW-UP REVISIONS (same session, per user review of the dev server):**

- **Removed Avg response time** (stat + note) from the Fire dashboard, and **removed the Mutual aid
  given chart**. Durable: build_publicsafety.py no longer emits the response stat/note (the
  `--response-report` arg + `parse_response_report` deleted); build_fire_trends.py no longer emits
  the mutual-aid chart and gained `DEPRECATED_TITLE_PREFIXES` so a re-merge strips any stale copy.
  EN exports still absent, so info-publicsafety.json was hand-edited for the response removal and
  re-merged by build_fire_trends.py for the mutual-aid strip. Panel now: 5 stats / 5 charts.
- **New top-level "Public Safety" dashboard category** (store.svelte.ts DASHBOARD_GROUPS): contains
  **Burton Fire & Rescue** (publicsafety, was labeled "Public Safety") + **Roadway Safety**
  (roadsafety, was "Traffic Safety"). Both removed from the Infrastructure group. Panel titles
  renamed to match: info-publicsafety.json title -> "Burton Fire & Rescue" (build_publicsafety.py
  too); info-roadsafety.json + extract_crashes.py title -> "Roadway Safety".
- Test updated: dropped the mutual-aid parser test, added `test_merge_strips_deprecated_charts`.
- Gates re-run ALL GREEN: pytest 65, svelte-check 0, vitest 36, build clean. Dev server (:5173)
  serves the renamed 5-chart panel.

**FOLLOW-UP 2 (same session) -- de-draft, FD-category by-type, logo support:**

- **Removed the draft banner + "Draft figures pending" footer note** (Fire dashboard is signed off).
  build_publicsafety.py no longer emits draft/draftNote or the draft footer note.
- **Switched "Responses by type" to the FD's OWN categories with history** (user choice). Dropped the
  NFIRS single-year by-type bars (removed from build_publicsafety.py + DEPRECATED_TITLE_PREFIXES strips
  any stale copy). New **"Calls by type: 2025 vs 2015"** compare chart (FD categories: Hazardous
  Conditions, Fire & CO Alarms, Good Intent/Service, Cancelled En Route, Open Burning, Structure/Vehicle/
  Brush/Other Fires, Rescues & Extrications), biggest-current first, from Annual Stats. Alarms 82->174,
  Hazardous 112->185, Cancelled-en-route 33->94 are the standout decade jumps.
- **"Calls by station area" is now historical** too: a **"2025 vs 2015"** compare (Station 1/2/3),
  replacing the single-year bars. Both comparisons use latest vs ~a decade earlier.
- Final Fire chart set (5): Responses by month (2025) / Calls by type 2025 vs 2015 / Total calls by year
  2014-2025 / Calls by station area 2025 vs 2015 / Busiest months 2020-2025 avg.
- **Logo support added to InfoView** (optional `InfoPanel.logo`, header `<img>` that hides itself on
  load error so a missing file never shows a broken icon). Panel points at `public/burton-fire-logo.jpg`
  -- **user to drop their FD logo jpg at that path** (no FD logo existed in the repo; only burton-seal.png).
- **KNOWN minor nuance (flagged to user):** the "Hazardous-condition calls" STAT = 178 (EN NFIRS series 4)
  while the by-type CHART's "Hazardous Conditions" 2025 bar = 185 (FD workbook category) -- different
  definitions, both real. Stats left untouched (out of the user's ask); offered to reconcile.
- New tool funcs: parse_category_by_year, parse_station_by_year, _baseline_year, _compare_rows. Tests
  updated (station-by-year, category parse, baseline, deprecated-strip of type+station+mutual). Gates
  ALL GREEN: pytest 67, svelte-check 0, vitest 36, build clean.

**FOLLOW-UP 3 (same session) -- reconcile stat + DEPLOY TO MAIN:**

- **Reconciled the Hazardous 178/185 mismatch:** dropped the "Hazardous-condition calls" stat card
  (the FD-category by-type chart shows "Hazardous Conditions" 185 authoritatively; the EN/NFIRS
  series-4 count 178 differed). Removed from build_publicsafety.py + the JSON. Stats now: Total
  responses, Fire responses, False alarms, 11-year change. (False alarms 174 = the chart's Fire & CO
  Alarms 174, so no conflict there.) commit `7b5ac75`.
- **MERGED feature/census-expansion -> main + PUSHED (deploy).** main had DIVERGED (origin/main carried
  2 later Android commits not in census-expansion: `9a77449` hybrid data loading + native geolocation,
  `474bceb` signed AAB + Play upload). Reconciled with a real merge `ee0f71d` (NOT a force-push --
  would have lost the Android work). The Android merge added `@capacitor/geolocation` to package.json;
  ran `npm install` then re-ran ALL gates green (svelte-check 0 over 133 files, vitest 36, build clean,
  pytest 67). Pushed `9a77449..ee0f71d main`. Pages "Deploy to GitHub Pages" workflow in_progress.
- **Logo still pending:** user to drop `public/burton-fire-logo.jpg` (the panel header img hides
  gracefully until then, so the live site shows no broken image). Once added, commit + push to show it.
- Dependabot: 7 high alerts on main = the pre-existing transitive build/dev deps (issue #21), not new.

**FOLLOW-UP 4 (same session) -- branch + issue cleanup:**

- **Dev server stopped** (port 5173 freed).
- **Branch cleanup:** deleted 14 merged LOCAL branches and 5 merged REMOTE feature branches
  (access-crashes, census-expansion, roads-trails-overlays, transit-traffic-parks, zoning-snow).
  KEPT (unmerged): `feature/crime-dashboard-hold` (NEVER push), public-safety-fire/combined/sample
  (old Fire dev branches, superseded by the merged work but not ancestors of main). KEPT remote
  `origin/android-play-release` (looks like an ongoing release branch -- did NOT delete; confirm if
  it should go). Remote now = main + android-play-release only.
- **Issues:** CLOSED **#29** (fire trends -- shipped+deployed) and **#22** (Schools attainment +
  higher-ed -- shipped+deployed; noted ACS enrollment-by-level B14001/B14007 was the one optional
  bullet not added). COMMENTED + kept OPEN **#19** (Public Safety: Fire half live, Crime half still
  held on crime-dashboard-hold pending PD buy-in; noted response-time + combined-panel deviations).
  Left untouched (on hold / not this session): #26 air trend, #27 uninsured trend, #28 county-cities
  toggle, #21 dependabot, #16/#23/#17/#15/#14/#4/#3.

**FOLLOW-UP 5 (same session) -- keyless Play uploads + privacy policy (commit `5942170`, deployed):**

- **Android release workflow converted to KEYLESS** (`.github/workflows/android-release.yml`): the
  Burton GCP org blocks downloadable SA keys (`iam.disableServiceAccountKeyCreation`), so the user
  couldn't create the `PLAY_SERVICE_ACCOUNT_JSON` key (PLAY_RELEASE.md step 3). Switched to **Workload
  Identity Federation**: `permissions: id-token: write` + `google-github-actions/auth@v2` (token_format
  access_token w/ androidpublisher scope = verifies WIF->impersonation->scope BEFORE upload) + **Gradle
  Play Publisher** plugin (`com.github.triplet.gradle:play-publisher:3.12.1` in android/build.gradle;
  `apply plugin` + `play { useApplicationDefaultCredentials.set(true); track.set("internal") }` in
  android/app/build.gradle). Upload step now `./gradlew publishReleaseBundle --track internal
  --release-status <input>`. Removed r0adkll + PLAY_SERVICE_ACCOUNT_JSON.
  - **Chose GPP over fastlane supply** because GPP has first-party ADC/WIF support (verified via README);
    fastlane supply's `--json_key` can't consume an external_account/WIF credential. **Verify-in-CI risk:**
    GPP 3.12.1 vs the bleeding-edge AGP 8.13 -- if publish errors on plugin compat, bump the GPP version.
    Manual first upload ships regardless (the signed .aab is always a workflow artifact).
  - **User's GCP to-do (in PLAY_RELEASE.md step 3, rewritten):** create SA (no key), WIF pool+provider
    locked to repo via `--attribute-condition` (mandatory security), bind principalSet with
    workloadIdentityUser, set 3 new secrets `GCP_PROJECT_ID`/`GCP_WORKLOAD_IDENTITY_PROVIDER`/
    `GCP_SERVICE_ACCOUNT`, remove `PLAY_SERVICE_ACCOUNT_JSON`, invite SA in Play Console. **Pre-warned
    org wall #2:** `iam.allowedPolicyMemberDomains` (domain-restricted sharing) will likely reject the
    `principalSet://` member -> needs a narrow org-policy exception (safer than allowing keys).
- **Privacy policy LIVE:** `public/privacy.html` -> <https://explore.burtonmi.gov/privacy.html> (standalone,
  Burton-branded, NOT behind SPA routing so Play's crawler + the in-app absolute-URL link both resolve).
  Accurate to the app: on-device-only "Near me" geolocation (not collected), Cloudflare cookieless
  analytics, localStorage only for the install-prompt dismiss flag, no accounts/ads/tracking. Linked from
  the **About dialog** (`src/lib/About.svelte`, absolute URL for the bundled app). Contact = **privacy@
  burtonmi.gov** (user picked dedicated role-based; **mailbox needs creating/routing**). This is also the
  Play Console privacy-policy URL (PLAY_RELEASE.md step 2 updated).
- Gates: svelte-check 0, build clean, workflow YAML valid (15 steps). PLAY_RELEASE.md (OneDrive, not
  git-tracked) updated: secrets table + step 3 + privacy URL.

**FOLLOW-UP 6 (same session) -- Android shipped to Play internal testing + store listing:**

- **App LIVE on Play internal testing** (version 1.0, signed, installed + verified on device). City
  of Burton GCP project `exploreburton`; WIF pool/provider/binding set up by the user (gcloud), 3
  `GCP_*` secrets set (no JSON key). Auth chain verified GREEN in CI; the user did the manual first
  upload (enrolls Play App Signing) + granted the SA "Release to testing tracks".
- **GPP dropped, REST upload adopted.** Triple-T Gradle Play Publisher broke the build on AGP 8.13;
  reverted it and switched the upload step to the **Play REST API using the auth step's access token**
  (open edit -> upload bundle -> assign internal track -> commit). Fully keyless, decoupled from Gradle.
- **Two real build fixes (commits on main):** (1) `versionCode`/`versionName` switched to `=`
  assignment -- the `versionCode (expr).toInteger()` method-call form mis-bound under AGP 8.13
  ("Value is null"); (2) **target SDK 34 -> 35** (Play requirement) with
  `android:windowOptOutEdgeToEdgeEnforcement` in styles.xml to keep the layout (temporary until
  target 36 -> filed **issue #30**).
- **Privacy policy LIVE + store listing:** `public/privacy.html` (built + verified) linked in About;
  feature graphic generated (`tools/gen-feature-graphic.mjs` -> `C:\utils\explore-burton-feature-
  graphic.png`, uses the transparent burton-design seal); copy + decisions saved to OneDrive
  `STORE_LISTING.md`. App icon = `public/pwa-512.png`. Category Travel & Local. A **closed (Alpha)**
  release was created to trigger the app's first store review; user sending it for review.
- **Issues:** commented **#15** (installable-app epic: Android tier now in internal testing; iOS
  deferred), filed **#30** (edge-to-edge before target 36). Observations #244-247 logged.
- **Open ops items (not code):** create/route the `privacy@burtonmi.gov` mailbox; add phone
  screenshots to the listing; promote to production when the city decides; re-run the workflow to
  confirm keyless auto-upload once Play permission fully propagates (auth already green).

---

- **BUILT on `feature/census-expansion`** (the held branch where the Fire dashboard lives). #29:
  fold the Fire Chief's 5 OneDrive summary workbooks (`ExploreBurton App/`) into the Public Safety
  (Fire) dashboard as multi-year TREND charts. All ADDITIVE -- the current-year EN snapshot (stats +
  NFIRS "by type" + 2025 monthly) is untouched.
- **New tool `tools/build_fire_trends.py`** (+ `tools/test_build_fire_trends.py`, 10 tests). Reads 4
  of the 5 workbooks, writes a committable fragment `tools/fire-trends.json` (pure aggregates, NO
  PII), and **idempotently merges** 4 charts + 1 stat + 1 note into `public/info-publicsafety.json`.
  Re-runs do not stack (owned chart/stat/note keys are replaced). Reuses build_publicsafety's PII guard.
- **Charts added (after the existing 2):**
  1. **Total calls for service by year (2014-2025)** -- trend. [Annual Stats] 513->758, headline growth.
  2. **Calls by station area (2025)** -- bars. [Station Comparison] Sta 1=325 / Sta 2=335 / Sta 3=96.
  3. **Busiest months (2020-2025 average)** -- bars. [Monthly Average Worksheet] Aug peak 82.8. FULL
     years only (2026 partial excluded).
  4. **Mutual aid given to neighbors (2016-2025)** -- trend. [Annual Comparison] 15->23/yr.
  Plus stat **"11-year change +48%"** (513 in 2014 -> 758 in 2025).
- **Quarterly Statistics.xlsx reviewed, NOT charted** -- quarterly granularity is redundant with the
  annual + monthly views; omitted by design (noted in the tool header), not missed.
- **Source discipline:** annual totals come from Annual Stats / Station Comparison (2025=758, matches
  the live headline). The Monthly worksheet (NFIRS-station based, 2025 sums to 748) feeds ONLY the
  seasonality shape -- the two sources are never crossed in one chart. The workbook's plain-language
  categories (Good Intent/Service etc.) are NOT restated as a chart (they don't reconcile 1:1 with the
  NFIRS series already shown, so juxtaposing would invite "these don't add up").
- **`build_publicsafety.py` wired with `--trends-cache`** (default `tools/fire-trends.json`): a
  from-scratch rebuild from the EN exports now re-merges the trends instead of dropping them. Mirrors
  the `--pd-cache` precedent. EN exports were NOT in Downloads this session, so the merge ran against
  the committed base panel directly via build_fire_trends.py.
- **Gates ALL GREEN:** pytest **65** (was 55; +10), svelte-check 0 errors, vitest 36, build clean.
  Static conformance check: all 6 charts/6 stats match the InfoChart contract; PII guard clean.
  **No new chart component / no new InfoChart type** (reuses trend + bars), so rendering risk is low.
- **Browser QA DEFERRED:** no chrome-devtools/playwright MCP was connected this session. Dev server
  (vite, :5173) confirmed to SERVE the merged panel (HTTP 200, valid JSON, 6 charts) but pixels not
  captured. Pixel-level verification falls to the user's dev-server review at work (the established
  flow for this held branch).
- **TO DEPLOY:** still HELD. After the user reviews `feature/census-expansion` at work, merge -> main.
- **Refresh recipe:** drop updated workbooks in OneDrive `ExploreBurton App/`, run
  `python tools/build_fire_trends.py` (xls-venv or pipeline/.venv -- both have openpyxl), commit the
  regenerated `tools/fire-trends.json` + `public/info-publicsafety.json`.

## Latest session -- 2026-06-10 (cont. 9) -- Traffic Safety + Access & Equity dashboards (dashboard-only)

- **BUILT on `feature/access-crashes` (off main).** Two DASHBOARD-ONLY panels (user: crashes as
  data/trends, no overlay). Cont. 6/7/8 are LIVE on main.
- **Traffic Safety.** `tools/extract_crashes.py` -> `public/info-roadsafety.json`. Source: GCMPC
  `Crash_Locations_2014_2018` (MSP UD-10), `CITY='Burton'`, paginated. **3,011 crashes 2014-2018**
  (2,302 PDO / 700 injury / 9 fatal; 9 killed, 1,020 injured), ~602/yr. Charts: by year, severity
  donut, common types; table of crash hotspots (Bristol & Grand Traverse 153, Belsay & Court 116,
  Atherton & Center 110). Labeled HISTORICAL (2014-2018, not current; road changes since). In the
  **Infrastructure** group.
- **Access & Equity.** `tools/extract_access.py` -> `public/info-access.json`. Sources: GCMPC
  `Median_HH_Income_WFL1` (tract) + `Cars_per_Household_WFL1` (block group; MODELED AMI-household
  H+T cost). Clipped to Burton by census-area interior point (INTPTLON/LAT). **Median income
  $53,945; housing 23% + transport 25% = 48% of income (>45% affordability benchmark -- transport
  costs more than housing here); 1.9 cars/hh; income range $33k-$109k.** Charts: cost-of-living
  share, income distribution across 8 tracts. In **People & Housing**.
  - **Dropped (data-quality):** `LowMod_Income` (layer appears pre-filtered to low-mod BGs -> a "100%
    low-mod" artifact) and the amenity-count chart (`Access_to_Medical` returned 0; schools/groceries
    redundant with the map). Refocused on solid cost+equity (modeled, clearly labeled).
- **Gates ALL GREEN:** svelte-check 0, build clean, vitest 36, **pytest 45** (added
  `test_extract_crashes.py` + `test_extract_access.py`). Browser-verified both dashboards (desktop).
- **TO DEPLOY:** push `feature/access-crashes` + FF to `main`.
- **OPEN:** user ran a ChatGPT repo audit and referenced an attached markdown file of recommendations
  -- the file was NOT found on disk / not received; need it pasted or a path to action it.
- **GCMPC candidates now mostly exhausted** for civic dashboards; Land_Use_2023 remains (lower value,
  overlaps Zoning). Catalog/pattern in vault "Reference/GIS - Genesee County ArcGIS (GCMPC)".

## Latest session -- 2026-06-10 (cont. 8) -- Parks (overlay+dashboard) + Bus stops; AADT/county-stops skipped

- **BUILT on `feature/transit-traffic-parks` (off main).** Cont. 6/7 (Roads, Trails, Zoning, Snow)
  are LIVE on main; #24/#25/#18 closed.
- **Parks.** `tools/extract_parks.py` -> `public/parks.geojson` (park-boundary polygons, "Parks"
  overlay) + `public/info-parks.json` (dashboard). Source: GCMPC `Genesee_County_Parks`, clipped to
  Burton by centroid-in-boundary (bbox pulls in many Flint parks). **7 parks, 416 ac** (For-Mar 364,
  Kelly Lake 41, + small city parks: Settlement, Veteran's Memorial, Water Tower, Fireman's, Davison
  Roadside). Colored by who runs it (City of Burton green / Genesee County blue). Dashboard in the
  **Health & Environment** group. Acreage = full park extent (noted for border parks like For-Mar).
- **Bus stops.** Extended `tools/extract_transit.py` to ALSO emit `public/bus-stops.geojson` from the
  **MTA GTFS stops.txt** (the rider-facing source) clipped to Burton -> **105 stops** as a point
  overlay "Bus stops" (overlayMarkers pane, tappable). Complements the existing bus-routes lines.
- **SKIPPED (data-quality calls, logged not silently dropped):**
  - `Latest_Traffic_Count_AADT` -- counts are 1993-2018 (mostly 20+ yrs old) AND redundant with the
    Roads dashboard's current AADT. Too stale to publish.
  - County `Bus_Stops` (611 unlabeled transit-model points, no names) and `Regional_Transit_Stops`
    (only 4 regional hubs) -- both poor; GTFS stops.txt is the right source (used above).
- **Gates ALL GREEN:** svelte-check 0, build clean, vitest 36, **pytest 39** (added
  `test_extract_parks.py`). Browser-verified parks dashboard + parks overlay (7 polygons) + bus-stops
  overlay (105 markers). Only console errors = expected CF-beacon CORS on localhost.
- **TO DEPLOY:** push `feature/transit-traffic-parks` + FF to `main`.
- **Remaining GCMPC candidates:** Land_Use_2023 (overlaps zoning -- lower priority), crash/safety
  layers (2014-19, label vintage), equity/access block-group layers (a "neighborhood access"
  dashboard). See vault note "Reference/GIS - Genesee County ArcGIS (GCMPC)".

## Latest session -- 2026-06-10 (cont. 7) -- Zoning overlay (#18) + Snow & Ice guide section

- **BUILT on `feature/zoning-snow` (off main), to be pushed.** Continued down the GCMPC ArcGIS
  candidate list (see memory `reference_genesee_arcgis_catalog`).
- **Zoning -- RESOLVES #18.** `tools/extract_zoning.py` -> `public/zoning.geojson` (accurate
  district-polygon overlay "Zoning") + `public/info-zoning.json` (dashboard).
  - Source: GCMPC `Zoning_Layer` filtered `CVT='City of Burton'` -> 746 polygons, **City of Burton
    2017 zoning map** (fields Zoning/ZoneDescr/ZoningCat/AcreCalc). **Replaced the approximate
    georeferenced `zoning-map.jpg` imageOverlay** (config `imageOverlays` now `[]`; removed the
    orphaned `zoning-map.jpg` + `zoning-legend.png`). The generic imageOverlay+legend code in
    Map.svelte/app.css stays for future use.
  - Polygons colored by category (Residential yellow / Commercial red / Office blue / Industrial
    purple / Parking grey). Dashboard: 13,246 zoned ac, 15 districts, 76% residential, 2017; category
    donut (= the map legend), largest-districts bars, district table. Browser-verified: 746 polygons
    render with the right category fills; old "Zoning map (approx.)" overlay gone.
  - Placed in the **People & Housing** dashboard group.
- **Snow & Ice -- Resident Guide section (from the DPW Snow & Ice Control Plan, rev. Dec 2016).**
  New `content/guide/snow-and-ice.md` + registered in `content/guide/index.json` after Roads.
  Resident-friendly: "safe roads at safe speeds" level of service, Priority 1 (major) vs Priority 2
  (local), 7 areas, an accumulation->timeline table (0-2 salt / 2-4 ~24h / 4-8 ~72h / 8-12 ~96h /
  >12 ~120h), no-parking advisories, DPW (810) 742-9230 + Nov 1-Apr 1 activation, salt/winter-sand.
  **No fake plow-priority map overlay** -- the city's actual 7-area/priority-route layer isn't public,
  and approximating it from functional class would mislead residents. Cross-linked FROM the Roads
  dashboard (`info-roads.json` link `#guide/snow-and-ice`, regenerated via extract_paser.py).
- **Gates ALL GREEN:** svelte-check 0, build clean, vitest 36, **pytest 35** (added
  `test_extract_zoning.py`). Browser-verified zoning dashboard + overlay + the snow guide section
  (desktop). Only console errors = expected CF-beacon CORS on localhost.
- **TO DEPLOY:** push `feature/zoning-snow` + FF to `main` (= public deploy). #18 closes on merge.
- **Remaining GCMPC candidates (verified, not yet built):** Bus_Stops (611 pt, complements bus
  routes), Latest_Traffic_Count_AADT (541 pt), Genesee_County_Parks (40 poly), Land_Use_2023_WFL1,
  crash layers (2014-19, label vintage), equity/access layers. Full menu in the vault note
  "Reference/GIS - Genesee County ArcGIS (GCMPC)".

## Latest session -- 2026-06-10 (cont. 6) -- Roads (PASER) + Trails: overlays + dashboards (#24, #25)

- **BUILT on `feature/roads-trails-overlays` (off main), committed, NOT pushed.** Two new
  Infrastructure-group dashboards + toggleable map overlays, both cloned from the Bridges pattern.
- **Roads & Pavement (#24):** `tools/extract_paser.py` -> `public/paser-roads.geojson` (condition-
  colored line overlay "Road conditions (PASER)") + `public/info-roads.json` (dashboard).
  - Source: Genesee County (GCMPC) **PASER_Map_2025_WFL1/3** (RoadSoft, ratings dated **2024**) in
    the official county ArcGIS org `5ckbIY7K9TUKoseK`. NEWER than the handoff's 2021 `PASER_Layer`.
  - **Scope = federal-aid roads only (FEDAID=1)** -- the TAMC-inspected network; clean data
    (~0 unrated). USER CHOSE this scope + the comparison framing (asked, given the sensitivity).
  - Clipped to the boundary (rep-point-in-polygon; segments are short so full LENGTHMILE is fine).
    Condition by TAMC grouping CURRRATING: Good 8-10 / Fair 5-7 / Poor 1-4; 0/null = Not Rated,
    EXCLUDED from the %. Reported **by road-mile**, not segment count.
  - **Burton: 65.4 rated mi, 13% Good / 34% Fair / 54% Poor.** Comparison chart Burton vs **Genesee
    County (10/41/49)** from the same layer + rule -> frames the ~54% Poor as a regional reality
    (Genesee roads are notoriously bad), NOT a Burton outlier. Michigan-statewide PASER is NOT in
    this county org, so the compare is 2-bar (Burton vs county) -- honest + self-sourced.
  - Dashboard: 5 stat cards, condition donut, Burton-vs-Genesee compare bars, road-miles-by-surface
    bars, per-road table (aggregated by name, miles-weighted condition, busiest first). Honest notes
    (Poor = needs major repair not closed; federal-aid only = not every residential street; 2024).
- **Trails & Pathways (#25):** `tools/extract_trails.py` -> `public/trails.geojson` (line overlay
  "Trails & pathways") + `public/info-trails.json` (dashboard).
  - Source: county "Legacy Trail Map" web map -> **Legacy_Trail_Map_WFL1/0** "Major Trail Segments"
    (same org). Fields: NAMELOCAL, STATUS, TRAILTYP, SurfaceType, LENMILES.
  - **LENMILES is the FULL-segment length** (runs far past Burton: Flint River Trail 17.85 mi total)
    -> mileage is **clipped to Burton** (densified midpoint-in-polygon, ~0.02 mi sampling), so the
    headline is honest. Burton: **12.1 existing mi across 4 trails + 4.0 planned mi; 6 named trails.**
  - **STATUS honesty:** Existing = solid line + counted as built; Programmed/Proposed/Under
    Construction = **dashed** line + tallied separately (never shown as built). Confirmed in browser:
    4 dashed (3 programmed + 1 under-construction) vs 4 existing solid.
  - Dashboard: 4 stat cards, miles-by-status donut, by-type + by-surface bars, named-trails table.
- **Wiring (additive):** `public/config.json` dataLayers (+2 line overlays); `store.svelte.ts`
  DASHBOARD_GROUPS Infrastructure (+roads, +trails); `types.ts` InfoView (+'roads','trails');
  `Map.svelte` line `style` now honors `_dashArray` (planned trails dashed). loadInfo auto-derives
  from DASHBOARDS (no hardcode).
- **Gates ALL GREEN:** svelte-check 0 errors, build clean, **vitest 36**, **pytest 32** (18 existing
  plus 14 new in `test_extract_paser.py` / `test_extract_trails.py`). Browser-verified (playwright MCP)
  both dashboards desktop + roads mobile (390px), both overlays on the map (422 PASER segments colored
  230 Poor/138 Fair/54 Good; trails existing-solid/planned-dashed). Only console errors = the expected
  CF-beacon CORS block on localhost.
- **TO DEPLOY:** `git push origin feature/roads-trails-overlays` then merge/FF to `main` (or push main
  directly) = immediate public deploy. **User to run the push** -- roads-condition data is honest but
  publishes "~54% of our roads are Poor" on the city's OWN site (contextualized vs the county). Refresh
  recipe: `python tools/extract_paser.py` / `python tools/extract_trails.py` (re-pulls ArcGIS, rewrites
  the committed geojson+json). Diagnostic kept at `C:\utils\paser-burton-analysis.py`.
- **Deferred:** reconcile this work onto `feature/public-safety-combined` (same as Bridges deferral).
  Issues #24/#25 close on merge.

## Latest session -- 2026-06-09 (cont. 5) -- dashboard enrichments LIVE + keys persisted

- **Broadband dashboard ENRICHED + PUSHED LIVE** (main `9862060`): provider/competition chart
  ("Where each provider reaches" -- 6 terrestrial named + 3 satellite tagged), "9 providers" stat,
  and **adoption 85.5%** (Census ACS B28002), plus a verified FCC **deep-link** to Burton's area
  summary. No pricing (FCC collects none). `fetch_broadband.py` now also pulls the FCC Provider
  Summary + Provider List and (with `CENSUS_API_KEY`) the adoption %. (NOTE: this is the *dashboard*
  enrichment; the sub-place coverage *overlay* remains license-blocked per cont. 4.)
- **Water dashboard: LEAD added + PUSHED LIVE** (main `52a1e6b`): "Lead (90th percentile) 0 mg/L"
  (at/below detection, every period 2017-2023, below the 0.015 action level) from EPA SDWIS LCR
  (keyless). Copper (CU90) + treatment are NOT in SDWIS for Burton, so omitted, not blanked.
- **API KEYS now persisted as USER env vars** (setx): `FCC_USERNAME`, `FCC_HASH`, `CENSUS_API_KEY`,
  `DATA_GOV_API_KEY` -- future sessions inherit them; **declined** the user's "git-tracked key file"
  request (public repo / security.md). See memory `reference_explore_burton_api_keys.md`. Census API
  now REQUIRES a key (no longer keyless).
- **PASER reframe:** the public hunt (statewide TAMC, State-of-MI `michigan_admin` org, GCRC hub)
  found no openly-published PASER feed -- BUT the `PASER_Layer` (`services2.arcgis.com/5ckbIY7K9TUKoseK`,
  Genesee 2021) is in the **official Genesee County ArcGIS org** (same org as the county's trails +
  other data), so it's county data, not a random individual. Usable (labeled "2021") or get a current
  export; TAMC's is biennial (~2023+ newer).
- **NEW: Trails / sidewalks / non-motorized paths -- FEASIBLE, build next.** Genesee County org
  (`5ckbIY7K9TUKoseK`) has a "Legacy Trail Map" web map (owner `MDutkiewicz_GCcountymi`, field
  `LENMILES`). Resolve the underlying FeatureServer, clip to Burton, render as a line overlay (same
  infra as bus routes / transit). Source dashboard:
  `gccountymi.maps.arcgis.com/apps/dashboards/882502c5000146ec8cafa9158a8e63c1`.

## Latest session -- 2026-06-09 (cont. 4) -- mobile bug fixes + Broadband scoping (#20/#21)

- **Bridges work PUSHED + LIVE** (main `c68a04f`): map overlay + dashboard table/comparison.
- **Bug fix PUSHED + LIVE (main `15ab592`): bridge overlay markers tappable on mobile.** Root cause
  (systematic-debugging): point markers were in the `dataLayers` pane (z-350), below the business
  marker-cluster pane (z-600), so clusters swallowed taps -- worst on the zoomed-out mobile fit.
  Fix: new `overlayMarkers` pane (z-650) for point overlays; polygons/lines stay in dataLayers
  (below business markers). Verified at 390px: all markers tappable, popups open.
- **"Dashboard order broken on mobile" -- RESOLVED: stale PWA service-worker cache** on the user's
  phone (serving a pre-grouped-menu bundle). Confirmed by the user: clearing the cache fixed it. No
  code change. (Could not reproduce in a clean dev build -- the grouped dropdown renders correctly on
  mobile in both map and dashboard views.) Lesson: a "broken on mobile only" UI report on this PWA is
  a stale-SW suspect first -- have the user hard-reload/reopen before code-debugging.
- **Dependabot issue filed: ExploreBurtonMI#21** (8 alerts: minimatch ReDoS + 6 node-tar + uuid; all
  transitive build/dev deps, low runtime exposure on a static site).
- **#20 Part C (Broadband overlay) -- BLOCKED by data/licensing; NOT built.** Scoped with the user's
  FCC creds (runtime only): FCC public **Summary by Geography Type** stops at Census **Place** (+
  county/CBSA/CD/tribal/state) -- **NO public tract or block-group summary**. Sub-place data is only
  the **H3-8 "Hexagon Coverage"** / "Location Coverage" files, and **H3-8 is exactly the CostQuest
  Tier-C-licensed republication boundary** -> a sub-Burton choropleth is NOT license-clean without a
  signed Tier-C license (ADR-0001 rules it out). License-clean alternative = deep link to the FCC map.
  Captured in memory `reference_fcc_broadband_sub_place_licensing.md`. Awaiting user's call:
  (a) deep-link enhancement, (b) pursue Tier-C license, or (c) leave as-is. Verified via
  `C:\utils\fcc-explore.py` (as_of 2025-12-31).

## Latest session -- 2026-06-09 (cont. 3) -- Bridges MAP overlay (#20 Part B)

- **Part A (Bridges dashboard enrichment) was ALREADY DONE + LIVE before this session** --
  STATE was stale. Commit `a4c055b` (busiest bridge, ownership, deck length, by-decade) is on
  `origin/main`; `public/info-bridges.json` carries those stats. Verified, not re-done.
- **DASHBOARD ENRICHED FURTHER (per user follow-up) -- commit `c68a04f`, NOT pushed:**
  - **Per-bridge table** ("Every bridge in Burton", busiest first): Bridge / Condition / Built /
    Daily traffic / Maintained by, with a condition-colored dot per row. New `InfoTable` type +
    `src/lib/InfoTable.svelte` (a11y `<table>`, `th scope=col`, decorative dot since Condition is
    also a text column, mobile horizontal-scroll wrapper, Svelte auto-escaped cells). `InfoView`
    renders `panel.tables` after the charts. **First per-item table in any info panel.**
  - **State/local comparison** via the existing (until now unused) `compare` chart + `CompareBars`:
    **Burton vs Genesee County vs Michigan statewide**, Good/Fair/Poor %, all tallied from the SAME
    NBI file by the identical rule. Burton 30/65/5, Genesee 23/62/15, Michigan 34/55/11 (by count).
    **Verified: computed MI Poor 11% + ~11.4k bridge count match FHWA/ARTBA published figures**
    (the deck-area 27.2%/7.8% figures are a different lens -- noted as "by bridge count").
  - Honest small-sample note (n=20, one bridge ~5%). 9 pytest, svelte-check clean, browser-verified
    desktop + 390px mobile (table scrolls inside its own region; panel/page do NOT overflow-x).
- **Part B (per-bridge condition map markers) BUILT + browser-verified on
  `feature/bridges-map-overlay`** (off `main`, commit `d6167e2`, **NOT pushed**):
  - `tools/fetch_bridges.py` now ALSO emits `public/bridges.geojson` (pure
    `build_bridges_geojson`): 20 FHWA NBI bridge Points, each with `_color` by condition and a
    `_popupRows` list. **Coords are `[-lon, lat]`** -- NBI packs West longitude as a positive
    value, so the x must be negated or every point lands in Asia (a pytest asserts the bbox).
    `Unrated -> #888888` via `.get()`, no KeyError on future NBI years.
  - `src/lib/Map.svelte` dataLayers gained `pointToLayer` (condition-colored circle markers) +
    a multi-field `_popupRows` popup (each value escaped in JS; GeoJSON carries no raw HTML).
    **Gotcha fixed:** Leaflet applies the `style` callback to circleMarkers from `pointToLayer`
    too (after it runs), clobbering them to `fillOpacity 0.12` + condition-colored stroke. Fix:
    `style` returns `{}` for `geometry.type === 'Point'` (no-op setStyle). Verified live:
    fill-opacity 0.95, white 1.5px ring. Polygon/line layers unaffected (85 paths still render).
  - `public/config.json`: new `bridges.geojson` layer "Bridges (condition)", off by default.
  - Browser QA (playwright MCP, dev server :4321): 20 markers = 6 Good/13 Fair/1 Poor (matches
    the dashboard + data); popup clean (`HEMPHILL RD over I-475 / Poor / 15,000/day / 1971 /
    State`); 0 new console errors (only the expected CF-beacon CORS block on localhost).
    Gates: 6 pytest, 36 vitest, svelte-check 0 errors, build clean.
- **TO DEPLOY:** `git push origin feature/bridges-map-overlay` then merge/fast-forward to `main`
  (or push `main` directly) -- **pushing to main = immediate public deploy via Actions.** User
  to run the push.
- **Deferred (next session):**
  1. **Reconcile Part B onto `feature/public-safety-combined`** (same pattern as the grouped-menu
     reconcile `792e964`), or it drifts. This is the git-worktree's real job.
  2. **Optional polish:** on-map Good/Fair/Poor legend (popup states condition in words + the
     dashboard donut has the key, so optional); bridge markers share the dataLayers pane (z-350)
     below the business cluster (z-600), so a few may be occluded/unclickable where they overlap.
  3. **#20 Part C -- Broadband coverage overlay** (FCC hexagon files, large) -- still "scope first",
     not started.

## Latest session -- 2026-06-09 (cont. 2) -- dashboard grouping + branch reconcile (after interruption)

- **Grouped dashboard menu LIVE on main** (commit `b5b5be4`, pushed + deploying): the dropdown is now
  themed categories with sub-dashboards. `store.svelte.ts` `DASHBOARD_GROUPS` is the single source of
  truth; flat `DASHBOARDS` derives from it (`flatMap`); `DashboardMenu.svelte` renders category
  headers + indented items. Groups (main, 10 public dashboards): **People & Housing** (Demographics,
  Housing & Growth, Schools) / **Money & Jobs** (Finances, Jobs & Employers) / **Health &
  Environment** (Community Health, Drinking Water, Environment) / **Infrastructure** (Broadband,
  Bridges).
- **Branches reconciled on `feature/public-safety-combined`** (commit `792e964`, local only): brought
  the 4 new public dashboards + analytics index.html onto the PS branch so ALL 11 dashboards + the
  Fire/PD toggle coexist for local review. Same grouping there **plus a 5th "Public Safety" group**.
  This is now the comprehensive local-view branch; `main` stays the live (no-PS) branch.
- **Dev server** runs on `feature/public-safety-combined` at localhost:4321 for local viewing
  (grouped menu + PS toggle). **Lesson (logged obs #118):** the long-running Vite dev server keeps
  stale HMR across `git checkout`; `TaskStop` did NOT kill the node process (orphan kept port 4321,
  forcing a fallback to 4322 and serving an OLD bundle -> false "no toggle" symptom). Fix: kill the
  PID by port and restart dev after branch switches. Don't trust a browser check against a
  branch-switched dev server without a fresh restart.
- **PENDING (the user's open requests, next session):**
  1. **Bridges -- enrich detail** ("too generic"): NBI has more per-bridge fields (owner state/
     county/city, feature carried/crossed, structure length, ADT). Add stats/by-owner chart.
  2. **Bridges MAP overlay**: per-bridge points colored by condition (Good/Fair/Poor) via the
     reusable `config.dataLayers` infra + a bridges GeoJSON; needs `DataLayerConfig`/Map.svelte to
     support point markers (currently polygons/lines). **Visual -- needs browser QA.**
  3. **Broadband MAP overlay**: area-based (FCC hexagon coverage files, large) -- heavier; scope first.
  Note: chrome-devtools MCP disconnected mid-session; map-overlay visual verification needs it (or
  the playwright MCP) back.

## Latest session -- 2026-06-09 (cont.) -- civic dashboards + Fire/PD toggle + analytics plan

- **Fire/PD sub-toggle + dept logos** added to the Public Safety panel (combined branch).
  New optional `InfoPanel.sections` model + segmented control in `InfoView.svelte`; flat panels
  unchanged (shared snippet). `build_publicsafety.py` emits a Fire section always + Police when
  `--pd-cache`. Logos auto-use `public/logo-fire.png`/`logo-police.png` if present, else the seal
  (commit `f92aedf`). **NEED: the two dept logo PNGs.**
- **New "strong-fit" dashboards** building on branch **`feature/civic-dashboards`** (off main,
  publishable -- not pushed yet). User picked Housing, Broadband, Water, Bridges + **Cloudflare Web
  Analytics**.
  - **Cloudflare Web Analytics ADDED** (commit `f3df1f7`): cookieless beacon in `index.html`
    (token is a public client id; no SRI -- CF beacon auto-updates). Goes live with this branch.
  - **FD review applied to the Fire dashboard** (combined branch, commit `e0079b3`): removed the
    response-time stat (FD won't display response times), relabeled NFIRS 3xx "Rescue & EMS" ->
    "Rescue" (FD runs no medical), excluded mutual-aid (out-of-city) responses, wired real logos
    (`burton-fire-logo.jpg`/`burton-police-logo.png`). New CY2025 (Burton incidents): **743**
    responses, 98 fire (46 building). #1390 vs #22 differ ~1% on mutual-aid flagging -> for exact
    final numbers, FD should re-run both EN reports with mutual aid filtered out.
  - **Keys received (runtime only, NEVER committed):** `CENSUS_API_KEY` (Housing), FCC username
    `r.bertram@burtonmi.gov` + token (Broadband). Cloudflare beacon token (committed -- it's public).
  - **ALL FOUR NEW DASHBOARDS NOW LIVE on main** (pushed + deployed + verified on
    explore.burtonmi.gov): Drinking Water (EPA SDWIS), **Housing & Growth** (Census ACS: 13,325
    units, 75.8% owner, $131,200 median value, built-1963 median; commit 2c9d5df), **Broadband
    Access** (FCC NBM: 14,416 homes, 100% at 100/20, 48% gigabit, Cable-dominant; 5cb25a9),
    **Bridges & Infrastructure** (FHWA NBI: 20 bridges, 6 Good/13 Fair/1 Poor, 363k daily crossings;
    c8734dc). Tools: `fetch_housing.py` (CENSUS_API_KEY), `fetch_broadband.py` (FCC_USERNAME
    `r.bertram@burtonmi.gov` + FCC_HASH), `fetch_bridges.py` (keyless, filters NBI to Burton via
    boundary point-in-polygon). Dashboards dropdown now has 10.
  - **LIVE BUG FOUND + FIXED (commit 38c86b3):** `App.svelte` `loadInfo()` hardcoded the 6 original
    dashboard ids, so any new dashboard showed in the menu but its `info-*.json` was never fetched
    -> "temporarily unavailable" on the live Drinking Water panel. Now derives ids from `DASHBOARDS`.
    Lesson: the single-source-of-truth comment was there but the array was still hardcoded; local
    test was a FALSE POSITIVE (dev server had the public-safety branch's fixed App.svelte via HMR).
    Returning users get the fix on next visit (PWA autoUpdate) or a reload.
  - **Drinking Water -- DONE** (commit `1790b28`): `tools/fetch_water.py` -> EPA SDWIS Envirofacts
    (keyless), Burton PWSID **MI0001010**. 21,000 served, 6,203 connections, surface water; 8
    violations on record since 2001 (1 health-based, all resolved, 0 open). Honest health-vs-paperwork
    framing. Wired into DASHBOARDS; verified.
  - **Broadband -- BLOCKED:** FCC Broadband Map API needs **username (registration email) + token**
    together (token alone -> 401). User gave a token; **NEED the FCC username/email.**
  - **Housing & growth -- BLOCKED:** needs **`CENSUS_API_KEY`** (env, never committed; same key that
    built demographics). Plan: ACS place-level housing (units, value, rent, year built, vacancy) +
    maybe Building Permits Survey.
  - **Bridges -- buildable next** (FHWA National Bridge Inventory file; keyless).
  - **Analytics:** Cloudflare Web Analytics chosen (cookieless). **NEED the beacon token** (CF dash ->
    Web Analytics -> add site). Add the JS beacon to `index.html`.
- **Keys this session (runtime only, NEVER committed):** api.data.gov key (PD/CDE), FCC token. Both
  live only in the conversation; rotate if desired.
- **To publish dashboards live:** push `feature/civic-dashboards` -> main (Actions deploys). APK picks
  up dashboards automatically on rebuild. Play: **Internal testing track** = private install (signed
  AAB needed, not the debug keystore).

## Latest session -- 2026-06-09 (Public Safety: real Fire data built; PD + combined local view)

Built the **Public Safety dashboard from real Burton FD data** (Emergency Networking / Tyler RMS),
verified in a browser, **held local pending FD sign-off** (not pushed). PD wired with **sample** data
for layout review pending PD buy-in + a real FBI CDE pull. Full detail in
`planning/specs/2026-06-09-public-safety-dashboard.md` (BUILD NOTES section).

- **Recon via the EN standard-report catalog** (user exported it): mapped every panel metric to an
  aggregate, PII-free report. Used `#1390` (incident-type counts), `#22` (incidents per year +
  monthly), `#922` (avg response time). `#1390`/`#1714` exports carry incident **addresses** (and
  #1714 firefighter names) -- the transform never reads `Location`; a **PII guard** aborts on any
  address-like output. `.xlsx` exports stay in Downloads, never committed.
- **Real CY2025 Fire figures:** 758 responses; avg response **9:37** (dispatch->arrival); 108 fire
  (54 building fires); NFIRS-series mix (Good intent 184 / Hazardous 178 / False alarm 174 / Fire
  108 / Service 94 / Rescue&EMS 18). **EMS only ~2%** -> framed as **Fire & Rescue** (not EMS-heavy).
  **EN history starts mid-2024** (2024 = partial, first incident 2024-06-01, 437; 2025 = first full
  year) -> year-trend replaced by a 2025 **calls-by-month** chart; 2024 labelled partial.
- **Tool:** `tools/build_publicsafety.py` (openpyxl). Optional `InfoPanel.draftNote` so the banner
  says "real, pending review" (not "sample"). Refresh recipe = run #1390/#22/#922 -> Downloads ->
  `python tools/build_publicsafety.py` -> commit the JSON. `npm run check` 0 errors, build clean,
  browser-verified (0 console errors).
- **Police: REAL data now pulled** from **FBI Crime Data Explorer**, **Burton PD ORI `MI2583900`**.
  User supplied a free **api.data.gov key** (runtime only via `DATA_GOV_API_KEY`/`--key`; NEVER
  stored). `tools/fetch_pd_crime.py` maps agency offense *actuals* (violent-crime/property-crime
  aggregates for totals+donut+trend; individual NIBRS offenses for the by-type bars). **CY2023:
  1,159 reported offenses (244 violent / 915 property)**; NIBRS-era trend 2021-2023. (DEMO_KEY 503s;
  a real key returns 400 unless `type=counts&from=MM-YYYY&to=MM-YYYY` + offense slug.)
  `build_publicsafety.py --pd-cache tools/pd-section.json` merges the Police section into the one
  unified panel. Sample mode (no key) still available. **CDE also returns clearances + police
  employment** -- candidate add-ons (clearance rate, officer staffing).
- **`view-local.cmd`** = double-click local viewer (Vite dev server, no PWA SW -> no stale-cache).
  Gotcha learned: a stale PWA service worker from `npm run preview` keeps serving old data; on
  Windows `localhost` resolves to IPv6 `::1` first, so an orphaned `preview` on `[::1]:4321` can
  shadow a `--host` dev server -- kill orphans + unregister the SW. Dev server avoids the SW entirely.
- **Branches (all LOCAL, never pushed):** `feature/public-safety-fire` = real Fire, **Fire-only**
  (FD sign-off candidate; commit `c757ef8`); `feature/public-safety-combined` = real Fire + sample
  Police for viewing (commit `0e25d29`); `feature/public-safety-sample` = original mockup.
- **NEXT:** FD signs off on Fire (esp. response-time method: it's dispatch->arrival and includes
  mutual-aid-given outside the city) -> then the Fire branch can publish. **PD: real CDE data is
  already pulled** (combined branch) -- remaining gate is PD buy-in before the Police section can
  publish. USFA national benchmark (Fire) + possible clearance-rate/officer-staffing (PD, same CDE)
  are fast-follows. Review packet: `planning/public-safety-review-packet.md`.

## Latest session -- 2026-06-09 (dashboards, code review, installable app, Public Safety planning)

Net current state (spanned several sub-sessions; all "live" items pushed to `main` + deployed):

- **Finances dashboard** rebuilt from extracted data -- `tools/fetch_finances.py` pulls a 16-yr
  audited trend from the MI Community Financials API + city adopted-budget constants (budget PDFs
  removed). Live.
- **Map data quality + UX (live):** scrubbed 97 duplicate listings (~1,150 features now) via
  `tools/find_dupes.py` + `tools/apply_dupe_overrides.py` (override-based, auditable, NOT a live
  heuristic); big-box stores collapsed to one pin with multi-value `category` + `services`; Kroger
  fixed; click-to-zoom on select; overlay layer control left open + zoning legend moved bottom-right;
  Guide PDF moved below About; Home button hidden on mobile.
- **Three new dashboards (live):** Community Health (CDC PLACES, Burton place-level), Jobs & Employers
  (Census CBP + BLS, Genesee County), Environment (EPA AirData). New `tools/fetch_health.py`,
  `fetch_jobs.py`, `fetch_environment.py`. Nav redesigned: a **Dashboards dropdown**
  (`src/lib/DashboardMenu.svelte`) holds all six; `DASHBOARDS` in `store.svelte.ts` is the single
  source of truth for the menu, hash routing, and which `info-*.json` panels load.
- **Code review (3 batches, all live):** escape Leaflet tooltip/popup HTML (XSS); WCAG-AA muted text
  via a `--pub-muted` token; dense trend-label collision fix; keyboard-accessible Dashboards dropdown;
  O(1) marker highlight; debounced search; reduced-motion; emitted-coord rounding; `safeHref` guard
  on data-driven links.
- **Installable app (Phase 1, live):** `vite-plugin-pwa` manifest + service worker (precache shell,
  network-first data, capped tile cache) + seal icons (`tools/gen-pwa-icons.mjs`); "Near me"
  geolocation (center + "you are here" marker + nearest-first list; out-of-Burton handled); in-app
  Install button + iOS Add-to-Home hint (`src/lib/InstallPrompt.svelte`); mobile header kept to one row.
- **Native app wrappers (Capacitor 8 -- NOT published):** `android/` + `ios/` scaffolded; icons/splash
  from the seal (`tools/gen-app-assets.mjs`). **Android debug APK builds in CI**
  (`.github/workflows/android-debug.yml`: JDK 21; targetSDK 34 to avoid Android-15 forced edge-to-edge;
  civic-blue status bar via theme; **explicit shared debug keystore from secret
  `ANDROID_DEBUG_KEYSTORE_B64` so the app updates in place** -- signing cert SHA-256 `9569a256...2e66`).
  **iOS compiles unsigned on a macOS runner** (`.github/workflows/ios-build.yml`) -- no Mac needed.
  Test APKs distributed via a **private** repo `City-of-Burton-IT/exploreburtonmi-builds` (Releases)
  and the user's OneDrive (`ExploreBurton App/`). iOS deferred until an Apple Developer account
  ($99/yr); Play deferred until a $25 account, a signed AAB, a privacy policy, and a listing.
- **Specs written (local `planning/specs/`):** `2026-06-08-installable-app.md` (PWA + Capacitor,
  phased), `2026-06-08-business-listing-requests.md` (M365 Forms -> SharePoint -> Graph pull-sync),
  `2026-06-09-public-safety-dashboard.md`.
- **Public Safety dashboard -- PLANNING (not built).** Decided: ONE "Public Safety" panel, with
  **Fire first, then Crime after PD buy-in** (the quarantined `feature/crime-dashboard-hold` work folds in).
  Fire source = Burton FD's **Emergency Networking (Tyler) RMS**; its token API exists but **public API
  docs were not found**, so the plan is to **run reports + export CSV** from EN's reporting/analytics
  module -> transform -> committed `info-publicsafety.json`. NFIRS national figures as a benchmark
  (annual bulk, not live). **Aggregates only; FD sign-off before publish.** A sample mockup (placeholder
  Fire + Police figures, `draft:true info-publicsafety.json`) lives on the **local-only** branch
  `feature/public-safety-sample` (commit d223559) -- NOT pushed, per the crime-hold discipline for
  sample/sensitive public-safety content. `loadInfo` there already derives panel ids from `DASHBOARDS`.

## Latest session -- 2026-06-05 (Public data-sources expansion, issue #5)

- **Issue #5 fully spec'd; 8 sub-issues filed (#6-#13); epic #5 has the tracking checklist.**
  Spec: `planning/specs/2026-06-05-public-data-sources.md`. Architecture (locked): three
  surfaces -- info-panel extensions, toggleable map layers, Guide link-sections. No new
  top-bar tab per topic. Volatile/authoritative-elsewhere civic data is linked, never
  reproduced (ADR-0001). License verdicts done per source (Census redistributable + ToS
  notice required; BS&A public access confirmed live `uid=209`; MTA GTFS terms ambiguous ->
  transit link-out, map layer gated on written permission; MDOT MiDrive = state routes only;
  school districts = TIGER/cartographic SHP->GeoJSON conversion needed).
- **Slice #6 (expanded ACS demographics) SHIPPED to the repo, committed `5167c18`
  (closes #6). NOT YET PUSHED** -- awaiting user OK to deploy live (push = public .gov deploy).
  - `tools/fetch_census.py` extended: ACS tables B15003 (education), B23025 (employment),
    B08301 (commute), B01001 (age), B17001 (poverty), B21001 (veterans). Variable codes
    verified against the Census `/groups/<TABLE>.json` metadata endpoints (keyless).
  - **Population trend uses non-overlapping decennial counts** (2010 SF1 `P001001`,
    2020 PL `P1_001N`) + the ACS estimate -- Census warns against charting overlapping ACS
    5-yr vintages (advisor catch). Trend omitted if <2 points available.
  - **Census API ToS notice** ("not endorsed or certified by the Census Bureau") + a
    comparability caveat added via a new `InfoPanel.notes[]` field rendered in `InfoView`
    footer (reused by slice #7 millage explainer).
  - Panel now: 10 stat cards + 6 charts (tenure donut, age bars, income bars, education bars,
    commute donut, population trend). `public/info-demographics.json` regenerated with the
    live key (key never written to any file).
  - Verified: 9 new pytest (`tools/test_fetch_census.py`), 36 vitest, svelte-check (0 errors)
    and a clean build; browser-verified the rendered panel (a11y snapshot, 0 console errors);
    real values cross-checked vs Census QuickFacts (pop 29,529; bachelor's 16%; poverty 17%).
- **Content sprint SHIPPED + LIVE (commit 2bc3fdb; closes #7/#8/#9/#11).** Three new Resident
  Guide sections, all link-out only (nothing volatile reproduced):
  - **Property Taxes** (`content/guide/property-taxes.md`) -- #9 BS&A Online lookup
    (`bsaonline.com/?uid=209`) + #7 millage/Headlee/taxable-value explainer (folded here per the
    spec's "pairs with Finances"; sourced to MSU Extension + State of Michigan; mill mechanic =
    $1 per $1,000 TV; hypothetical worked example, NO volatile city figures in prose).
  - **Elections** (`elections.md`) -- MI Voter Information Center + Genesee County link-outs; NO
    hard-coded election dates (volatile -> deferred to MVIC).
  - **Public Transit** (`transit.md`) -- MTA Flint routes serving Burton (15 Burton-Davison,
    9 Lapeer, 11 Fenton) + schedules/fares. MTA GTFS map layer still gated on redistribution
    permission (#11 deferred part).
  - All URLs verified to resolve; browser-verified (0 console errors). `notes[]` reserved for the
    Census ToS only (millage explainer rendered at readable size in the Guide, not as a footnote).
- **Business-listing enrichment SHIPPED + LIVE (commit 0ccbe44).** User had manually enriched
  `public/data.geojson` (137 features, Overture-matched phone/website/address) directly, bypassing
  the pipeline. Made it durable + safe: captured into `pipeline/data/overrides.json`, applied
  bright-line policy, regenerated via `run.py`.
  - **Accepted 97 / rejected 40.** Rejected: 14 curated (the hand-verified civic layer is NOT
    regressed with auto-matched data -- e.g. Fire Station 3 had matched a data-broker URL), 13 far
    (>100 m = chain cross-contamination, incl. a 7.5 km post-office match), 7 low-score (<0.60),
    6 no-metadata. Hygiene on accepted: stripped URL tracking params, dropped data-broker domains,
    normalized phones to (810) XXX-XXXX.
  - Verified: 97/97 overrides applied (0 ID-drift no-ops), 0 internal `_enrichment_*` fields in the
    published file (validate allowlist strips them), 1243 features. Audit:
    `C:/utils/eb-enrichment-decisions.csv`.
  - **Civic-facility URLs RESOLVED + applied to `facilities.geojson`** (commits 0d3f8a1 +
    2fe26fa, **HELD -- not pushed/deployed** per user). User supplied authoritative police/fire/
    court URLs; remaining burtonmi.gov dept pages verified live via Playwright (real browser
    bypasses the WAF that 403s curl -- both `/government/` and `/departments/` paths work).
    Applied: Police, Fire 1/2/3 (station_N.php -- replaced the rejected homefacts.com), DPW,
    Senior, Parks Office, Kelly Lake, Settlement Park, Water/Sewer, Health (gchd.us), USPS line.
    67th District Court CORRECTED to the official listing (4081->4094 Manor Dr, phone
    742-1530->743-5600, hours 4:30->4:00, + 67thdc.com). **Lovedale SKIPPED** (lovedale.com 404s).
    Court pin coordinate unchanged (was building-verified); confirm if 4094 needs a pin move.
  - Civic commits (0d3f8a1, 2fe26fa) DEPLOYED + verified live (court shows 4094 / 743-5600 /
    67thdc.com; all burtonmi.gov dept pages confirmed in a real browser).
- **EPIC #5 COMPLETE + CLOSED (commit 1fe220f).** Remaining slices shipped + live + verified:
  - **#10 School-district map layer** -- `tools/extract_school_districts.py` (pyshp pure-Python
    SHP->GeoJSON from the Census cartographic boundary; added to `tools/requirements.txt`),
    `public/school-districts.geojson` = the **7 districts serving Burton** (Atherton, Bendle,
    Bentley, Carman-Ainsworth, Davison, Grand Blanc, Kearsley -- derived from boundary
    intersection, NOT the spec's assumed 4). Reusable toggleable-overlay infra (`config.dataLayers`
    with the new `DataLayerConfig` type); Map.svelte layer control (off by default), districts in a
    dedicated pane below markers and below the dim mask, distinct colors and hover labels.
  - **#12 Roads** -- `content/guide/roads.md`: MDOT Mi Drive live state-route link-out (I-69/I-475/
    M-54 only) + FY2026-27 budget-sourced city corridors (named only -- no amounts/dates/status,
    sourced from the budget PDF) + DPW contact. Live local closures remain blocked (no DPW feed).
  - **#13 Parks/events** -- enhanced existing `events.md` with City Parks + Pavilion rentals +
    Parks & Rec page link (the events calendar already existed).
- **Transit MAP LAYER SHIPPED + LIVE (commit 80a3b87).** Was deferred; unblocked by MTA's Terms
  of Use grant ("you may use MTA content displayed on the Site"). `tools/extract_transit.py`
  parses the MTA Flint GTFS (`mtaflint.org/wp-content/media/gtfs.zip`) -> `public/transit-routes.geojson`
  = the **7 routes whose path passes through Burton** (8, 9, 10, 11, 13, 15, 502; derived from the
  boundary), drawn with the agency's own GTFS route colors. Map.svelte `dataLayers` style now uses
  a feature's own `_color` when present, else the palette. Second map overlay ("Bus routes").
  GTFS download URL: `https://www.mtaflint.org/wp-content/media/gtfs.zip`.
- **MDOT live-closure layer -- NOT built (decision, not a gap).** No public CORS-queryable
  lane-closure feed exists: MDOT open data (ArcGIS) = planned STIP projects, not live closures;
  live closures sit behind the MiDrive app's internal API (undocumented, fragile to build on for a
  .gov site). The Roads section's **Mi Drive link** is the robust live solution and stays. Burton's
  state routes (I-69, M-54/Dort, I-475) are covered by that link.
- **Still deferred (blocked on data that does not yet exist / needs a handoff):** live LOCAL road
  closures (no City/DPW feed), live parks calendar (no machine-readable feed), elections precinct
  overlay (needs precinct GeoJSON from City Clerk / Genesee County GIS). **No open ExploreBurtonMI
  issues remain.**
- **Map-layer infra (reusable):** `config.dataLayers: [{source,label,nameField}]` +
  `DataLayerConfig` type + a single `L.control.layers` in Map.svelte (overlays off by default, in a
  pane below markers + below the dim mask). Two layers live (School districts, Bus routes); adding
  another = one tool that emits a GeoJSON + one config line. Out-of-band tools use `pyshp` (school
  districts) / stdlib csv (transit); both in the pipeline venv, `pyshp` in `tools/requirements.txt`.
- **Remaining slices:** #10 school-district overlay (first map layer + reusable layer-toggle infra),
  #12 roads (budget local list + optional MDOT state layer), #13 parks events (static list).
  Map-layer infra lands in #10. Deferred/blocked: transit map layer (MTA permission), live road
  closures (DPW feed), live parks calendar (feed), precinct overlay (Clerk GIS).

## Earlier session -- 2026-06-05 (info panels + Resident Guide)

- **Issues #1 + #2 DONE and DEPLOYED.** #2 (post-recreate cleanup): bundle archived
  to `C:\utils\session-archive\`, local clone genuinely purged (first gc was a no-op
  until two anchoring refs removed; pack 7.30 MiB -> 928 KiB). #1 (facility coords):
  verified the 6 non-building-verified coords -- corrected the Davison Rd post office
  (~174 m off), confirmed/kept county-health, lovedale (aka Peace Memory Gardens),
  dpw, senior-center; replaced the fake Belsay Rd compost-site with an **off-map**
  "Dump Permits (Brent Run Landfill)" listing (new `offMap` capability: exempt from
  the in-bounds gate, id-guarded to `burton:` ids, not plotted). Pushed (commit
  a5a27e8); #1 auto-closed.
- **Issue #3 logged** (deferred): business/resident listing submissions with an
  approval gate -- architecture options captured.
- **Info panels SHIPPED + LIVE (commit 7f9f554, UI fixes a3dfe36).** Finances +
  Demographics as in-app top-bar views, hash-synced. Hand-rolled SVG charts
  (Donut/Bars/TrendLine, `src/lib/charts/`), data-driven JSON (`public/info-*.json`),
  `tools/fetch_census.py` (key-aware, place FIPS 2612060). Spec:
  `planning/specs/2026-06-05-info-panels.md`. Real data: Finances = FY2026-27 Approved
  Budget ($67.7M; from `C:\Utils\1-FINAL BUDGET BOOK.pdf`); Demographics = US Census
  ACS 2023 5-year (refresh via `CENSUS_API_KEY=<key> python tools/fetch_census.py`,
  key never committed). Later fixes: full-width panels + de-duplicated %-donut legend.
- **Interactive Resident Guide SHIPPED + LIVE (commit c9f8e29; issue #4).** New top-bar
  **Guide** view replacing the re-published PDF packet. 7 sections (Welcome, Staff &
  Council, Meetings, Trash & Recycling, Permits, Events & Parks, Utility Billing).
  Hybrid content in `content/guide/` (Markdown + `contacts.json`/`meetings.json`);
  build-time render `tools/build_guide.mjs` (devDep `marked`) -> `public/guide.json`
  via npm `prebuild` (zero runtime md weight). Section-nav sidebar, `#guide/<section>`
  hash, tap-to-call/email, next-meeting auto-highlight, responsive top-bar pill-bar,
  `public/resident-guide.pdf` download fallback. Content converted from the City Word
  doc via pandoc; auto-pay bank form intentionally NOT reproduced. `nextMeeting.ts` TDD.
  Spec: `planning/specs/2026-06-05-resident-guide.md`.
- **Map zoom bug FIXED + LIVE (commit eeee4da).** Returning to Map from an info view no
  longer zooms out -- capture center/zoom in `$effect.pre` before the workspace hides,
  restore after `invalidateSize`.
- **All deployed:** every commit pushed to `origin/main`; Actions deploy `27031993017`
  succeeded. svelte-check 0 errors, 36 vitest, browser-verified.

## Status

**LAUNCHED 2026-06-04** -- live at <https://explore.burtonmi.gov> (GitHub Pages,
HTTPS enforced), serving the built Vite SPA + 175 verified listings on a State of
Michigan aerial basemap. Deploys automatically on push to `main` via GitHub Actions.

Track 1 viewer is feature-complete through milestone M5. Built as a ground-up
modern rebuild of the forked Finda app (see `../SPEC.md` for the review of the
original). Runs as a 100% static SPA.

Decisions made this session (brainstorm -> build):

- **Base:** custom static rebuild (not Datasette/uMap) - chosen for a public,
  Internet-facing site: near-zero server attack surface, trivial hosting, full
  control of branding. Datasette adopted later as the Track 2 data-exploration tool.
- **Stack:** Vite, Svelte 5 (runes), TypeScript, Leaflet 1.9, markercluster,
  MiniSearch. Swapped Fuse.js for MiniSearch in M4 (Fuse's character-fuzzy gave
  noisy results; MiniSearch's token/prefix matching is predictable for a directory).
- **Basemap:** State of Michigan public aerial imagery (`imagery.michigan.gov`,
  token-free cached MapServer) + Esri reference overlays (World_Transportation,
  World_Boundaries_and_Places) for roads/labels, configured via `tiles.overlays`.
  Replaced CARTO pre-launch -- CARTO requires an Enterprise license for public
  .gov use (free only for non-profit grantees).
- **Hosting:** GitHub Pages at **explore.burtonmi.gov**, deployed via GitHub
  Actions (`.github/workflows/deploy.yml`); Vite `base` stays `/`. DNS CNAME
  (`explore.burtonmi.gov` -> `city-of-burton-it.github.io`) set in Cloudflare as
  **DNS only** (NOT proxied -- a proxied/orange CNAME blocks GitHub's cert + DNS
  check and returns a Cloudflare challenge 403); HTTPS enforced.

**Track 2 (data pipeline)** is built (`pipeline/`, Python). Re-runnable
(`python run.py [--refresh]`); merges OSM businesses (Overpass, clipped to the
Burton boundary from OSM/Nominatim) + curated `data/facilities.geojson` +
`data/overrides.json` (per-ID corrections applied last), geocodes address-only
facilities via the US Census geocoder, validates public-safe (property allowlist,
in-bounds, fail-loud), and emits `public/data.geojson` (191 features). Datasette
remains available for deeper QA; verification was done via the viewer itself.

Implementation notes / deviations from the Track 2 spec:

- **Boundary source:** used OSM/Nominatim `polygon_geojson` (one cached request)
  instead of the County GIS ArcGIS layer - sufficient for point clipping and
  keeps one geo source. Swappable via `pipeline/config.json` `boundary.arcgis_url`.
- **No shapely:** point-in-polygon is a small pure-Python module (`src/clip.py`),
  avoiding a binary dependency on Python 3.14. Validation bbox is derived from the
  boundary's own extent so anything that passes the clip passes validation.

Quality gates (all green): viewer `npm run check` (0 errors) + `npm test`
(23 passing) + `npm run build` (~77 KB gzipped JS); pipeline `pytest` (24 passing).

## Repo

- **History recreated 2026-06-04** to purge licensed/PII data from a merged PR.
  `origin/main` is now a **single clean orphan commit** (`Explore Burton public map`)
  on a fresh public repo at the same URL (`City-of-Burton-IT/ExploreBurtonMI`). No
  prior commits, branches, or PRs exist on it. Deploys on push to `main` via Actions.
- **`ExploreBurtonMI-old`** = the previous repo, now **private + renamed**, still
  holding the full pre-scrub history. **User to delete it** when back at a desk.
- Backup bundle of the old history: `..\eb-history-backup.bundle` (local only;
  contains AtoZ data + residential addresses -- delete once old repo is gone).
- Local clone reflog still has old objects: `git -C <repo> reflog expire
  --expire=now --all && git gc --prune=now` to finish the local scrub.
- `planning/` and `docs/` are now **gitignored** (kept local; not in the public repo).
- Local clone: `C:\IT\ClaudeProjects\ExploreBurtonMI`.

## In Progress

(none - M5 complete)

## Blockers

- **Facility data verified (2026-06-04).** `public/data.geojson` now has 185
  features (170 OSM + 15 curated). All curated facility coordinates were verified
  against burtonmi.gov + Nominatim (building-level) + cross-checked against OSM
  POIs, and now carry explicit Point geometry in `facilities.geojson` (no longer
  dependent on the flaky Census geocoder). Corrections applied: fire stations 1/2/3
  (wrong addresses AND coords; HQ label moved 1->2), Burton Memorial Library
  (renamed from "GDL Burton Branch", street Lapeer->Atherton), Kelly Lake Park
  (~6 km coord fix), police/DPW/court campus (building-level), senior center
  (coord + phone). Phantom "Memorial Park" removed; Settlement Park added.
- **Open data items (non-blocking):**
  - **compost-site** (Belsay Rd) left as-is pending the user's on-the-ground check
    -- no web evidence of a public drop-off; city uses EMTERRA curbside (issue #2).
  - **OSM gas-station duplicates:** RESOLVED -- `merge.py` now runs a
    `dedupe_proximity` pass (identical normalized name within 60 m -> keep first).
    Removed 10 same-site fuel+convenience duplicates (185 -> 175 features); 0
    same-name pairs remain. Conservative full-name match leaves the church/school
    pair and "BP Shop"/"BP" intact (issue #3). 3 new pytest tests cover it.

## Next Up

Site is LIVE. Open work tracked as GitHub Issues under the **Public launch**
milestone. Closed this session: issues 1, 3, 4, 5, 6, 7, 8. Only issue 2 remains
open (the compost-site check below).

1. **compost-site verification (issue #2):** the "Yard Waste & Compost Drop-off"
   on Belsay Rd is at an unverified placeholder coord and has no web evidence of
   a public drop-off (city uses EMTERRA curbside). Confirm on the ground; correct
   in `pipeline/data/facilities.geojson` or remove, then `python run.py` + push.
2. **Parcels PII governance (AGOL, not this repo) -- service ticket opened.** The
   City's `City_of_Burton_Parcels2023` FeatureServer exposes owner names/addresses/
   assessed values and is anonymously readable + referenced by a public web map.
   Fix documented in the vault (`Infrastructure/GIS - ArcGIS Online.md`): publish a
   hosted **view layer** with sensitive fields hidden, share the view publicly,
   unshare the source, repoint apps, disable Export -- plus an Assessor/City-Attorney
   policy call on which fields are legitimately public. User has logged a service
   ticket to track execution.
3. **Updating data later:** edit `pipeline/data/{facilities.geojson,overrides.json}`,
   `cd pipeline; .venv\Scripts\python run.py [--refresh]`, then push -- the deploy
   workflow rebuilds and publishes automatically.
4. **Overture business layer -- SHIPPED to repo (see ADR-0001 +
   planning/specs/2026-06-04-overture-ingest.md). Commits 820e757, ccac06d,
   4e882a5 unpushed; pushing makes the ~1,208-listing map live (from 175).**
   - Approach C: `tools/extract_overture.py` -> committed
     `pipeline/data/overture_places.geojson`; pure-Python normalize +
     `overture_category_map.json` (validated on real data: catch-all 37%->19%),
     120 m cross-source dedup, civic-category exclusion (curated owns
     Government/Public Safety/Public Works), Overture attribution (CDLA). 44
     pipeline tests + 23 viewer tests green. Both USPS locations present (Davison Rd
     curated; Manor Dr via OSM override). City-limits outline + locked view added.
   - **Residential filter DISABLED (resolved).** Verification showed the category
     filter dropped legit child-care centers, commercial roofers, and supply stores
     -- false positives outweighed the benefit. Set `overture.exclude_categories: []`.
     Overture is commercial-sourced so residential exposure is low.
   - **Childcare recategorized (done).** Day-cares Overture mis-tagged `home_service`
     now map to Education via name hints (`overture_category_map.json` ->
     `name_hints`; `normalize_overture.resolve_category`). 12 childcare records ->
     Education.
   - **Restored 2 civic facilities (done).** County Health office + Lovedale
     Cemetery (Overture had mis-tagged them Government -> dropped by the civic skip)
     re-added to curated `facilities.geojson`. **Map now 1,243 listings.**
   - **Review lists (regenerate via the CSV snippet in session notes):**
     `C:\utils\burton-map-all-locations.csv` (all on the map) and
     `C:\utils\overture-excluded.csv` (excluded w/ reason + in_burton flag).
   - **Still future:** city-owned business-registration ingest (needs a City data
     export); optional consent-based "claim/add your business" form. Keep a
     residential filter for the registration source (it carries real home addresses).
   - **Cleanup:** `tools/convert_business_csv_to_geojson.py` (dead AtoZ converter)
     superseded; delete when convenient.
5. **AtoZ follow-up (governance, optional):** confirm publish restrictions in
   writing with the AtoZ rep for the record; optionally add a *link* from the site
   to the authenticated AtoZ patron portal (compliant -- data stays behind their
   auth) instead of hosting any records.
6. **City of Burton public brand applied (done, commit 232d748).** Viewer restyled
   to the burton-design public_site system: civic blue `#2c57a0` + green `#4ea735`,
   Inter body / Poppins headings (shipped in `public/fonts/`), white seal header
   with the dashed-green divider motif, 12 px rounding, branded About modal +
   sidebar/detail. Seal at `public/burton-seal.png`, favicon swapped. Verified in a
   real browser. Marker category colors left as-is (functional).
7. **Responsive mobile/tablet layout (done, commit d7747b6).** Below 860 px the
   viewer becomes a full-screen map with a Map/List toggle in the header; the
   filter/list panel slides in as a drawer over the map (map stays mounted, no
   Leaflet resize glitch; drawer z-index above Leaflet's controls), tapping a result
   switches to map + shows the place detail as a bottom sheet, and list/facet rows
   get larger touch targets. Verified at phone (390 px), tablet portrait (820 px),
   and desktop in a real browser. Desktop keeps the side-by-side sidebar.
8. **Map refinements (done, commit 4a82ff3).** Removed the on-map Leaflet/credits
   overlay (`attributionControl: false`) -- full attribution now lives only in the
   About dialog (OSM/Overture/Esri/State of Michigan credits preserved there).
   Dim-outside-boundary mask: a world polygon with the city limits punched out as a
   hole (`boundary.dimOutside/dimColor/dimOpacity` in config), so Burton reads as the
   bright focus. Added a **Home** button (header, ghost pill) linking to
   <https://www.burtonmi.gov>; wordmark hides < 520 px so the phone header stays one row.
9. **Map credit + filter UX (done, commit 0271409).** Small corner **©** button on
   the map opens the About dialog (belt-and-suspenders attribution alongside the
   removed overlay; About state lifted into the store). Fixed a mobile gap where the
   filtered business list was pushed off-screen below the 17 category filters: the
   sidebar now pins search, caps the category filter to a scrollable 45 %, and flexes
   the results list to fill the rest -- so filtering by category shows results in
   place (verified: Lodging -> 5 results visible) on both phone and desktop.
10. **Polish backlog:** per-category map legend; optional Playwright smoke test.

## Public-safe review (M5)

- No third-party trackers (Finda's Google Analytics + bostonbuilt.org pixel are
  NOT carried over).
- All external resources are HTTPS (CARTO tiles, Google Fonts not used); no
  mixed-content risk on an HTTPS host.
- URL-scheme validation in `src/lib/templates.ts` (`safeExternalUrl`) rejects
  `javascript:`/`data:` and is unit-tested - fixes the original Finda gap.
- Data is public-safe by construction: the Track 2 `validate` step enforces a
  property allowlist (name/category/address/phone/website/hours/description only)
  and is unit-tested. No owner PII or FOIA-sensitive fields are sourced. OSM data
  is ODbL (redistributable with attribution, which is given in the About modal).
- Static output = no server-side attack surface.
