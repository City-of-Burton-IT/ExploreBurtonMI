# Property Tax City Millage Breakdown Implementation Plan

> **For implementation:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Use superpowers:subagent-driven-development only if the user explicitly authorizes delegation. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give residents a personalized, exact breakdown of the FY2026-27 City of Burton levy while keeping the separately dated 2025 complete-bill estimate understandable and mathematically honest.

**Architecture:** Extend the property-tax estimator data contract with authoritative City levy components and two explicit source periods. Keep millage arithmetic in a small pure TypeScript module, generate all Burton constants and resident copy from `tools/build_propertytax.py`, and render the City and complete-bill results as separate semantic sections in the shared `TaxEstimator` component.

**Tech Stack:** Svelte 5, TypeScript 6, Vitest server rendering, Python 3.12/pytest, committed JSON, Vite/PWA, Capacitor Android webview.

## Global Constraints

- Work only on `feature/dashboard-clarity-comparison` in `.worktrees/dashboard-clarity`.
- Use Burton's FY2026-27 Approved Budget for General Operating `4.0000`, Police Levies `8.3159`, Fire Levy `0.9789`, City total `13.2948`, and voter-approved Police and Fire subtotal `9.2948` mills.
- Label General Operating `City Charter`; label Police and Fire `Voter approved`.
- Keep the complete-bill estimate explicitly labeled `2025 published rates`; never subtract the FY2026-27 City amount from that 2025 total or calculate a mixed-vintage City percentage.
- Calculate tax as `taxable value x mills / 1,000`, retaining full precision until display rounding.
- Use semantic theme tokens and preserve WCAG AA contrast in light and dark modes.
- Preserve strict `web`, `python`, `pin-editor`, and CodeQL checks.
- Preserve issue #94's deferral and all branch protections.
- Do not add parcel lookup, collect an address, publish preliminary 2026 overlapping-authority rates, push, merge, or publish the comparison.

## File Structure

- `src/lib/propertyTax.ts`: pure taxable-value normalization, millage-to-dollar, and levy-total calculations.
- `src/lib/types.ts`: typed City levy and estimator JSON contract.
- `src/lib/dashboard/infoPanel.ts`: runtime validation at the committed-JSON boundary.
- `tools/build_propertytax.py`: authoritative Burton rates, source periods, resident copy, and JSON generation.
- `public/info-propertytax.json`: generated Property Taxes panel data.
- `src/lib/TaxEstimator.svelte`: accessible controls, City levy table, complete-bill result, rounding disclosure, and responsive styles.
- `public/dashboard-clarity.json`: Property Taxes context, headline, explanation, priority facts, takeaways, and official sources.
- `public/freshness.json`: latest Property Taxes panel refresh date.
- `test/propertyTax.test.ts`: pure arithmetic and invalid-input tests.
- `test/taxEstimator.test.ts`: server-rendered resident wording and semantic-table tests.
- `test/infoPanel.test.ts`: estimator contract validation tests.
- `test/dashboardClarityContent.test.ts`: committed rate, vintage, copy, and source-link assertions.
- `tools/test_build_propertytax.py`: generator constants, reconciliation, and output-contract tests.
- `planning/comparison/dashboard-clarity-review.md`: old/new review notes and fresh verification evidence.
- `planning/comparison/screenshots/new-propertytax-*.png`: representative comparison captures.

---

### Task 1: Pure property-tax calculations

**Files:**

- Create: `src/lib/propertyTax.ts`
- Create: `test/propertyTax.test.ts`

**Interfaces:**

- Consumes: `EstimatorCityLevy` from `src/lib/types.ts` after Task 2; use a local structural type in this task so the arithmetic module remains independently testable before the contract lands.
- Produces: `normaliseTaxableValue(value: number | null | undefined): number`, `taxForMills(taxableValue: number | null | undefined, mills: number): number`, `sumLevyMills(levies: readonly MillageLevy[], voterApprovedOnly?: boolean): number`, and `roundedCents(value: number): number`.

- [ ] **Step 1: Write the failing arithmetic tests**

Create `test/propertyTax.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import {
  normaliseTaxableValue,
  roundedCents,
  sumLevyMills,
  taxForMills,
} from '../src/lib/propertyTax';

const levies = [
  { mills: 4, voterApproved: false },
  { mills: 8.3159, voterApproved: true },
  { mills: 0.9789, voterApproved: true },
];

describe('property-tax calculations', () => {
  it('calculates City service amounts without dropping mill precision', () => {
    expect(taxForMills(50_000, 4)).toBe(200);
    expect(taxForMills(50_000, 8.3159)).toBeCloseTo(415.795, 6);
    expect(taxForMills(50_000, 0.9789)).toBeCloseTo(48.945, 6);
    expect(taxForMills(50_000, sumLevyMills(levies))).toBeCloseTo(664.74, 6);
  });

  it('totals only voter-approved levies when requested', () => {
    expect(sumLevyMills(levies)).toBeCloseTo(13.2948, 6);
    expect(sumLevyMills(levies, true)).toBeCloseTo(9.2948, 6);
    expect(taxForMills(50_000, sumLevyMills(levies, true))).toBeCloseTo(464.74, 6);
  });

  it('normalises blank, negative, and non-finite taxable values to zero', () => {
    expect(normaliseTaxableValue(undefined)).toBe(0);
    expect(normaliseTaxableValue(null)).toBe(0);
    expect(normaliseTaxableValue(-1)).toBe(0);
    expect(normaliseTaxableValue(Number.NaN)).toBe(0);
    expect(normaliseTaxableValue(Number.POSITIVE_INFINITY)).toBe(0);
  });

  it('rounds display values to integer cents', () => {
    expect(roundedCents(415.795)).toBe(41_580);
    expect(roundedCents(48.945)).toBe(4_895);
    expect(roundedCents(664.74)).toBe(66_474);
  });
});
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `npm test -- test/propertyTax.test.ts`

Expected: FAIL because `src/lib/propertyTax.ts` does not exist.

- [ ] **Step 3: Implement the pure functions**

Create `src/lib/propertyTax.ts`:

```ts
export interface MillageLevy {
  mills: number;
  voterApproved: boolean;
}

