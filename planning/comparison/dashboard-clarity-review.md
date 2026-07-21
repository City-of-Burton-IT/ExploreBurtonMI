# Dashboard clarity old/new review

**Branch:** `feature/dashboard-clarity-comparison`

**Comparison head before this guide:** `6be939f`

**Old baseline:** `origin/main` at `33833ae`

**Prepared:** 2026-07-21

## Open both versions

- Old dashboard: <http://127.0.0.1:4173/#finances>
- New dashboard: <http://127.0.0.1:43820/?unlock=burton-preview#finances>

Both production previews are intentionally left running for review. The baseline
was built in a clean detached worktree, not the user's modified main checkout.

Use these representative routes in both versions:

| Review topic | Old | New |
|---|---|---|
| City finances | <http://127.0.0.1:4173/#finances> | <http://127.0.0.1:43820/?unlock=burton-preview#finances> |
| Property taxes | <http://127.0.0.1:4173/#propertytax> | <http://127.0.0.1:43820/?unlock=burton-preview#propertytax> |
| Demographics | <http://127.0.0.1:4173/#demographics> | <http://127.0.0.1:43820/?unlock=burton-preview#demographics> |
| County jobs | <http://127.0.0.1:4173/#jobs> | <http://127.0.0.1:43820/?unlock=burton-preview#jobs> |
| Drinking water | <http://127.0.0.1:4173/#water> | <http://127.0.0.1:43820/?unlock=burton-preview#water> |
| Roads | <http://127.0.0.1:4173/#roads> | <http://127.0.0.1:43820/?unlock=burton-preview#roads> |
| Fire & rescue | <http://127.0.0.1:4173/#publicsafety> | <http://127.0.0.1:43820/?unlock=burton-preview#publicsafety> |

## What changed

Every dashboard now uses the same resident-first reading order:

1. an `About this data` block explaining what the dashboard covers, its information
   type, time period, and primary official sources;
2. one plain-language headline;
3. no more than four priority facts;
4. why the information matters;
5. what the City controls and what it does not;
6. a useful resident action;
7. named detail sections, charts, tables, sources, and caveats.

The shared explanation component uses semantic theme tokens, so the dark-mode
contrast fix applies to every dashboard rather than to individual pages.

The former `Scope`, `Status`, and `As of` pills are now full plain-language rows:

- `This covers`
- `Information type`
- `Time period`
- `Official sources`

Stored status values are translated for residents as `Latest available data`,
`Historical record`, `Model-based estimate`, `Adopted plan`, or
`Reference information`. Each dashboard has one to three curated source links rather
than automatically repeating every related footer link. City Finances and Capital
Projects link directly to the City's stable Budgets & Resources page, which lists the
2026-27 Approved Budget; complete source descriptions and secondary resources remain
in the footer.

All 21 explanations were reviewed for audience, geography, time period, source
boundary, municipal responsibility, and unsupported conclusions. Important scope
corrections include countywide Jobs, district-wide Schools, federal-aid Roads,
historical Road Safety, system-level Water, and plan-versus-audit Finances.

The review also corrected four source-data presentation problems:

- mixed-status trail names now have separate built and planned rows;
- Fiscal Health uses the 2020 Census count of 29,715 for per-resident figures;
- all 28,707 Senior Center program sign-ins reconcile to displayed categories;
- the provisional 13.4 City display, exact 13.44 supporting rate, and separate
  13.2948 Approved Budget service-line total are explicit.

Property Taxes now begins with a provisional 13.4-mill City rate, backed by the last
supported exact 13.44 rate, while the current certified L-4029 is pending. The
calculator uses 13.44 and estimates $672 per year at $50,000 taxable value. It shows
the FY2026-27 Approved Budget's General 4.0000, aggregate Police 8.3159, and Fire
0.9789 lines as budget references. Because those total 13.2948, the table displays a
separate 0.1452-mill unassigned difference rather than allocating it to a service
without the L-4029. The historical series and 2025 complete-bill rates remain visibly
dated and separate.

Resident actions now use verified current destinations for Burton zoning, the
2025 water-quality report, the Senior Activity Center, Burton-specific AirNow
conditions, and Burton's Citizen Request Center for road issues. Fire retains the
safer emergency instruction: call 911.

