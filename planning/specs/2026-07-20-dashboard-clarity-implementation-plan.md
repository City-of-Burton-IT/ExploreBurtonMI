# Dashboard Clarity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every Explore Burton dashboard a concise, validated resident-facing
headline, visible scope/date/status context, no more than four priority facts,
plain-language interpretation, government responsibility, a next action, and
grouped evidence without changing the underlying chart library or data-download
behavior.

**Architecture:** Keep generated `public/info-*.json` files focused on source data
and place reviewed civic interpretation in a new committed
`public/dashboard-clarity.json` overlay. The dashboard loader validates the raw
panel and clarity record separately, enriches the panel with stable IDs and copy
overrides, then validates the complete `InfoPanel` before it reaches Svelte. Shared
components render the resulting hierarchy for all 21 dashboards.

**Tech Stack:** Svelte 5, TypeScript 6, Vite 8, Vitest 4, committed JSON, Python
3.12 data generators, pytest.

## Global Constraints

- Work only on `feature/dashboard-clarity-comparison` in
  `C:\IT\ClaudeProjects\ExploreBurtonMI\.worktrees\dashboard-clarity`.
- Preserve the current `main` checkout for side-by-side comparison.
- Use semantic theme tokens in shared components; do not add dashboard-specific
  style patches.
- Do not add unsupported school outcomes, Burton commute data, response-time data,
  current crash data, bridge inspection data, or water-quality results.
- Do not alter issue 94 or branch protections.
- Every production behavior change begins with a failing test and an observed RED
  result.
- Preserve strict `web`, `python`, `pin-editor`, and CodeQL checks.
- Keep sources, CSV downloads, accessible chart tables, navigation, and existing
  freshness metadata working.

---

### Task 1: Add the clarity contract and enrichment boundary

**Files:**

- Modify: `src/lib/types.ts`
- Modify: `src/lib/dashboard/infoPanel.ts`
- Create: `src/lib/dashboard/dashboardClarity.ts`
- Modify: `test/infoPanel.test.ts`

**Interfaces:**

- Consumes: generator-owned `RawInfoPanel` values and one `DashboardClarity`
  record.
- Produces: `validateRawInfoPanel(value, id): RawInfoPanel`,
  `validateDashboardClarityMap(value, dashboardIds): Record<string,
  DashboardClarity>`, and `enrichInfoPanel(raw, clarity, lastUpdated): InfoPanel`.

- [ ] **Step 1: Write failing contract tests**

  Extend `test/infoPanel.test.ts` with fixtures and assertions proving that the
  clarity validator rejects missing IDs, invalid status values, more than four
  priority facts, duplicate section headings, unknown stat/chart/table references,
  link actions without an HTTPS/hash URL, and incomplete chart takeaways. Add a
  successful enrichment assertion that IDs are stable even when display labels are
  overridden.

  ```ts
  expect(() => validateDashboardClarityMap({ finances: invalid }, dashboardIds))
    .toThrow(/finances.*context\.status.*current.*historical.*modeled.*planned.*reference/i);

  const panel = enrichInfoPanel(rawPanel, clarity.finances, '2026-06');
  expect(panel.stats.filter((stat) => stat.priority)).toHaveLength(4);
  expect(panel.charts[0]).toMatchObject({
    id: 'revenue-by-source-fy2025-audited-governmental-funds-m',
    takeaway: expect.any(String),
  });
  ```

- [ ] **Step 2: Run the focused test and observe RED**

  Run: `npm test -- test/infoPanel.test.ts`

  Expected: FAIL because the clarity types, validator, and enrichment function do
  not exist.