export function normaliseTaxableValue(value: number | null | undefined): number {
  return typeof value === 'number' && Number.isFinite(value) && value > 0 ? value : 0;
}

export function taxForMills(
  taxableValue: number | null | undefined,
  mills: number,
): number {
  return (normaliseTaxableValue(taxableValue) * mills) / 1_000;
}

export function sumLevyMills(
  levies: readonly MillageLevy[],
  voterApprovedOnly = false,
): number {
  return levies
    .filter((levy) => !voterApprovedOnly || levy.voterApproved)
    .reduce((sum, levy) => sum + levy.mills, 0);
}

export function roundedCents(value: number): number {
  return Math.round((value + Number.EPSILON) * 100);
}
```

- [ ] **Step 4: Run the focused test and verify GREEN**

Run: `npm test -- test/propertyTax.test.ts`

Expected: 4 tests PASS.

- [ ] **Step 5: Commit the arithmetic boundary**

```powershell
git add src/lib/propertyTax.ts test/propertyTax.test.ts
git commit -m "Add precise property tax calculations"
```

---

### Task 2: Authoritative City levy contract and generated data

**Files:**

- Modify: `src/lib/types.ts`
- Modify: `src/lib/dashboard/infoPanel.ts`
- Modify: `test/infoPanel.test.ts`
- Modify: `tools/build_propertytax.py`
- Modify: `tools/test_build_propertytax.py`
- Regenerate: `public/info-propertytax.json`
- Modify: `public/freshness.json`

**Interfaces:**

- Consumes: `sumLevyMills` semantics from Task 1 and the existing `EstimatorDistrict` contract.
- Produces: `EstimatorCityLevy`, the expanded `InfoEstimator`, validated committed JSON, `CITY_LEVIES`, `CITY_TOTAL`, `VOTER_APPROVED_TOTAL`, `CITY_RATE_PERIOD`, and `FULL_BILL_RATE_PERIOD`.

- [ ] **Step 1: Replace the outdated Python assertions with failing FY2026-27 assertions**

In `tools/test_build_propertytax.py`, replace the old City rounding tests and add output-contract coverage:

```python
def test_fy2026_27_city_levies_match_adopted_budget():
    assert pt.CITY_GENERAL == 4.0000
    assert pt.CITY_POLICE == 8.3159
    assert pt.CITY_FIRE == 0.9789
    assert pt.CITY_TOTAL == 13.2948
    assert pt.VOTER_APPROVED_TOTAL == 9.2948


def test_city_levies_have_unique_ids_and_exact_authorization():
    assert len({levy["id"] for levy in pt.CITY_LEVIES}) == 3
    assert [levy["authorization"] for levy in pt.CITY_LEVIES] == [
        "City Charter",
        "Voter approved",
        "Voter approved",
    ]
    assert sum(levy["mills"] for levy in pt.CITY_LEVIES) == pt.CITY_TOTAL
    assert sum(
        levy["mills"] for levy in pt.CITY_LEVIES if levy["voterApproved"]
    ) == pt.VOTER_APPROVED_TOTAL


def test_estimator_separates_city_and_complete_bill_periods():
    estimator = pt.build_estimator()
    assert estimator["cityRatePeriod"] == "FY2026-27 adopted levy"
    assert estimator["fullBillRatePeriod"] == "2025 published rates"
    assert estimator["cityMills"] == 13.2948
    assert estimator["cityLevies"] == pt.CITY_LEVIES
    assert "countyMills" not in estimator


def test_2025_full_bill_breakdown_uses_2025_city_rate():
    assert pt.PUBLISHED_2025_CITY_TOTAL == 13.44
    uniform = (
        pt.PUBLISHED_2025_CITY_TOTAL
        + pt.COUNTY
        + pt.MOTT
        + pt.ISD
        + pt.MTA
        + pt.AIRPORT
    )
    schools_set = round(pt.HOMESTEAD_TOTAL - uniform, 2)
    assert abs((uniform + schools_set) - pt.HOMESTEAD_TOTAL) < 0.001
```

Add a small `build_estimator() -> dict` helper so tests can verify the dated estimator contract directly. Keep the existing `main()` orchestration and use the helper when assembling the panel.

- [ ] **Step 2: Add failing TypeScript contract-validation tests**

Replace the `completePanel.estimator` fixture in `test/infoPanel.test.ts` with:

```ts
estimator: {
  cityRatePeriod: 'FY2026-27 adopted levy',
  fullBillRatePeriod: '2025 published rates',
  cityMills: 13.2948,
  cityLevies: [
    {
      id: 'general-operating',
      service: 'General city operations',
      authorization: 'City Charter',
      description: 'Supports general municipal services.',
      mills: 4,
      voterApproved: false,
    },
    {
      id: 'police',
      service: 'Police services',
      authorization: 'Voter approved',
      description: 'Supports Police Department operations.',
      mills: 8.3159,
      voterApproved: true,
    },
    {
      id: 'fire',
      service: 'Fire services',
      authorization: 'Voter approved',
      description: 'Supports Fire Department operations.',
      mills: 0.9789,
      voterApproved: true,
    },
  ],
  districts: [{ name: 'Example district', homestead: 32, nonHomestead: 50 }],
},
```

Add these rejection tests:

```ts
it.each([
  ['negative mills', { mills: -1 }, /cityLevies\[0\]\.mills.*non-negative/i],
  ['invalid voter flag', { voterApproved: 'yes' }, /cityLevies\[0\]\.voterApproved.*boolean/i],
  ['missing authorization', { authorization: '' }, /cityLevies\[0\]\.authorization/i],
] as const)('rejects %s in City levy data', (_label, change, expected) => {
  const levy = { ...completePanel.estimator.cityLevies[0], ...change };
  const invalid = {
    ...completePanel,
    estimator: { ...completePanel.estimator, cityLevies: [levy] },
  };
  expect(() => validateRawInfoPanel(invalid, 'propertytax')).toThrow(expected);
});

