# Plain-Language Dashboard Context

**Date:** 2026-07-20

**Branch:** `feature/dashboard-clarity-comparison`

**Status:** Approved follow-up to the dashboard clarity redesign

## Purpose

Replace the compact `Scope`, `Status`, and `As of` badges with a context block that
residents and staff can understand without data-governance or municipal-finance
knowledge. Put direct links to the most useful official sources in the same block.

## Approved wording

The shared header will render an `About this data` block with these rows:

- `This covers`: the place, government, network, population, or service represented.
- `Information type`: a plain-language phrase derived from the stored status.
- `Time period`: the year, fiscal year, survey vintage, or reporting period.
- `Official sources`: one to three curated links to the primary public sources.

Status values will be translated consistently:

| Stored value | Resident-facing phrase |
| --- | --- |
| `current` | Latest available data |
| `historical` | Historical record |
| `modeled` | Model-based estimate |
| `planned` | Adopted plan |
| `reference` | Reference information |

The stored status values remain unchanged so validation, filtering, and future data
updates retain a stable vocabulary.

## Source-link rules

- Source links are curated separately from general dashboard links. Related maps,
  actions, colleges, and contact pages do not automatically become data sources.
- Each dashboard may show one to three links. Link text names the source or document,
  rather than using generic wording such as `Learn more`.
- The City Finances and Capital Projects dashboards link to the stable City of Burton
  `Budgets & Resources` page, which currently lists the 2026-27 Approved Budget.
- State, federal, county, and other authoritative sources remain visibly named so a
  resident can tell who produced the data.
- Only `https` links are allowed in this row. In-app navigation remains in the existing
  resident-action and footer areas.
- If the underlying records are not exposed as a public dataset, the dashboard may
  link to the responsible City department while the full footer citation continues to
  say that the figures come from internal City records.
- The complete source description, notes, report-outdated action, and secondary links
  remain in the footer.

## Shared implementation

`DashboardContext` gains an optional `sourceLinks` array using the existing
`InfoLink` shape. The clarity validator checks link text, `https` URLs, duplicate
URLs, and the three-link limit. All resident-facing dashboards will provide at least
one curated source link where an authoritative public page exists.

`InfoHeader` remains the single renderer. It changes from three pills to a compact
semantic description list and renders source links from `context.sourceLinks`.
Status wording comes from a small shared formatter so all five values are covered by
unit tests.

The block uses the existing semantic surface, border, ink, muted-text, and link-color
tokens. At phone width the rows stack naturally, source links wrap, and the block must
leave the dashboard headline and start of the key facts reachable without excessive
scrolling.

## Accessibility and verification

- The block has a visible `About this data` heading and a stable accessible label.
- Labels and values use semantic `dl`, `dt`, and `dd` markup.
- External links open in a new tab with `noopener noreferrer`.
- Text and links meet WCAG AA contrast in light and dark themes.
- Tests cover all status phrases, source rendering, safe URL validation, and the
  resident-facing labels.
- The comparison build is checked at desktop and 390-pixel Android phone width in
  light and dark modes before it is committed.

## Out of scope

- Removing the detailed source footer.
- Turning every related dashboard link into a source link.
- Adding unpublished datasets or claiming that internal records are publicly
  downloadable.
- Changing issue #94, branch protections, publishing, or merging.