- [ ] **Step 3: Add the minimal contract**

  Add these exact concepts to `src/lib/types.ts`:

  ```ts
  export type DashboardStatus =
    | 'current' | 'historical' | 'modeled' | 'planned' | 'reference';

  export interface DashboardContext {
    scope: string;
    status: DashboardStatus;
    asOf: string;
  }

  export type DashboardAction =
    | { kind: 'link'; text: string; href: string }
    | { kind: 'none'; text: string };

  export interface InfoSection {
    heading: string;
    stats?: string[];
    charts?: string[];
    tables?: string[];
  }
  ```

  Add optional `id` and `priority` to raw stats, optional `id` and `takeaway` to
  raw charts, and optional `id` to raw tables. The enriched `InfoPanel` requires
  `context`, `headline`, `responsibility`, `action`, and `sections`.

  Define `DashboardClarity` with optional `title`/`subtitle`, required context and
  interpretation fields, `statOverrides` keyed by source stat label,
  `chartOverrides` keyed by source chart title, `tableIds` keyed by source table
  title, and explicit sections. Generate stable lowercase hyphen IDs from the
  original source labels/titles before applying display-copy overrides.

- [ ] **Step 4: Implement strict validation and enrichment**

  Preserve all existing nested raw-data checks. Add exact coverage rules:

  ```ts
  const presentedStats = new Set([
    ...panel.stats.filter((stat) => stat.priority).map((stat) => stat.id),
    ...panel.sections.flatMap((section) => section.stats ?? []),
  ]);
  assertExactlyOnce(presentedStats, panel.stats.map((stat) => stat.id), 'stats');
  assertExactlyOnce(
    panel.sections.flatMap((section) => section.charts ?? []),
    panel.charts.map((chart) => chart.id),
    'charts',
  );
  ```

  Enforce headline maximum 30 words, one summary paragraph maximum 80 words,
  responsibility maximum 55 words, action text maximum 25 words, and takeaway
  maximum 35 words. Reject any chart without a takeaway and any item referenced
  zero times or more than once.

- [ ] **Step 5: Run focused tests and observe GREEN**

  Run: `npm test -- test/infoPanel.test.ts`

  Expected: PASS.

- [ ] **Step 6: Commit the contract**

  ```powershell
  git add src/lib/types.ts src/lib/dashboard/infoPanel.ts `
    src/lib/dashboard/dashboardClarity.ts test/infoPanel.test.ts
  git commit -m "Add validated dashboard clarity contract"
  ```

---

### Task 2: Load and apply clarity metadata once per session

**Files:**

- Modify: `src/lib/dashboard/dashboardData.svelte.ts`
- Modify: `test/dashboardData.test.ts`
- Delete: `public/summaries.json`

**Interfaces:**

- Consumes: `dashboard-clarity.json`, `freshness.json`, and `info-<id>.json`.
- Produces: a fully enriched, strictly validated `InfoPanel` in every
  `DashboardState.panel`.

- [ ] **Step 1: Write failing loader tests**

  Replace summary-overlay fixtures with a complete clarity fixture. Assert that
  metadata is fetched once, clarity copy overrides generator copy, freshness fills
  `lastUpdated`, missing clarity produces a validation error, and direct/retry/loadAll
  behavior remains unchanged.

  ```ts
  expect(fetcher.mock.calls.filter(([url]) => url === 'dashboard-clarity.json'))
    .toHaveLength(1);
  expect(data.state('finances').panel?.headline).toBe(
    'Burton adopted a $67.7 million all-funds plan for FY2026–27.',
  );
  ```

- [ ] **Step 2: Run the focused test and observe RED**

  Run: `npm test -- test/dashboardData.test.ts`

  Expected: FAIL because the loader still requests `summaries.json` and does not
  enrich the panel.

- [ ] **Step 3: Implement the loader pipeline**

  Fetch `dashboard-clarity.json` and `freshness.json` together once. Validate the
  raw panel first, call `enrichInfoPanel`, then call strict `validateInfoPanel` on
  the result. Remove `validateSummaryMap` and delete the obsolete summary file so
  unsupported legacy prose cannot be served accidentally.

- [ ] **Step 4: Run loader and full contract tests**

  Run: `npm test -- test/dashboardData.test.ts test/infoPanel.test.ts`

  Expected: PASS.

- [ ] **Step 5: Commit the loader**

  ```powershell
  git add src/lib/dashboard/dashboardData.svelte.ts test/dashboardData.test.ts `
    public/summaries.json
  git commit -m "Load resident dashboard clarity metadata"
  ```