it('rejects duplicate levy ids', () => {
  const levy = completePanel.estimator.cityLevies[0];
  const invalid = {
    ...completePanel,
    estimator: { ...completePanel.estimator, cityLevies: [levy, { ...levy }] },
  };
  expect(() => validateRawInfoPanel(invalid, 'propertytax')).toThrow(
    /cityLevies\[1\]\.id.*duplicate/i,
  );
});

it('rejects a City total that does not equal its levy components', () => {
  const invalid = {
    ...completePanel,
    estimator: { ...completePanel.estimator, cityMills: 99 },
  };
  expect(() => validateRawInfoPanel(invalid, 'propertytax')).toThrow(
    /cityMills.*sum of cityLevies/i,
  );
});
```

- [ ] **Step 3: Run Python and TypeScript tests and verify RED**

Run:

```powershell
& 'C:\IT\ClaudeProjects\ExploreBurtonMI\pipeline\.venv\Scripts\python.exe' -m pytest tools/test_build_propertytax.py -q
npm test -- test/infoPanel.test.ts
```

Expected: Python fails on old constants and missing `build_estimator`; Vitest fails on the missing estimator fields and validators.

- [ ] **Step 4: Add the estimator types**

In `src/lib/types.ts`, add and export:

```ts
export interface EstimatorCityLevy {
  id: string;
  service: string;
  authorization: string;
  description: string;
  mills: number;
  voterApproved: boolean;
}

export interface InfoEstimator {
  cityRatePeriod: string;
  fullBillRatePeriod: string;
  cityMills: number;
  cityLevies: EstimatorCityLevy[];
  districts: EstimatorDistrict[];
}
```

Remove `countyMills` from `InfoEstimator`; the UI must not use a 2025 County amount to create a mixed-vintage result split.

- [ ] **Step 5: Add strict runtime validation**

Import and re-export `EstimatorCityLevy` in `src/lib/dashboard/infoPanel.ts`. Add these helpers:

```ts
function nonNegativeNumber(value: unknown, context: string, path: string): number {
  const number = numberValue(value, context, path);
  if (number < 0) fail(context, path, 'expected a non-negative number');
  return number;
}

function booleanValue(value: unknown, context: string, path: string): boolean {
  if (typeof value !== 'boolean') fail(context, path, 'expected a boolean');
  return value;
}
```

Replace `validateEstimator` with validation that:

```ts
const estimator = objectValue(value, context, path) as Partial<InfoEstimator>;
stringValue(estimator.cityRatePeriod, context, `${path}.cityRatePeriod`);
stringValue(estimator.fullBillRatePeriod, context, `${path}.fullBillRatePeriod`);
const cityMills = nonNegativeNumber(estimator.cityMills, context, `${path}.cityMills`);
const cityLevies = arrayValue(estimator.cityLevies, context, `${path}.cityLevies`);
if (cityLevies.length === 0) fail(context, `${path}.cityLevies`, 'expected at least one levy');
cityLevies.forEach((item, index) => {
  const levyPath = `${path}.cityLevies[${index}]`;
  const levy = objectValue(item, context, levyPath) as Partial<EstimatorCityLevy>;
  stringValue(levy.id, context, `${levyPath}.id`);
  stringValue(levy.service, context, `${levyPath}.service`);
  stringValue(levy.authorization, context, `${levyPath}.authorization`);
  stringValue(levy.description, context, `${levyPath}.description`);
  nonNegativeNumber(levy.mills, context, `${levyPath}.mills`);
  booleanValue(levy.voterApproved, context, `${levyPath}.voterApproved`);
});
uniqueObjectField(cityLevies, 'id', context, `${path}.cityLevies`);
const levyTotal = cityLevies.reduce(
  (sum, item) => sum + (item as EstimatorCityLevy).mills,
  0,
);
if (Math.abs(levyTotal - cityMills) > 0.0000001) {
  fail(context, `${path}.cityMills`, 'expected the sum of cityLevies');
}
```

Then retain the existing district validation, changing its numeric fields to `nonNegativeNumber`.

- [ ] **Step 6: Replace outdated generator constants and resident copy**

In `tools/build_propertytax.py`, use:

```python
CITY_RATE_PERIOD = "FY2026-27 adopted levy"
FULL_BILL_RATE_PERIOD = "2025 published rates"

CITY_GENERAL = 4.0000
CITY_POLICE = 8.3159
CITY_FIRE = 0.9789
CITY_TOTAL = round(CITY_GENERAL + CITY_POLICE + CITY_FIRE, 4)
VOTER_APPROVED_TOTAL = round(CITY_POLICE + CITY_FIRE, 4)
PUBLISHED_2025_CITY_TOTAL = 13.44

CITY_LEVIES = [
    {
        "id": "general-operating",
        "service": "General city operations",
        "authorization": "City Charter",
        "description": "Supports general municipal services provided by the City.",
        "mills": CITY_GENERAL,
        "voterApproved": False,
    },
    {
        "id": "police",
        "service": "Police services",
        "authorization": "Voter approved",
        "description": "Supports Police Department staffing and operations.",
        "mills": CITY_POLICE,
        "voterApproved": True,
    },
    {
        "id": "fire",
        "service": "Fire services",
        "authorization": "Voter approved",
        "description": "Supports Fire Department services and operations.",
        "mills": CITY_FIRE,
        "voterApproved": True,
    },
]
```

Build the 2025 full-bill chart with `PUBLISHED_2025_CITY_TOTAL`, not `CITY_TOTAL`. Give it the title `Where a typical 2025 homestead tax bill went (mills)`. Keep the historical City chart explicitly titled `Reported City millage, FY2017-FY2026` so it is not presented as the new adopted levy.

Generate this estimator shape from a dedicated helper:

```python
def build_estimator() -> dict:
    return {
        "cityRatePeriod": CITY_RATE_PERIOD,
        "fullBillRatePeriod": FULL_BILL_RATE_PERIOD,
        "cityMills": CITY_TOTAL,
        "cityLevies": CITY_LEVIES,
        "districts": [
            {"name": name, "homestead": hs, "nonHomestead": nhs}
            for name, hs, nhs in DISTRICT_RATES
        ],
    }
