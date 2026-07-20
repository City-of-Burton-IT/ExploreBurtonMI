# Dashboard Clarity Redesign

**Date:** 2026-07-20

**Branch:** `feature/dashboard-clarity-comparison`

**Status:** Design checkpoint for user review

## Purpose

Make all 21 Explore Burton dashboards understandable to residents and staff who do
not know municipal terminology, government responsibilities, data-source boundaries,
or the difference between a budget, an audited result, and an operational measure.

The comparison branch must remain independently runnable beside the current `main`
version so the City can compare old and new dashboards before deciding whether to
merge the redesign.

## Success criteria

A resident should be able to answer these questions without opening footnotes:

1. What is the most important finding?
2. Is the information about Burton, the county, a school district, or another owner?
3. How current is it, and is it current, historical, modeled, or planned?
4. What part does the City control?
5. What can the resident do or where can they get authoritative details?

A staff member should also be able to distinguish the source, reference period,
denominator, government owner, and major caveats without reverse-engineering the
chart or generator.

## Approaches considered

### 1. Copy-only revision

Rewrite summaries and labels in the existing JSON shape. This is the smallest change,
but it leaves the flat sequence of stats and charts, keeps caveats in the footer, and
cannot distinguish current plans from audited history.

### 2. Shared clarity model plus content revision — selected

Extend the shared dashboard contract with top-level context, short key takeaways,
prioritized statistics, chart explanations, grouped sections, responsibility, and a
resident action. Update all dashboards through this shared model.

This preserves one renderer and one data-driven system while fixing both wording and
information hierarchy.

### 3. Separate dashboard-v2 application

Build new routes and components while keeping the old dashboards in the same build.
This makes an in-app toggle possible but duplicates the renderer, increases long-term
maintenance, and risks the two versions drifting. The requested branch/worktree
comparison provides isolation without permanent duplication.

## Resident-facing information hierarchy

Each dashboard will render in this order:

1. Group, title, and plain-language subtitle.
2. Visible context badges: geographic scope, data date, and data status.
3. One short headline containing the primary finding.
4. Up to four priority facts.
5. A compact explanation with:
   - why the finding matters;
   - what the City controls or does not control;
   - what the resident can do next.
6. Evidence grouped into named sections such as Current condition, Change over time,
   Comparison, and Detailed data.
7. Methodology, complete tables, sources, downloads, and report-outdated link.

The first phone viewport should show the title, context, headline, and at least the
start of the key facts. A long explanation must not consume the full first screen.

## Shared data contract

The existing `InfoPanel` remains the validation boundary. Add these concepts without
creating dashboard-specific Svelte components:

- `context.scope`: a short label such as `Burton`, `Genesee County`, or
  `Federal-aid roads in Burton`.
- `context.status`: `current`, `historical`, `modeled`, `planned`, or `reference`.
- `context.asOf`: the panel's authoritative reference period. Existing freshness
  overlays may supply it during migration.
- `headline`: one plain-language sentence, normally no more than 30 words.
- `stats[].priority`: whether a statistic belongs in the initial key-facts group.
- `charts[].id` and `tables[].id`: stable local identifiers used by sections.
- `sections[]`: named groups that reference related chart and table identifiers.
- `charts[].takeaway`: one sentence telling the reader what to notice.
- `responsibility`: what Burton controls, what another government controls, or that
  the City is only reporting the measure.
- `action`: a short instruction and link for the resident's next step.

The validator must reject unknown status values, missing required context, duplicate
section headings, references to unknown chart/table IDs, and more than four priority
facts.

During migration, legacy panels may still render through a compatibility adapter.
The branch is complete only when every registered dashboard uses the new fields and
the compatibility path is covered by tests or removed.

## Shared components

- `InfoHeader` renders scope/status/date badges directly below the subtitle.
- A new compact headline component replaces long prose at the top.
- `DashboardSummary` becomes a short Why this matters / City responsibility / What
  you can do block rather than an unrestricted multi-paragraph essay.
- `InfoView` renders priority facts first and named evidence sections afterward.
- `DashboardChart` renders an optional takeaway immediately above the visualization.
- `DashboardFooter` retains full source, notes, downloads, and outdated-data report.

Existing chart implementations, accessible data tables, CSV downloads, navigation,
palette, and semantic theme tokens remain in use.

## Content rules

All dashboard copy must follow these rules:

- Lead with a finding present in the displayed data, not a generic statement about
  why the topic matters.
- Do not claim causation, performance, safety, response speed, or government action
  unless the panel contains evidence for it.
- Put geographic scope and dataset age near the title, not only in notes.
- Use `plan`, `audited actual`, `estimate`, `reported availability`, and `historical`
  explicitly where applicable.
- Define municipal terms at first use: mill, taxable value, Act 51, fund, fund
  balance, PASER, OPEB, and federal-aid road.
- State denominators: residents, households, occupied homes, monitored days,
  road-miles, bridges, district enrollment, or program attendances.
- Identify ownership or responsibility for roads, bridges, schools, regional data,
  and state/federal programs.
- Avoid presenting per-resident government obligations as personal bills.
- Use no more than four initial facts and one primary finding.
- Preserve uncertainty: modeled estimates and rounded components must not imply false
  precision.

## Dashboard-specific corrections

### People and Housing

- **Demographics:** lead with modest population decline, older age profile, income
  context, and homeownership. Remove duplicated population displays and move secondary
  demographic charts into detail sections.
- **Jobs and Employers:** rename to `Genesee County Jobs & Industries` unless Burton
  commute/top-employer data is added. Remove claims about where Burton residents work,
  top employers, working close to home, and Burton's tax base.
