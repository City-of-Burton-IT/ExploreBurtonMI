# Dashboard clarity old/new review

**Branch:** `feature/dashboard-clarity-comparison`

**Comparison head before this guide:** `918aefe`

**Old baseline:** `origin/main` at `33833ae`

**Prepared:** 2026-07-20

## Open both versions

- Old dashboard: <http://127.0.0.1:4173/#finances>
- New dashboard: <http://127.0.0.1:4174/#finances>

Both production previews are intentionally left running for review. The baseline
was built in a clean detached worktree, not the user's modified main checkout.

Use these representative routes in both versions:

| Review topic | Old | New |
|---|---|---|
| City finances | <http://127.0.0.1:4173/#finances> | <http://127.0.0.1:4174/#finances> |
| Demographics | <http://127.0.0.1:4173/#demographics> | <http://127.0.0.1:4174/#demographics> |
| County jobs | <http://127.0.0.1:4173/#jobs> | <http://127.0.0.1:4174/#jobs> |
| Drinking water | <http://127.0.0.1:4173/#water> | <http://127.0.0.1:4174/#water> |
| Roads | <http://127.0.0.1:4173/#roads> | <http://127.0.0.1:4174/#roads> |
| Fire & rescue | <http://127.0.0.1:4173/#publicsafety> | <http://127.0.0.1:4174/#publicsafety> |

## What changed

Every dashboard now uses the same resident-first reading order:

1. scope, status, and as-of date;
2. one plain-language headline;
3. no more than four priority facts;
4. why the information matters;
5. what the City controls and what it does not;
6. a useful resident action;
7. named detail sections, charts, tables, sources, and caveats.

The shared explanation component uses semantic theme tokens, so the dark-mode
contrast fix applies to every dashboard rather than to individual pages.

All 21 explanations were reviewed for audience, geography, time period, source
boundary, municipal responsibility, and unsupported conclusions. Important scope
corrections include countywide Jobs, district-wide Schools, federal-aid Roads,
historical Road Safety, system-level Water, and plan-versus-audit Finances.

The review also corrected four source-data presentation problems:

- mixed-status trail names now have separate built and planned rows;
- Fiscal Health uses the 2020 Census count of 29,715 for per-resident figures;
- all 28,707 Senior Center program sign-ins reconcile to displayed categories;
- the 13.43 displayed-component versus 13.44 ACFR property-tax rounding is explicit.

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
- `npm test`: 54 files, 484 tests passed;
- `npm run build`: production and PWA build completed;
- pipeline/tools: 249 tests passed;
- pin-editor: 44 tests passed;
- repository security: 12 tests passed;
- modified Python generators: `py_compile` completed, and 21 focused tests passed.

Visual verification covered all 21 dashboard hashes at 1280×720 desktop and
390×844 Android-phone width in light and dark modes:

- every route rendered title, three context items, headline, priority facts, and
  explanation;
- every phone layout began priority facts within the first viewport;
- no route had document-level horizontal overflow;
- no comparison or baseline browser warnings/errors were recorded;
- light-mode measured contrast was at least 7.05:1 for the blue dashboard heading
  and 13.01:1 for explanation text;
- dark-mode measured contrast was at least 4.89:1 for the blue dashboard heading
  and 11.78:1 for explanation text.

Representative captures are in `planning/comparison/screenshots/`:

- `old-finances-desktop-light.png`
- `new-finances-desktop-light.png`
- `new-finances-phone-light.png`
- `new-demographics-phone-light.png`
- `new-jobs-phone-light.png`
- `new-water-phone-dark.png`
- `new-roads-phone-dark.png`
- `new-publicsafety-phone-dark.png`

GitHub's configured CodeQL analysis remains a protected-PR gate; no local check is
being substituted for it. Branch protections were not changed, and issue #94
remains deferred.

## Preview process details

- Baseline server process: PID `49456`, port `4173`
- Comparison server process: PID `53204`, port `4174`
- Logs: `.worktrees/dashboard-baseline/preview.*.log` and
  `.worktrees/dashboard-clarity/preview.*.log`

To stop only these two preview servers after review:

```powershell
Stop-Process -Id 49456,53204
```

If the previews are restarted later, record their new PIDs instead of reusing the
ones above.

## Publication boundary

Do not merge from the comparison worktree. After City approval, push this branch,
open a ready protected pull request, and wait for required web, python, pin-editor,
and CodeQL checks. Reconcile the newer `planning/STATE.md` from the user's main
checkout during that protected handoff; this branch intentionally does not replace
it.