```

In the existing `main()` function, replace the inline estimator dictionary with `estimator = build_estimator()` before assembling the panel.

Replace the mixed-vintage share statistic with:

```python
{
    "label": "Voter-approved City millages",
    "value": f"{VOTER_APPROVED_TOTAL:.4f} mills",
    "hint": "Police and Fire levies approved by Burton voters",
}
```

Keep `City of Burton's rate`, but display `13.2948 mills` with the hint `General 4.0000 + Police 8.3159 + Fire 0.9789`. Generate the $50,000 City example as approximately `$665/yr` from the FY2026-27 total. Rewrite summary, source, and notes so the adopted City levy and 2025 complete-bill totals are always named with their own periods.

Use these exact generated blocks in `main()` alongside `estimator = build_estimator()`:

```python
city_dollars = CITY_TOTAL * EXAMPLE_TAXABLE / 1000
lo_total = round(DISTRICT_HOMESTEAD[0][1] * EXAMPLE_TAXABLE / 1000)
hi_total = round(DISTRICT_HOMESTEAD[-1][1] * EXAMPLE_TAXABLE / 1000)

stats = [
    {
        "label": "City of Burton's rate",
        "value": f"{CITY_TOTAL:.4f} mills",
        "hint": (
            f"General {CITY_GENERAL:.4f} + Police {CITY_POLICE:.4f} "
            f"+ Fire {CITY_FIRE:.4f}"
        ),
    },
    {
        "label": "Voter-approved City millages",
        "value": f"{VOTER_APPROVED_TOTAL:.4f} mills",
        "hint": "Police and Fire levies approved by Burton voters",
    },
    {
        "label": "City tax on a $50k-taxable home",
        "value": f"${round(city_dollars):,}/yr",
        "hint": "FY2026-27 adopted City levy; about a $100,000 market-value home",
    },
    {
        "label": "School districts in Burton",
        "value": "7",
        "hint": "2025 complete-bill rates vary by district",
    },
]

summary = {
    "heading": "What this means for you",
    "body": [
        (
            f"Burton's FY2026-27 adopted City levy is {CITY_TOTAL:.4f} mills. "
            f"Of that, {VOTER_APPROVED_TOTAL:.4f} mills are voter-approved Police "
            f"and Fire levies; {CITY_GENERAL:.4f} mills support general City operations "
            "under the City Charter."
        ),
        (
            f"At ${EXAMPLE_TAXABLE:,} of taxable value, the City portion is about "
            f"${round(city_dollars):,} a year. The latest complete published bill rates "
            f"are from 2025 and range from about ${lo_total:,} to ${hi_total:,} at that "
            "taxable value, depending on school district."
        ),
        (
            "County, schools, the State, ISD, college, transit, airport, and other "
            "authorities receive their own portions; those amounts do not become City revenue."
        ),
    ],
}

source = (
    "City of Burton FY2026-27 Approved Budget, Tax Millage; Michigan Department "
    "of Treasury, 2025 Total Property Tax Rates in Michigan; and City of Burton "
    "audited financial statements for the historical rate series."
)

notes = [
    (
        "One mill is $1 per $1,000 of taxable value. Taxable value is shown on the "
        "assessment notice and is not the same as market value."
    ),
    (
        "The City service table uses the FY2026-27 adopted City levy. The complete-bill "
        "district estimate and authority chart use 2025 published rates; the two periods "
        "are shown separately and are not subtracted from one another."
    ),
    (
        "Estimate only. Actual bills can differ because of exact parcel values, exemptions, "
        "special assessments, administrative fees, and a possible Downtown Development "
        "Authority levy for affected parcels. Not a tax statement."
    ),
]
```

Add these footer links:

```python
{"text": "City of Burton 2026-27 Approved Budget",
 "href": "https://www.burtonmi.gov/government/controller_s_office/budgets.php"},
{"text": "Genesee County L-4029 information",
 "href": "https://www.geneseecountymi.gov/departments/equalization/l-4029_information.php"},
{"text": "Michigan property-tax estimator",
 "href": "https://www.michigan.gov/taxes/property/estimator"},
{"text": "City Finances dashboard", "href": "#finances"},
```

End the generator with this reporting boundary after the existing panel dictionary is written:

```python
    write_json(OUT, panel)
    print(f"Wrote {OUT}")
    print(
        f"  FY2026-27 City {CITY_TOTAL:.4f} mills; "
        f"voter-approved {VOTER_APPROVED_TOTAL:.4f} mills"
    )
    print(f"  2025 complete-bill districts: {len(DISTRICT_RATES)}")
    return 0
```

- [ ] **Step 7: Regenerate the committed panel and freshness date**

Run:

```powershell
& 'C:\IT\ClaudeProjects\ExploreBurtonMI\pipeline\.venv\Scripts\python.exe' tools/build_propertytax.py
```

Set `public/freshness.json` propertytax to `2026-06`, the month the FY2026-27 Approved Budget was adopted and published.

- [ ] **Step 8: Run focused tests and compile the generator**

Run:

```powershell
& 'C:\IT\ClaudeProjects\ExploreBurtonMI\pipeline\.venv\Scripts\python.exe' -m pytest tools/test_build_propertytax.py -q
& 'C:\IT\ClaudeProjects\ExploreBurtonMI\pipeline\.venv\Scripts\python.exe' -m py_compile tools/build_propertytax.py
npm test -- test/infoPanel.test.ts test/propertyTax.test.ts
```