---

### Task 3: Render the shared resident-first hierarchy

**Files:**

- Create: `src/lib/dashboard/DashboardHeadline.svelte`
- Create: `src/lib/dashboard/DashboardSection.svelte`
- Modify: `src/lib/InfoHeader.svelte`
- Modify: `src/lib/dashboard/DashboardSummary.svelte`
- Modify: `src/lib/dashboard/DashboardChart.svelte`
- Modify: `src/lib/InfoView.svelte`
- Modify: `test/dashboardSections.test.ts`
- Modify: `test/dashboardChart.test.ts`

**Interfaces:**

- `InfoHeader` consumes `context: DashboardContext` and renders scope/status/date
  badges.
- `DashboardHeadline` consumes `headline: string`.
- `DashboardSummary` consumes `summary`, `responsibility`, and `action`.
- `DashboardSection` consumes a resolved section containing `InfoStat[]`,
  `InfoChart[]`, and `InfoTable[]`.

- [ ] **Step 1: Write failing server-render tests**

  Assert semantic output for badges, headline, the three explanation labels, safe
  linked/no-action variants, section headings, priority facts before explanations,
  and chart takeaways before each visualization. Retain the issue 101 light/dark
  contrast assertions.

  ```ts
  expect(body.indexOf('The adopted plan')).toBeLessThan(body.indexOf('Why this matters'));
  expect(body).toContain('City responsibility');
  expect(body).toContain('What you can do');
  expect(body).toContain('Data status: Planned');
  ```

- [ ] **Step 2: Run component tests and observe RED**

  Run: `npm test -- test/dashboardSections.test.ts test/dashboardChart.test.ts`

  Expected: FAIL because the shared hierarchy is not implemented.

- [ ] **Step 3: Implement the components using semantic tokens**

  Render in this order: header/context, headline, up to four priority stats,
  explanation, estimator when present, named evidence sections, explainer,
  methodology, footer, navigation. Use only `--pub-*` and `--civic-*` tokens for
  foregrounds, backgrounds, and borders. Status badges use text labels as well as
  color. The no-action variant renders text, not a disabled link.

- [ ] **Step 4: Add compact phone layout**

  At 390 pixels, keep title/context/headline compact, use a two-column priority
  grid when content fits and one column for long values, and render explanation
  subsections as short stacked rows. Do not hide caveats or actions.

- [ ] **Step 5: Run component tests and observe GREEN**

  Run: `npm test -- test/dashboardSections.test.ts test/dashboardChart.test.ts`

  Expected: PASS.

