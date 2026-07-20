# Plain-Language Dashboard Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace dashboard context pills with an accessible plain-language block that includes curated official source links.

**Architecture:** Extend the shared `DashboardContext` contract with optional curated links, validate them at the existing clarity boundary, and render the entire treatment through `InfoHeader`. Keep raw status values stable and translate them with one pure formatter.

**Tech Stack:** Svelte 5, TypeScript 6, Vitest server rendering, Vite, committed JSON dashboard metadata.

## Global Constraints

- Work only on `feature/dashboard-clarity-comparison` in `.worktrees/dashboard-clarity`.
- Use `This covers`, `Information type`, `Time period`, and `Official sources` exactly.
- Translate statuses to `Latest available data`, `Historical record`, `Model-based estimate`, `Adopted plan`, and `Reference information`.
- Allow one to three curated `https` source links and reject duplicate URLs.
- Use existing semantic theme tokens; preserve WCAG AA contrast in light and dark modes.
- Preserve the detailed source footer, strict web/Python/pin-editor/CodeQL checks, issue #94 deferral, and branch protections.
- Do not publish, merge, or alter the baseline worktree.

---

### Task 1: Context contract and status wording

**Files:**
- Modify: `src/lib/types.ts`
- Modify: `src/lib/dashboard/dashboardClarity.ts`
- Create: `src/lib/dashboard/dashboardContext.ts`
- Test: `test/infoPanel.test.ts`
- Test: `test/dashboardSections.test.ts`

**Interfaces:**
- Consumes: `DashboardStatus` and the existing `InfoLink` shape.
- Produces: `DashboardContext.sourceLinks?: InfoLink[]` and `dashboardStatusLabel(status: DashboardStatus): string`.

- [ ] **Step 1: Write failing formatter and validation tests**

Add a table-driven test that expects:

```ts
expect(DASHBOARD_STATUSES.map(dashboardStatusLabel)).toEqual([
  'Latest available data',
  'Historical record',
  'Model-based estimate',
  'Adopted plan',
  'Reference information',
]);
```

Extend `completeClarity.context` with:

```ts
sourceLinks: [
  { text: '2026-27 Approved Budget', href: 'https://example.gov/budget' },
],
```

Add rejection tests for an `http` URL, a fourth link, and duplicate URLs.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `npm test -- test/infoPanel.test.ts test/dashboardSections.test.ts`

Expected: FAIL because `dashboardStatusLabel` and `sourceLinks` validation do not exist.

- [ ] **Step 3: Add the minimal contract and formatter**

Add this field:

```ts
export interface DashboardContext {
  scope: string;
  status: DashboardStatus;
  asOf: string;
  sourceLinks?: InfoLink[];
}
```

Implement the formatter with an exhaustive record:

```ts
const STATUS_LABELS: Record<DashboardStatus, string> = {
  current: 'Latest available data',
  historical: 'Historical record',
  modeled: 'Model-based estimate',
  planned: 'Adopted plan',
  reference: 'Reference information',
};

export function dashboardStatusLabel(status: DashboardStatus): string {
  return STATUS_LABELS[status];
}
```

In `validateContext`, accept an omitted array or validate one to three objects, require
non-empty `text`, require `href` to start with `https://`, and reject duplicate URLs.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run: `npm test -- test/infoPanel.test.ts test/dashboardSections.test.ts`

Expected: all focused tests PASS.

### Task 2: Shared `About this data` renderer

**Files:**
- Modify: `src/lib/InfoHeader.svelte`
- Test: `test/dashboardSections.test.ts`

**Interfaces:**
- Consumes: `DashboardContext`, `dashboardStatusLabel`, and `safeHref`.
- Produces: the single shared resident-facing context block for all dashboards.

- [ ] **Step 1: Write the failing server-render test**

Change the hierarchy fixture assertions to require the visible heading and semantic
row text:

```ts
expect(body).toContain('About this data');
expect(body).toContain('This covers');
expect(body).toContain('City of Burton');
expect(body).toContain('Information type');
expect(body).toContain('Adopted plan');
expect(body).toContain('Time period');
expect(body).toContain('FY2026–27 plan');
expect(body).toContain('Official sources');
expect(body).toContain('href="https://example.gov/budget"');
expect(body).not.toContain('>Scope<');
expect(body).not.toContain('>Status<');
expect(body).not.toContain('>As of<');
```

- [ ] **Step 2: Run the renderer test and verify RED**

Run: `npm test -- test/dashboardSections.test.ts`

Expected: FAIL because the old pill labels still render.

- [ ] **Step 3: Implement the semantic description list**

Render a visible `About this data` heading followed by a `dl` containing three fixed
rows and the optional source row. Render external links with `target="_blank"` and
`rel="noopener noreferrer"`. Retain `aria-label="Dashboard data context"` for stable
automation and accessibility.

Replace pill styles with a compact semantic-token card:

```css
.context {
  border: 1px solid var(--pub-border);
  border-radius: var(--pub-radius-sm, 6px);
  background: var(--pub-surface-2);
  color: var(--pub-ink);
}
.context dt { color: var(--pub-muted); }
.context a { color: var(--civic-blue-link); }
```

Use a two-column label/value grid on larger screens and a tighter label column at
phone width. Allow values and source links to wrap without horizontal scrolling.

- [ ] **Step 4: Run the renderer test and verify GREEN**

Run: `npm test -- test/dashboardSections.test.ts`

Expected: all renderer tests PASS.

### Task 3: Curated sources for every dashboard

**Files:**
- Modify: `public/dashboard-clarity.json`
- Test: `test/infoPanel.test.ts`

**Interfaces:**
- Consumes: the validated `context.sourceLinks` contract.
- Produces: one to three primary official links per registered dashboard.

- [ ] **Step 1: Write a failing committed-data test**

For every registered dashboard, assert one to three source links, unique `https` URLs,
and descriptive text. Add a City Finances assertion for the stable budget page:

```ts
expect(clarity.finances.context.sourceLinks).toContainEqual({
  text: '2026-27 Approved Budget',
  href: 'https://www.burtonmi.gov/government/controller_s_office/budgets.php',
});
```

- [ ] **Step 2: Run the contract test and verify RED**

Run: `npm test -- test/infoPanel.test.ts`

Expected: FAIL because committed clarity records do not yet contain `sourceLinks`.

- [ ] **Step 3: Add curated links**

Use this source routing; each entry is the visible link text followed by its URL:

| Dashboard | Primary official sources |
| --- | --- |
| demographics | U.S. Census data — `https://data.census.gov/` |
| jobs | Census County Business Patterns — `https://www.census.gov/programs-surveys/cbp.html`; BLS Local Area Unemployment — `https://www.bls.gov/lau/` |
| access | Housing + Transportation Affordability Index — `https://htaindex.cnt.org/` |
| housing | Census QuickFacts: Burton — `https://www.census.gov/quickfacts/burtoncitymichigan` |
| zoning | Burton Zoning Division — `https://www.burtonmi.gov/departments/department_of_public_works/zoning_division.php` |
| schools | NCES Common Core of Data — `https://nces.ed.gov/ccd/`; Census data — `https://data.census.gov/` |
| finances | 2026-27 Approved Budget — `https://www.burtonmi.gov/government/controller_s_office/budgets.php`; Michigan Community Financials — `https://micommunityfinancials.michigan.gov/#!/dashboard/CITY/2612060` |
| propertytax | Genesee County Equalization — `https://www.geneseecountymi.gov/departments/equalization/l-4029_information.php`; Burton annual financial reports — `https://www.burtonmi.gov/government/controller_s_office/annual_reports.php` |
| fiscalhealth | Michigan Community Financials — `https://micommunityfinancials.michigan.gov/#!/dashboard/CITY/2612060`; Burton audit reports — `https://www.burtonmi.gov/government/controller_s_office/audits.php` |
| capital | 2026-27 Approved Budget — `https://www.burtonmi.gov/government/controller_s_office/budgets.php` |
| health | CDC PLACES — `https://www.cdc.gov/places/` |
| water | EPA drinking-water data — `https://echodata.epa.gov/echo/sdw_report.get_report?pgm_sys_id_in=MI0001010`; Burton water testing — `https://www.burtonmi.gov/departments/department_of_public_works/water_testing.php` |
| environment | EPA AirNow — `https://www.airnow.gov/?city=Burton&state=MI&country=USA`; Michigan EGLE — `https://www.michigan.gov/egle` |
| parks | Burton Parks & Recreation — `https://www.burtonmi.gov/departments/parks_and_recreation/index.php`; Genesee County Parks — `https://www.geneseecountyparks.org/` |
| trails | Genesee County trails dashboard — `https://gccountymi.maps.arcgis.com/apps/dashboards/882502c5000146ec8cafa9158a8e63c1`; Michigan Iron Belle Trail — `https://www.michigan.gov/dnr/things-to-do/iron-belle-trail` |
| seniorcenter | Burton Senior Center — `https://www.burtonmi.gov/government/senior_center/index.php` |
| broadband | FCC National Broadband Map — `https://broadbandmap.fcc.gov/area-summary/fixed?type=place&geoid=2612060` |
| bridges | FHWA InfoBridge — `https://infobridge.fhwa.dot.gov/` |
| roads | Michigan TAMC — `https://www.mcgi.state.mi.us/mappingforhealth/`; GCMPC pavement conditions — `https://www.gcmpc.org/` |
| publicsafety | Burton Fire Department — `https://www.burtonmi.gov/government/fire_department/index.php` |
| roadsafety | Michigan Traffic Crash Facts — `https://www.michigantrafficcrashfacts.org/` |

- [ ] **Step 4: Run the contract and full Vitest suites**

Run: `npm test -- test/infoPanel.test.ts`

Expected: focused tests PASS.

Run: `npm test`

Expected: all Vitest files and tests PASS.

### Task 4: Verification and comparison handoff

**Files:**
- Modify: `planning/comparison/dashboard-clarity-review.md`
- Update: representative images under `planning/comparison/screenshots/`

**Interfaces:**
- Consumes: the production comparison build on port 4174 and unchanged baseline on port 4173.
- Produces: review evidence for the user; no publication or merge.

- [ ] **Step 1: Run strict checks and production build**

Run: `npm run check`

Expected: zero errors and zero warnings.

Run: `npm run build`

Expected: production/PWA build succeeds.

- [ ] **Step 2: Preserve non-web quality gates**

Run the repository's existing pipeline/tools, pin-editor, and security pytest commands
recorded in the comparison guide.

Expected: every suite passes with unchanged counts or with an explained test-count
increase.

- [ ] **Step 3: Perform responsive visual verification**

Review at least City Finances and one non-City source dashboard at 1280x720 and
390x844, in both light and dark themes. Confirm:

- labels and status phrases are readable;
- the 2026-27 budget and other source links are visible and keyboard-focusable;
- no horizontal overflow occurs;
- the headline and key facts remain near the first phone viewport;
- normal text and links meet WCAG AA contrast.

- [ ] **Step 4: Update comparison documentation and screenshots**

Document the four-row block, status translations, curated-source rule, verification
results, and unchanged old/new URLs. Replace representative comparison screenshots
whose new-side header changed.

- [ ] **Step 5: Review the diff and commit**

Run: `git diff --check`

Expected: no whitespace errors.

Run: `git status --short`

Expected: only context implementation, tests, metadata, comparison documentation,
and intended screenshots are listed.

Commit with a resident-facing message such as:

```text
Clarify dashboard context and official sources
```