Expected: all focused tests PASS; `py_compile` exits 0 with no output.

- [ ] **Step 9: Commit the contract and generated data**

```powershell
git add src/lib/types.ts src/lib/dashboard/infoPanel.ts test/infoPanel.test.ts `
  tools/build_propertytax.py tools/test_build_propertytax.py `
  public/info-propertytax.json public/freshness.json
git commit -m "Update Burton City millage data"
```

---

### Task 3: Accessible responsive City millage renderer

**Files:**

- Modify: `src/lib/TaxEstimator.svelte`
- Create: `test/taxEstimator.test.ts`
- Modify: `test/dashboardSections.test.ts`

**Interfaces:**

- Consumes: `InfoEstimator`, `taxForMills`, `sumLevyMills`, and `roundedCents`.
- Produces: a semantic City levy table, a separate complete-bill result, invalid-input safety, and theme-token-only estimator surfaces and text.

- [ ] **Step 1: Write the failing server-render tests**

Create `test/taxEstimator.test.ts`:

```ts
import { render } from 'svelte/server';
import { describe, expect, it } from 'vitest';
import TaxEstimator from '../src/lib/TaxEstimator.svelte';
import type { InfoEstimator } from '../src/lib/types';

const data: InfoEstimator = {
  cityRatePeriod: 'FY2026-27 adopted levy',
  fullBillRatePeriod: '2025 published rates',
  cityMills: 13.2948,
  cityLevies: [
    {
      id: 'general-operating',
      service: 'General city operations',
      authorization: 'City Charter',
      description: 'Supports general municipal services provided by the City.',
      mills: 4,
      voterApproved: false,
    },
    {
      id: 'police',
      service: 'Police services',
      authorization: 'Voter approved',
      description: 'Supports Police Department staffing and operations.',
      mills: 8.3159,
      voterApproved: true,
    },
    {
      id: 'fire',
      service: 'Fire services',
      authorization: 'Voter approved',
      description: 'Supports Fire Department services and operations.',
      mills: 0.9789,
      voterApproved: true,
    },
  ],
  districts: [{ name: 'Atherton', homestead: 41.86, nonHomestead: 59.72 }],
};

describe('TaxEstimator', () => {
  it('renders the latest City levy as a personalized service table', () => {
    const { body } = render(TaxEstimator, { props: { data } });

    expect(body).toContain('Your City of Burton taxes');
    expect(body).toContain('FY2026-27 adopted levy');
    expect(body).toContain('<table');
    expect(body).toContain('City service');
    expect(body).toContain('Who authorized it');
    expect(body).toContain('General city operations');
    expect(body).toContain('Police services');
    expect(body).toContain('Fire services');
    expect(body).toContain('City Charter');
    expect(body.match(/Voter approved/g)).toHaveLength(2);
    expect(body).toContain('4.0000');
    expect(body).toContain('8.3159');
    expect(body).toContain('0.9789');
    expect(body).toContain('$200.00');
    expect(body).toContain('$415.80');
    expect(body).toContain('$48.95');
    expect(body).toContain('$664.74');
    expect(body).toContain('9.2948 voter-approved mills');
    expect(body).toContain('$464.74');
  });

  it('keeps the older complete-bill estimate in a separately dated result', () => {
    const { body } = render(TaxEstimator, { props: { data } });

    expect(body).toContain('Estimated complete property-tax bill');
    expect(body).toContain('2025 published rates');
    expect(body).toContain('$2,093.00');
    expect(body).toContain('41.86 mills');
    expect(body).toContain('do not become City of Burton revenue');
    expect(body).not.toContain('Only about');
    expect(body).not.toContain('Schools &amp; other');
  });
});
```

In `test/dashboardSections.test.ts`, read `src/lib/TaxEstimator.svelte` and assert its card, table, muted text, and dividers use `--pub-surface`, `--pub-surface-2`, `--pub-border`, `--pub-ink`, `--pub-muted`, and `--civic-blue-link`; reject `color: #444`, `border: 1px solid #d6e0f0`, and `background: var(--civic-blue-tint`.

- [ ] **Step 2: Run the renderer tests and verify RED**

Run: `npm test -- test/taxEstimator.test.ts test/dashboardSections.test.ts`

Expected: FAIL because the current renderer has one mixed-vintage result, no levy table, old copy, and hard-coded light colors.

- [ ] **Step 3: Replace the estimator calculations**

Use these derived values in `src/lib/TaxEstimator.svelte`:

```ts
import type { InfoEstimator } from './types';
import {
  normaliseTaxableValue,
  roundedCents,
  sumLevyMills,
  taxForMills,
} from './propertyTax';

let { data }: { data: InfoEstimator } = $props();
let taxableValue = $state<number | undefined>(50_000);
let districtIdx = $state(0);
let homestead = $state(true);

const district = $derived(data.districts[districtIdx] ?? data.districts[0]);
const safeTaxableValue = $derived(normaliseTaxableValue(taxableValue));
const totalRate = $derived(homestead ? district.homestead : district.nonHomestead);
const cityRows = $derived(
  data.cityLevies.map((levy) => ({
    ...levy,
    amount: taxForMills(safeTaxableValue, levy.mills),
  })),
);
const cityTotal = $derived(taxForMills(safeTaxableValue, data.cityMills));
const voterMills = $derived(sumLevyMills(data.cityLevies, true));
const voterTotal = $derived(taxForMills(safeTaxableValue, voterMills));
const completeBillTotal = $derived(taxForMills(safeTaxableValue, totalRate));
const rowCents = $derived(cityRows.reduce((sum, row) => sum + roundedCents(row.amount), 0));
const totalCents = $derived(roundedCents(cityTotal));
const hasRoundingDifference = $derived(rowCents !== totalCents);

const currency = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const fmtCurrency = (value: number) => currency.format(value);
const fmtMills = (value: number) => value.toFixed(4);
```