- [ ] **Step 6: Commit shared rendering**

  ```powershell
  git add src/lib/InfoHeader.svelte src/lib/InfoView.svelte `
    src/lib/dashboard/DashboardHeadline.svelte `
    src/lib/dashboard/DashboardSection.svelte `
    src/lib/dashboard/DashboardSummary.svelte `
    src/lib/dashboard/DashboardChart.svelte `
    test/dashboardSections.test.ts test/dashboardChart.test.ts
  git commit -m "Render resident-first dashboard hierarchy"
  ```

---

### Task 4: Populate and validate all 21 dashboard explanations

**Files:**

- Create: `public/dashboard-clarity.json`
- Modify: `src/lib/dashboards.ts`
- Create: `test/dashboardClarityContent.test.ts`
- Modify: `test/dashboards.test.ts`

**Interfaces:**

- Consumes: exact stat labels, chart titles, table titles, sources, and freshness
  periods from the 21 committed raw panels.
- Produces: one complete clarity record per registered dashboard.

- [ ] **Step 1: Write failing real-content coverage tests**

  Load every raw panel plus the clarity map, enrich it, and assert the strict
  contract. Add explicit regression assertions that the rendered copy does not
  contain these unsupported claims:

  ```ts
  const banned = [
    /where Burton residents work/i,
    /top employers/i,
    /how quickly/i,
    /most calls are medical/i,
    /building permits/i,
    /tap water is safe/i,
    /how each district is doing/i,
  ];
  ```

  Also assert corrected titles `Genesee County Jobs & Industries` and `School
  Districts Serving Burton`, county/network scope near the top, historical status
  for roadway safety, and plan/audit separation for finances.

- [ ] **Step 2: Run the content test and observe RED**

  Run: `npm test -- test/dashboardClarityContent.test.ts`

  Expected: FAIL because `dashboard-clarity.json` is absent.

- [ ] **Step 3: Add the 21 clarity records**

  Use these scope/status anchors exactly:

  | ID | Visible scope | Status/reference period |
  | --- | --- | --- |
  | demographics | Burton | current; ACS 2023 estimates and 2010/2020 Census history |
  | jobs | Genesee County | historical/current mix; 2022 employment and Dec. 2025 unemployment |
  | access | Burton census areas | modeled; 2020 regional-planning estimates |
  | housing | Burton | current estimate; ACS 2023 |
  | zoning | Burton | reference; 2017 map, not parcel-authoritative |
  | schools | Districts serving Burton | historical; district-wide 2023 enrollment |
  | finances | City of Burton | planned/audited mix; FY2026–27 plan and FY2025 actuals |
  | propertytax | Burton parcels | current reference; 2025/2026 rates |
  | fiscalhealth | City of Burton | historical audited actuals; FY2025 |
  | capital | City of Burton | planned; adopted FY2026–27 |
  | health | Burton and Genesee County | modeled/current mix; PLACES 2025 and ACS history |
  | water | Burton water system MI0001010 | historical/current compliance snapshot through 2023 |
  | environment | Genesee County | current annual summary; 2025 monitored days |
  | parks | Parks with land in Burton | reference; source refresh date not published |
  | trails | Trail segments within Burton | reference/planned mix; source refresh date not published |
  | seniorcenter | Burton Senior Center service area | current annual summary; calendar 2025 |
  | broadband | Burton serviceable locations | reported availability; FCC Dec. 31, 2025 and ACS subscription |
  | bridges | Bridges within Burton | historical inspection inventory; NBI 2024 |
  | roads | Federal-aid roads in Burton | historical condition; PASER 2024 |
  | publicsafety | Burton Fire Department | historical annual summary; calendar 2025 plus 2014–2025 trend |
  | roadsafety | Burton crash records | historical; 2014–2018 only |

  Every headline must state a displayed finding, every chart gets one takeaway,
  and every non-priority fact/chart/table is assigned once to a named section.
  Explanation text must state City ownership or reporting limits and provide an
  authoritative action link or an explicit no-direct-action value.

- [ ] **Step 4: Correct menu labels and descriptions**

  Replace the Jobs, Schools, Fire, Housing, and Water descriptions that promise
  unsupported data. Keep registry IDs and hash routes unchanged.

- [ ] **Step 5: Run all web content tests and observe GREEN**

  Run:
  `npm test -- test/dashboardClarityContent.test.ts test/infoPanel.test.ts test/dashboards.test.ts`

  Expected: PASS for all 21 panels.

- [ ] **Step 6: Commit reviewed content**

  ```powershell
  git add public/dashboard-clarity.json src/lib/dashboards.ts `
    test/dashboardClarityContent.test.ts test/dashboards.test.ts
  git commit -m "Clarify all dashboard data and explanations"
  ```

---

### Task 5: Fix data reconciliation defects at their generator sources

**Files:**

- Modify: `tools/extract_trails.py`
- Modify: `tools/test_extract_trails.py`
- Modify: `tools/fetch_fiscalhealth.py`
- Modify: `tools/test_fetch_fiscalhealth.py`
- Modify: `tools/build_seniorcenter.py`
- Modify: `tools/test_build_seniorcenter.py`
- Modify: `tools/build_propertytax.py`
- Modify: `tools/test_build_propertytax.py`
- Modify generated: `public/info-trails.json`
- Modify generated: `public/info-fiscalhealth.json`
- Modify generated: `public/info-seniorcenter.json`
- Modify generated: `public/info-propertytax.json`

**Interfaces:**

- Trails produces separate named-trail rows per status so planned mileage is never
  labeled existing.