## What to compare

For each representative route, answer these questions:

- Can a resident identify the geographic scope and date without reading notes?
- Is the main conclusion understandable without municipal-finance terminology?
- Do the first four facts answer the most likely resident or staff question?
- Does “City responsibility” separate City decisions from County, State, Federal,
  school-district, or household responsibilities?
- Is “What you can do” specific and useful?
- Are the later charts and tables easier to interpret because each has a takeaway?

## Verification evidence

Fresh local gates on the comparison head:

- `npm run check`: 0 errors, 0 warnings;
- `npm test`: 56 files, 509 tests passed;
- `npm run build`: production and PWA build completed with the three existing
  ineffective dynamic-import warnings and no build errors;
- pipeline/tools: 251 tests passed;
- pin-editor: 44 tests passed;
- repository security: 12 tests passed;
- modified Python generators: `py_compile` completed for `build_propertytax.py`,
  `build_seniorcenter.py`, `extract_trails.py`, and `fetch_fiscalhealth.py`; their
  tests are included in the 250-test pipeline/tools result.

The full redesign review covered all 21 dashboard hashes at 1280×720 desktop and
390×844 Android-phone width in light and dark modes. After the shared context block
changed, targeted current-head verification repeated both sizes and both themes for
City Finances and Genesee County Jobs & Industries:

- both routes rendered the four context rows, plain-language status, headline,
  priority facts, and primary source links;
- the phone layouts began key facts in or immediately below the first viewport;
- neither route had horizontal overflow at desktop or phone width;
- no comparison or baseline browser warnings/errors were recorded;
- light-mode measured contrast was at least 7.05:1 for the blue dashboard heading
  and 13.01:1 for explanation text;
- dark-mode measured contrast was at least 4.89:1 for the blue dashboard heading
  and 11.78:1 for explanation text;
- context-block contrast was 13.01:1 for values, 6.23:1 for labels, and 4.61:1 for
  links in light mode; dark mode measured 11.78:1, 6.72:1, and 6.12:1 respectively.

Final current-head Property Taxes verification used a 390×844 viewport in light and
dark modes. The browser's non-overlay scrollbar left a 375px effective content
width. In both themes, the document, header, and header scroll widths were all
exactly 375px; 4.0000, 8.3159, 0.9789, 0.1452, and the 13.4 total each occupied one
text line with `white-space: nowrap`; the reconciled table stayed inside its card;
and the browser recorded no warnings or errors. The comparison production bundle
was rebuilt immediately before this check and verified by its `index-ChwDRbsi.js`
fingerprint. A clean port was used
because the earlier preview origin retained a stale service-worker asset cache.

Representative captures are in `planning/comparison/screenshots/`:

- `old-finances-desktop-light.png`
- `old-propertytax-desktop-light.png`
- `new-finances-desktop-light.png`
- `new-finances-phone-light.png`
- `new-finances-phone-dark.png`
- `new-propertytax-desktop-light.png`
- `new-propertytax-phone-light.png`
- `new-propertytax-phone-dark.png`
- `new-demographics-phone-light.png`
- `new-jobs-phone-light.png`
- `new-water-phone-dark.png`
- `new-roads-phone-dark.png`
- `new-publicsafety-phone-dark.png`

GitHub's configured CodeQL analysis remains a protected-PR gate; no local check is
being substituted for it. Branch protections were not changed, and issue #94
remains deferred.

## Preview process details

- Baseline server process: PID `60876`, port `4173`
- Comparison server processes: PIDs `10736` and `21612`, port `43820`
- Baseline logs: `.worktrees/dashboard-baseline/preview.20260721.*.log`

To stop only these two preview servers after review:

```powershell
Stop-Process -Id 60876,10736,21612
```

If the previews are restarted later, record their new PIDs instead of reusing the
ones above.

## Publication boundary

Do not merge from the comparison worktree. After City approval, push this branch,
open a ready protected pull request, and wait for required web, python, pin-editor,
and CodeQL checks. Reconcile the newer `planning/STATE.md` from the user's main
checkout during that protected handoff; this branch intentionally does not replace
it.