Do not calculate `countyAmt`, `restAmt`, or `cityPct`.

- [ ] **Step 4: Render two dated semantic result sections**

Keep the three existing labeled controls. Replace the current `.result` markup with this structure:

```svelte
<section class="city-result" aria-labelledby="city-tax-heading">
  <div class="result-heading">
    <div>
      <h4 id="city-tax-heading">Your City of Burton taxes</h4>
      <p>{data.cityRatePeriod}</p>
    </div>
    <div class="result-total">
      <strong>{fmtCurrency(cityTotal)}</strong>
      <span>estimated City total per year</span>
    </div>
  </div>

  <table>
    <caption class="sr-only">City of Burton millage and estimated annual tax by service</caption>
    <colgroup>
      <col class="service-col" />
      <col class="authorization-col" />
      <col class="mills-col" />
      <col class="amount-col" />
    </colgroup>
    <thead>
      <tr>
        <th scope="col">City service</th>
        <th scope="col">Who authorized it</th>
        <th scope="col">Mills</th>
        <th scope="col">Your annual amount</th>
      </tr>
    </thead>
    <tbody>
      {#each cityRows as levy (levy.id)}
        <tr>
          <th scope="row">
            {levy.service}
            <span class="description">{levy.description}</span>
          </th>
          <td><span class="authorization">{levy.authorization}</span></td>
          <td class="numeric">{fmtMills(levy.mills)}</td>
          <td class="numeric amount">{fmtCurrency(levy.amount)}</td>
        </tr>
      {/each}
    </tbody>
    <tfoot>
      <tr>
        <th scope="row" colspan="2">City of Burton total</th>
        <td class="numeric">{fmtMills(data.cityMills)}</td>
        <td class="numeric amount">{fmtCurrency(cityTotal)}</td>
      </tr>
    </tfoot>
  </table>

  {#if hasRoundingDifference}
    <p class="rounding-note">
      Individually rounded service amounts can differ from the combined City total by one cent.
    </p>
  {/if}

  <p class="voter-takeaway">
    Police and Fire account for <strong>{fmtMills(voterMills)} voter-approved mills</strong>,
    or <strong>{fmtCurrency(voterTotal)}</strong> of this City estimate.
  </p>
</section>

<section class="complete-result" aria-labelledby="complete-tax-heading">
  <div>
    <h4 id="complete-tax-heading">Estimated complete property-tax bill</h4>
    <p>{data.fullBillRatePeriod} for {district.name} ({homestead ? 'homestead' : 'non-homestead'})</p>
  </div>
  <div class="complete-total">
    <strong>{fmtCurrency(completeBillTotal)}</strong>
    <span>{totalRate.toFixed(2)} mills per year</span>
  </div>
  <p>
    This complete-bill estimate includes County, schools, the State, ISD, college,
    transit, airport, and other authorities. Those amounts do not become City of Burton revenue.
  </p>
</section>
```

Keep the fine print, revising it to state that the estimate excludes exact parcel details, exemptions, special assessments, administrative fees, and a possible DDA levy. Keep `Not a tax statement.`

- [ ] **Step 5: Replace hard-coded estimator colors with semantic tokens**

Use `var(--pub-surface-2)` for the estimator shell, `var(--pub-surface)` for result sections, `var(--pub-border)` for all borders, `var(--pub-ink)` for primary text, `var(--pub-muted)` for captions, and `var(--civic-blue-link)` for emphasized headings and amounts. Use `table-layout: fixed; width: 100%`, right-align numeric columns, allow descriptions and headers to wrap, and set `.numeric { font-variant-numeric: tabular-nums; }`.

At `max-width: 520px`, keep the native table semantics but reduce cell padding and font size, hide `.description`, assign the four columns `31% 25% 18% 26%`, and allow header words to wrap. Set all containers to `min-width: 0` and do not add horizontal scrolling.

Implement those requirements with this CSS, retaining the current labeled-control layout where it already matches:

```css
.estimator {
  min-width: 0;
  margin: 0 0 1.6rem;
  padding: 1rem;
  border: 1px solid var(--pub-border);
  border-radius: var(--pub-radius, 10px);
  background: var(--pub-surface-2);
  color: var(--pub-ink);
}
h3,
h4 {
  margin: 0;
  color: var(--civic-blue-link);
  font-family: var(--font-head, sans-serif);
}
.lead,
.result-heading p,
.complete-result > div:first-child p,
.description,
.rounding-note,
.fineprint {
  color: var(--pub-muted);
}
.city-result,
.complete-result {
  min-width: 0;
  margin-top: 1rem;
  padding: 0.9rem;
  border: 1px solid var(--pub-border);
  border-radius: var(--pub-radius-sm, 8px);
  background: var(--pub-surface);
}
.result-heading,
.complete-result {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.75rem 1rem;
  align-items: start;
}
.result-total,
.complete-total {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  text-align: right;
}
.result-total strong,
.complete-total strong,
.amount {
  color: var(--civic-blue-link);
  font-weight: 800;
}
table {
  width: 100%;
  margin-top: 0.8rem;
  border-collapse: collapse;
  table-layout: fixed;
}
.service-col { width: 31%; }
.authorization-col { width: 25%; }
.mills-col { width: 18%; }
.amount-col { width: 26%; }
th,
td {
  padding: 0.55rem 0.45rem;
  border-bottom: 1px solid var(--pub-border);
  color: var(--pub-ink);
  text-align: left;
  vertical-align: top;
  overflow-wrap: anywhere;
}
thead th {
  color: var(--pub-muted);
  font-size: 0.75rem;
}
tbody th,
tfoot th {
  font-weight: 700;
}
.description {
  display: block;
  margin-top: 0.15rem;
  font-size: 0.72rem;
  font-weight: 400;
  line-height: 1.35;
}
.authorization {
  font-weight: 600;
}
.numeric {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
tfoot th,
tfoot td {
  border-top: 2px solid var(--pub-border);
  border-bottom: 0;
}
.voter-takeaway,
.complete-result > p {
  grid-column: 1 / -1;
  margin: 0.75rem 0 0;
  color: var(--pub-ink);
}
.rounding-note {
  margin: 0.5rem 0 0;
  font-size: 0.72rem;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
@media (max-width: 520px) {
  .estimator,
  .city-result,
  .complete-result {
    padding: 0.75rem;
  }
  .result-heading,
  .complete-result {
    grid-template-columns: 1fr;
  }
  .result-total,
  .complete-total {
    align-items: flex-start;
    text-align: left;
  }
  th,
  td {
    padding: 0.45rem 0.25rem;
    font-size: 0.72rem;
  }
  .description {
    display: none;
  }
}
```