- Fiscal Health uses the 2020 Decennial Census population 29,715 when naming that
  source.
- Senior Center program categories reconcile to 28,707 sign-ins.
- Property Tax explicitly explains the 13.43 rounded component sum versus the
  authoritative 13.44 total.

- [ ] **Step 1: Write four failing generator tests**

  ```python
  def test_named_trail_rows_never_mix_existing_and_planned_miles():
      rows = aggregate_named_segments([
          ("Trail A", "Existing", "Shared use", "Paved", 2.0),
          ("Trail A", "Proposed", "Shared use", "Paved", 3.0),
      ])
      assert [(row["status"], row["miles"]) for row in rows] == [
          ("Existing", 2.0), ("Proposed", 3.0),
      ]

  def test_population_matches_named_decennial_source():
      assert fiscal.POPULATION == 29_715

  def test_program_categories_reconcile_to_signins():
      assert sum(value for _, value in senior.PROGRAMS) == senior.PROGRAM_SIGNINS

  def test_city_millage_hint_discloses_rounding():
      assert round(tax.CITY_GENERAL + tax.CITY_POLICE + tax.CITY_FIRE, 2) == 13.43
      assert tax.CITY_TOTAL == 13.44
  ```

- [ ] **Step 2: Run the focused tests and observe RED**

  Run:
  `python -m pytest tools/test_extract_trails.py tools/test_fetch_fiscalhealth.py tools/test_build_seniorcenter.py tools/test_build_propertytax.py -q`

  Expected: four failing reconciliation assertions.

- [ ] **Step 3: Fix trails at the aggregation boundary**

  Aggregate by `(name, status)` with sets of types/surfaces. Compute the longest
  existing trail from existing buckets only. Emit separate table rows for existing,
  under-construction, programmed, and proposed portions.

- [ ] **Step 4: Fix denominator, omitted category, and rounding language**

  Change Fiscal Health population to 29,715 and rename `Pension owed per resident`
  to `Unfunded pension liability per resident`. Add `("Other / uncategorized", 68)`
  to Senior Center program categories. Change the Property Tax hint to
  `ACFR total; displayed components round to 13.43` and remove the unsupported
  “has not raised” conclusion from generated summary copy.

- [ ] **Step 5: Regenerate offline panels and update network-derived snapshots**

  Run `python tools/build_seniorcenter.py` and
  `python tools/build_propertytax.py`. Apply the tested Fiscal Health constant
  calculations to its committed snapshot without calling the state API. Regenerate
  Trails only if its official ArcGIS source is reachable; otherwise update the
  committed table using the same tested aggregation against the committed
  `public/trails.geojson` and verify status totals are unchanged.

- [ ] **Step 6: Run focused tests and observe GREEN**

  Run:
  `python -m pytest tools/test_extract_trails.py tools/test_fetch_fiscalhealth.py tools/test_build_seniorcenter.py tools/test_build_propertytax.py -q`

  Expected: PASS.

- [ ] **Step 7: Compile every modified Python script**

  Run:
  `python -m py_compile tools/extract_trails.py tools/fetch_fiscalhealth.py tools/build_seniorcenter.py tools/build_propertytax.py`

  Expected: exit 0 with no output.