- **Affordability and Access:** label the figures as modeled 2020 regional-planning
  estimates. Explain that the income chart counts eight census areas and that rounded
  housing and transportation components may not sum to the displayed combined value.
- **Housing and Growth:** remove the building-permit claim. Emphasize housing age,
  occupancy, ownership, and nominal—not inflation-adjusted—value/rent trends.
- **Zoning:** put `2017 reference map—not authoritative for a parcel` at the top and
  make contacting the zoning division the resident action.
- **Schools:** rename to `School Districts Serving Burton`. Remove the performance
  claim unless outcome measures are added. Clarify that enrollment covers entire
  districts and move unrelated adult educational attainment out of the primary facts.

### Money and Taxes

- **City Finances:** separate FY2026-27 adopted-plan sections from FY2025 audited
  results. Replace the ambiguous 39% budget statement with the exact audited revenue
  measure. Define legacy cost payment and distinguish all-funds, governmental-funds,
  and General Fund figures.
- **Property Taxes:** keep the estimator prominent, define mills and taxable value
  before it, reconcile the displayed 13.43/13.44 rounding, and describe the rate trend
  without an unsupported policy conclusion.
- **Financial Health:** shorten the explanation, rename the pension statistic to
  `Unfunded pension liability per resident`, rename taxable value accurately, and
  correct the population year/source used in the denominator.
- **Capital Projects:** keep funded road projects prominent, explain Act 51 and Other,
  and state that the per-resident figure is a scale comparison—not a household charge.

### Health and Environment

- **Community Health:** lead with the most meaningful Burton/county comparisons and
  label PLACES values as modeled estimates. Keep the ACS uninsured trend separate from
  the current PLACES estimate.
- **Drinking Water:** temper household-level safety claims, explain the 90th-percentile
  lead measure, and identify the resolved health-based violation. Link an official
  current Consumer Confidence Report if one is published; otherwise link the City
  water department and EPA ECHO and state that this branch does not contain a newer
  annual report.
- **Environment:** say `252 of 303 monitored days`, keep Genesee County scope visible,
  and make the live AirNow link the primary action.
- **Parks:** distinguish City and County ownership, add source vintage, and prioritize
  locations, amenities, accessibility, and map access over the acreage total.
- **Trails and Pathways:** fix the mixed-status aggregation before rewriting copy.
  Existing, under-construction, programmed, and proposed mileage must reconcile in
  the facts, charts, and named-trail table.
- **Senior Center:** define program hours, reconcile category sign-ins, explain the
  September attendance anomaly, and clarify eligibility/responsibility for members
  who live outside Burton.

### Infrastructure

- **Broadband Access:** lead with the difference between reported availability and
  actual subscription. Highlight limited fiber availability and clarify that provider
  count is not the number of choices at every address.
- **Bridges and Infrastructure:** identify ownership of the poor-rated bridge and who
  is responsible for repair. De-emphasize construction decade as a proxy for condition.
- **Roads and Pavement:** put the federal-aid-only boundary at the top, add owner or
  maintainer where available, and distinguish funded project sections from an entire
  named road.

### Public Safety

- **Burton Fire and Rescue:** derive the headline from the actual incident-category
  totals. Remove response-speed and medical-call claims unless those datasets are
  added. Explain the separate sources used for the 2025 detail and multi-year history.
- **Roadway Safety:** use a prominent historical status, translate crash-type labels,
  and explain that raw intersection totals reflect traffic exposure as well as risk.

## Data-quality gates

Add automated checks that:

- every registered dashboard has scope, status, date/reference-period, headline,
  responsibility, and an action or explicit `no resident action` value;
- headline and summary lengths stay within agreed limits;
- no dashboard has more than four priority facts;
- chart takeaways and section references are complete;
- totals intended to reconcile do so within an explicit rounding tolerance;
- trails never combine planned mileage into a row labeled fully existing;
- generated dashboard output matches generator constants and tests;
- links, source text, and freshness overlays continue to validate.

Content assertions should protect corrected high-risk language, including the Jobs,
Schools, Fire, Housing, Water, Financial Health, and Trails corrections.

## Comparison environment

The existing checkout remains on `main`. The redesign lives in:

`C:\IT\ClaudeProjects\ExploreBurtonMI\.worktrees\dashboard-clarity`

For review, run production builds from both checkouts on different localhost ports:

- current `main`: port 4173;
- comparison branch: port 4174.

Provide a small comparison index or clear launch commands linking the same dashboard
hash in each version. The comparison does not add a permanent old/new toggle to the
public application.

Capture at least these representative comparisons at desktop and phone width:

- City Finances: mixed plan/audit content;
- Demographics: high-density dashboard;
- Jobs or Schools: scope correction;
- Drinking Water: risk communication;
- Roads: ownership and network boundary;
- Fire and Rescue: corrected operational explanation.

## Verification

Required before the branch is offered for comparison:

- `npm run check` reports zero errors and zero warnings.
- All Vitest tests pass, including real-panel contract and clarity checks.
- Production build succeeds.
- Pipeline/tools pytest remains green.
- Pin-editor pytest remains green.
- Every registered dashboard opens directly by hash.
- Desktop and 390-pixel phone-width visual review covers light and dark modes.
- Current and comparison builds can run simultaneously without changing `main`.
- Independent content review confirms that every headline is supported by displayed
  data and every caveat is placed near the affected measure.

## Out of scope

- Adding new school outcome, Burton commute, current crash, bridge-inspection,
  response-time, or water-quality datasets that are not already available.
- Replacing the chart library, palette, navigation, CSV system, or dashboard registry.
- Publishing or merging the comparison branch before City review.
- Changing branch protections or issue 94.

Missing data will be described honestly rather than fabricated. Where the current
dashboard cannot support its promise, the branch will narrow the title and explanation
to the data that actually exists.