- [ ] **Step 6: Run focused tests and verify GREEN**

Run: `npm test -- test/taxEstimator.test.ts test/dashboardSections.test.ts test/propertyTax.test.ts`

Expected: all focused tests PASS.

- [ ] **Step 7: Run the type checker**

Run: `npm run check`

Expected: zero errors and zero warnings.

- [ ] **Step 8: Commit the renderer**

```powershell
git add src/lib/TaxEstimator.svelte test/taxEstimator.test.ts test/dashboardSections.test.ts
git commit -m "Show City millages by service"
```

---

### Task 4: Resident copy, priority facts, and official sources

**Files:**

- Modify: `public/dashboard-clarity.json`
- Modify: `test/dashboardClarityContent.test.ts`

**Interfaces:**

- Consumes: generated labels and periods from Task 2 and the existing dashboard clarity enrichment boundary.
- Produces: a consistent first-screen explanation and the three authoritative source links requested by the user.

- [ ] **Step 1: Write failing committed-content assertions**

Replace the outdated property-tax assertions in `test/dashboardClarityContent.test.ts` with:

```ts
const propertyTax = loadJson('public/info-propertytax.json') as {
  estimator: {
    cityRatePeriod: string;
    fullBillRatePeriod: string;
    cityMills: number;
    cityLevies: Array<{
      id: string;
      authorization: string;
      mills: number;
      voterApproved: boolean;
    }>;
  };
  stats: Array<{ label: string; value: string; hint: string }>;
  links: Array<{ text: string; href: string }>;
};
expect(propertyTax.estimator.cityMills).toBe(13.2948);
expect(propertyTax.estimator.cityRatePeriod).toBe('FY2026-27 adopted levy');
expect(propertyTax.estimator.fullBillRatePeriod).toBe('2025 published rates');
expect(propertyTax.estimator.cityLevies.map((levy) => levy.mills)).toEqual([
  4,
  8.3159,
  0.9789,
]);
expect(propertyTax.estimator.cityLevies.filter((levy) => levy.voterApproved))
  .toHaveLength(2);
expect(propertyTax.stats.find((stat) => stat.label === "City of Burton's rate")?.value)
  .toBe('13.2948 mills');
expect(propertyTax.stats.find((stat) => stat.label === 'Voter-approved City millages')?.value)
  .toBe('9.2948 mills');
expect(propertyTax.links).toEqual(expect.arrayContaining([
  {
    text: 'City of Burton 2026-27 Approved Budget',
    href: 'https://www.burtonmi.gov/government/controller_s_office/budgets.php',
  },
  {
    text: 'Genesee County L-4029 information',
    href: 'https://www.geneseecountymi.gov/departments/equalization/l-4029_information.php',
  },
  {
    text: 'Michigan property-tax estimator',
    href: 'https://www.michigan.gov/taxes/property/estimator',
  },
]));
```

Also assert the enriched Property Taxes panel contains all three context source links, mentions both source periods, contains `City Charter` and `Voter approved`, and no longer contains `13.44-mill City rate is about 29%` or `components round to 13.43`.

Use these exact assertions:

```ts
const propertyTaxPanel = enrichedPanels().propertytax;
expect(propertyTaxPanel.context).toEqual(expect.objectContaining({
  asOf: 'FY2026-27 City levy; 2025 complete-bill rates',
  sourceLinks: [
    {
      text: '2026-27 Approved Budget',
      href: 'https://www.burtonmi.gov/government/controller_s_office/budgets.php',
    },
    {
      text: 'Genesee County L-4029 information',
      href: 'https://www.geneseecountymi.gov/departments/equalization/l-4029_information.php',
    },
    {
      text: 'Michigan property-tax estimator',
      href: 'https://www.michigan.gov/taxes/property/estimator',
    },
  ],
}));
expect(propertyTaxPanel.headline).toContain('13.2948 mills');
expect(propertyTaxPanel.headline).toContain('9.2948 voter-approved');
expect(propertyTaxPanel.headline).toContain('4.0000 charter');
expect(JSON.stringify(propertyTaxPanel)).toContain('FY2026-27');
expect(JSON.stringify(propertyTaxPanel)).toContain('2025');
expect(JSON.stringify(propertyTaxPanel)).not.toContain('13.44-mill City rate is about 29%');
expect(JSON.stringify(propertyTaxPanel)).not.toContain('components round to 13.43');
expect(propertyTax.estimator.cityLevies.map((levy) => levy.authorization)).toEqual([
  'City Charter',
  'Voter approved',
  'Voter approved',
]);
```

- [ ] **Step 2: Run the committed-content test and verify RED**

Run: `npm test -- test/dashboardClarityContent.test.ts`

Expected: FAIL on the old context date, headline, explanation, stat overrides, and source list.

- [ ] **Step 3: Update the Property Taxes clarity record**

Set the `propertytax.context` fields to:

```json
{
  "scope": "Burton parcels",
  "status": "reference",
  "asOf": "FY2026-27 City levy; 2025 complete-bill rates",
  "sourceLinks": [
    {
      "text": "2026-27 Approved Budget",
      "href": "https://www.burtonmi.gov/government/controller_s_office/budgets.php"
    },
    {
      "text": "Genesee County L-4029 information",
      "href": "https://www.geneseecountymi.gov/departments/equalization/l-4029_information.php"
    },
    {
      "text": "Michigan property-tax estimator",
      "href": "https://www.michigan.gov/taxes/property/estimator"
    }
  ]
}
```