- [ ] **Step 8: Commit generator corrections**

  ```powershell
  git add tools/extract_trails.py tools/test_extract_trails.py `
    tools/fetch_fiscalhealth.py tools/test_fetch_fiscalhealth.py `
    tools/build_seniorcenter.py tools/test_build_seniorcenter.py `
    tools/build_propertytax.py tools/test_build_propertytax.py `
    public/info-trails.json public/info-fiscalhealth.json `
    public/info-seniorcenter.json public/info-propertytax.json
  git commit -m "Reconcile dashboard source data"
  ```

---

### Task 6: Verify current official links and high-risk civic language

**Files:**

- Modify: `public/dashboard-clarity.json`
- Modify: `test/dashboardClarityContent.test.ts`

**Interfaces:**

- Consumes: official City of Burton, EPA, AirNow, zoning, tax, and service pages.
- Produces: authoritative resident actions with no unsupported promises.

- [ ] **Step 1: Check official sources**

  Verify the current City water/Consumer Confidence Report destination, zoning
  contact page, tax lookup/estimator destination, AirNow page, park/trail map,
  Senior Center page, road reporting page, and Fire Department page. Prefer
  first-party government URLs and do not add a link that redirects to a missing or
  unrelated resource.

- [ ] **Step 2: Add a failing URL/copy assertion for each correction**

  Add exact tests for the selected official URL and for nearby caveat text. Run:
  `npm test -- test/dashboardClarityContent.test.ts`

  Expected: FAIL until the clarity file uses the verified destinations.

- [ ] **Step 3: Update actions and rerun the test**

  Expected: PASS. If no current Consumer Confidence Report is published, keep the
  City water and EPA ECHO links and state plainly that the dashboard contains no
  newer annual report.

- [ ] **Step 4: Commit link verification**

  ```powershell
  git add public/dashboard-clarity.json test/dashboardClarityContent.test.ts
  git commit -m "Verify dashboard resident action links"
  ```

---

### Task 7: Run complete protected checks and visual verification

**Files:**

- Modify only if a failing check reveals an in-scope defect, using a new failing
  regression test before the fix.

- [ ] **Step 1: Run web gates**

  Run: `npm run check`

  Expected: zero errors and zero warnings.

  Run: `npm test`

  Expected: all Vitest tests pass.

  Run: `npm run build`

  Expected: production build completes.

- [ ] **Step 2: Run Python and pin-editor gates**

  Run: `python -m pytest pipeline/test tools -q`

  Expected: all pipeline/tools tests pass.

  Run: `python -m pytest apps/pin-editor/test -q`

  Expected: all pin-editor tests pass.

- [ ] **Step 3: Run repository security and CodeQL-equivalent checks**

  Run the repository security test directly and confirm no workflow/source rule is
  weakened. Inspect the PR's CodeQL result after publication; do not dismiss or
  bypass alerts.

- [ ] **Step 4: Verify every route and representative layouts**

  Start the comparison build and open all 21 dashboard hashes. At desktop and
  390-pixel phone width, inspect light and dark modes. Capture representative
  screenshots for Finances, Demographics, Jobs or Schools, Water, Roads, and Fire.
  Confirm the first phone viewport shows title/context/headline and begins key facts.

- [ ] **Step 5: Commit any test-driven verification corrections**

  Use a narrowly scoped commit only if checks exposed a defect. Otherwise do not
  create an empty commit.

---

### Task 8: Launch the old/new comparison and prepare protected publication

**Files:**

- Create: `planning/comparison/dashboard-clarity-review.md`

- [ ] **Step 1: Build current and comparison checkouts**

  Create a clean baseline worktree from `origin/main`, then build it and this
  comparison worktree separately. Do not switch, build from, or stage anything in
  the user's original checkout with its pre-existing planning edits.

- [ ] **Step 2: Start both production previews**

  Launch hidden background previews with logs inside each checkout:

  - current version: `http://127.0.0.1:4173/#finances`
  - comparison version: `http://127.0.0.1:4174/#finances`

  Verify both return HTTP 200 before sharing them.

- [ ] **Step 3: Write the comparison guide**

  Document both URLs, the six representative routes, what changed, how to stop the
  preview processes, all gate results, and any remaining content decisions. Keep the
  comparison guide out of the public application.

- [ ] **Step 4: Commit the completed comparison package**

  Record the verified branch, checks, and comparison URLs in the review guide. A
  later protected merge/handoff may reconcile `planning/STATE.md` from the user's
  current copy; this comparison branch must not overwrite that newer local state.

  ```powershell
  git add -f planning/comparison/dashboard-clarity-review.md
  git commit -m "Document dashboard clarity comparison"
  ```

- [ ] **Step 5: Publish only through a protected pull request when requested**

  Push `feature/dashboard-clarity-comparison`, open a ready PR, and wait for all
  required checks including CodeQL. Do not merge until the City approves the old/new
  comparison.