Use this headline and explanation:

```json
"headline": "Burton's FY2026-27 City levy is 13.2948 mills: 9.2948 voter-approved Police and Fire mills plus 4.0000 charter mills for general operations.",
"summary": {
  "heading": "Why this matters",
  "body": [
    "One mill is $1 per $1,000 of taxable value. The calculator shows the latest adopted City levy by service and keeps the separately published 2025 complete-bill estimate clearly dated."
  ]
}
```

Keep the responsibility boundary and change the action text to `Use the City millage calculator`. Update `statOverrides` so the four priority labels are `City of Burton's rate`, `Voter-approved City millages`, `City tax on a $50k-taxable home`, and `School districts in Burton`. Update the first chart takeaway to say it is a typical **2025** homestead bill and the history takeaway to say it covers reported FY2017-FY2026 rates.

- [ ] **Step 4: Run focused and full Vitest suites**

Run:

```powershell
npm test -- test/dashboardClarityContent.test.ts test/infoPanel.test.ts test/taxEstimator.test.ts
npm test
```

Expected: focused and full Vitest suites PASS, with the total test count increased by the new arithmetic and estimator tests.

- [ ] **Step 5: Commit resident copy and sources**

```powershell
git add public/dashboard-clarity.json test/dashboardClarityContent.test.ts
git commit -m "Clarify current City property tax rates"
```

---

### Task 5: Complete verification and refresh the comparison handoff

**Files:**

- Modify: `planning/comparison/dashboard-clarity-review.md`
- Create or replace: `planning/comparison/screenshots/new-propertytax-desktop-light.png`
- Create or replace: `planning/comparison/screenshots/new-propertytax-phone-light.png`
- Create or replace: `planning/comparison/screenshots/new-propertytax-phone-dark.png`

**Interfaces:**

- Consumes: the production comparison server at `http://127.0.0.1:4174/#propertytax` and unchanged baseline at `http://127.0.0.1:4173/#propertytax`.
- Produces: reproducible check results and visual evidence for City comparison review; no publication.

- [ ] **Step 1: Run every protected local gate from the feature worktree**

Run:

```powershell
npm run check
npm test
npm run build
& 'C:\IT\ClaudeProjects\ExploreBurtonMI\pipeline\.venv\Scripts\python.exe' -m pytest pipeline/test tools -q
& 'C:\IT\ClaudeProjects\ExploreBurtonMI\apps\pin-editor\.venv\Scripts\python.exe' -m pytest apps/pin-editor/test -q
& 'C:\IT\ClaudeProjects\ExploreBurtonMI\pipeline\.venv\Scripts\python.exe' -m pytest tools/test_repo_security.py -q
& 'C:\IT\ClaudeProjects\ExploreBurtonMI\pipeline\.venv\Scripts\python.exe' -m py_compile tools/build_propertytax.py
```

Expected: Svelte check has zero errors and warnings; all Vitest, pipeline/tools, pin-editor, and repository-security tests pass; production/PWA build succeeds; Python compilation exits 0. CodeQL remains a required protected-PR result and is not replaced by a local claim.

- [ ] **Step 2: Reload the comparison server and verify desktop light mode**

Open the baseline and comparison Property Taxes routes at 1280x720. On the comparison route, confirm:

- the source block says `FY2026-27 City levy; 2025 complete-bill rates`;
- the headline exposes 13.2948, 9.2948, and 4.0000 without requiring chart interpretation;
- the default $50,000 City table shows all three services, authorizations, mills, dollars, and the one-cent rounding disclosure;
- the complete-bill result is visibly separate and labeled `2025 published rates`;
- official budget, County L-4029, and Michigan estimator links are visible and keyboard-focusable;
- no browser console errors or warnings occur.

- [ ] **Step 3: Verify Android phone width in light and dark modes**

At 390x844, verify both themes. Confirm no horizontal page overflow, all four table columns remain identifiable, dollars and service names remain readable, focus indicators are visible, and measured normal-text/link contrast is at least 4.5:1.

Exercise the estimator with:

- default $50,000 Atherton homestead;
- Bendle non-homestead;
- taxable value cleared to blank/zero; and
- taxable value changed to $100,000, which must show exact City amounts of $400.00, $831.59, $97.89, and $1,329.48.

- [ ] **Step 4: Capture comparison screenshots**

Capture the three named Property Taxes screenshots after the final production build. Keep the baseline server unchanged and do not overwrite unrelated representative screenshots.

- [ ] **Step 5: Update the comparison guide**

Add Property Taxes old/new links, explain the current City versus 2025 complete-bill vintage boundary, record the exact final test counts and visual checks, list the three new screenshots, and replace the obsolete statement about the 13.43-versus-13.44 ACFR rounding with the FY2026-27 adopted breakdown.

- [ ] **Step 6: Review the final diff**

Run:

```powershell
git diff --check
git status --short
git diff --stat origin/main...HEAD
```

Expected: no whitespace errors; only the property-tax calculation, contract, generator, generated data, renderer, tests, clarity metadata, comparison documentation, and intended screenshots are changed by this feature.

- [ ] **Step 7: Commit comparison evidence**

```powershell
git add planning/comparison/dashboard-clarity-review.md `
  planning/comparison/screenshots/new-propertytax-desktop-light.png `
  planning/comparison/screenshots/new-propertytax-phone-light.png `
  planning/comparison/screenshots/new-propertytax-phone-dark.png
git commit -m "Document property tax comparison"
```

- [ ] **Step 8: Stop at the comparison boundary**

Report the old/new URLs and verification results to the user. Do not push, open a pull request, merge, alter branch protection, update issue #94, or publish until the user approves the comparison.
