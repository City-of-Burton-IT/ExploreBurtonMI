# Property Tax City Millage Breakdown Design

**Date:** 2026-07-20

**Branch:** `feature/dashboard-clarity-comparison`

**Status:** Approved design; implementation pending written-plan approval

## Purpose

Make the Property Taxes dashboard show exactly how the City of Burton portion of a resident's property tax is divided among City services. Residents should be able to distinguish voter-approved millages from the City's charter-authorized operating levy and see the estimated annual dollars for their own taxable value.

## Source of Truth and Data Vintage

Use the latest adopted City levy in Burton's **FY2026-27 Approved Budget**:

| City levy | Authorization shown to residents | Mills |
| --- | --- | ---: |
| General Operating | City Charter | 4.0000 |
| Police Levies | Voter approved | 8.3159 |
| Fire Levy | Voter approved | 0.9789 |
| **City of Burton total** |  | **13.2948** |

The voter-approved Police and Fire subtotal is **9.2948 mills**. The General Operating levy must not be described as voter-approved.

Official sources:

- City budgets and resources: <https://www.burtonmi.gov/government/controller_s_office/budgets.php>
- FY2026-27 Approved Budget: <https://cms4files.revize.com/burton/government/controller_s_office/docs/1-FINAL%20BUDGET%20BOOK.pdf?t=20260604122406187>
- Genesee County L-4029 information: <https://www.geneseecountymi.gov/departments/equalization/l-4029_information.php>
- Michigan property-tax estimator: <https://www.michigan.gov/taxes/property/estimator>

The latest complete, published school-district totals currently used by the dashboard are 2025 rates. The interface must not silently combine the FY2026-27 City levy with 2025 complete-bill totals and present the result as one internally reconciled tax year.

## Resident Experience

Keep the existing taxable-value, school-district, and property-type controls. Present two clearly dated results:

1. **Your City of Burton taxes - FY2026-27 adopted levy**
   - Show General Operating, Police, and Fire as separate rows.
   - Show each row's authorization, mills, and estimated annual dollars.
   - Show the 13.2948-mill City subtotal.
   - Highlight the 9.2948-mill voter-approved Police and Fire subtotal in plain language.
2. **Your estimated complete property-tax bill - 2025 published rates**
   - Preserve the school-district and homestead/non-homestead estimate.
   - Clearly state that County, schools, ISD, college, transit, airport, and other authorities do not become City of Burton revenue.
   - Do not use the newer City amount to derive a remainder or percentage from the older complete-bill total.

For the default $50,000 taxable value, the City table should calculate:

| City levy | Estimated annual amount |
| --- | ---: |
| General Operating | $200.00 |
| Police Levies | $415.80 |
| Fire Levy | $48.95 |
| **City total** | **$664.74** |
| **Voter-approved Police and Fire subtotal** | **$464.74** |

The explanatory copy will define one mill as $1 per $1,000 of taxable value and remind residents that taxable value is not the same as market value.

At this example value, independently rounded levy rows add to one cent more than the subtotal calculated from the combined mill rate. Calculate subtotals from unrounded values and disclose that line-item rounding can create a one-cent difference; do not silently alter a levy rate or force an inaccurate component amount to make displayed cents reconcile.

## Component and Data Design

Extend the shared property-tax estimator contract with a collection of City levy components. Each component will contain:

- a stable identifier;
- resident-facing service label;
- authorization label;
- exact mill rate; and
- a short explanation of what the levy supports.

The build script remains the authoritative place for documented constants and generated `public/info-propertytax.json`. The Svelte estimator receives data only; it does not embed Burton millage constants.

The component will calculate dollars as:

`taxable value x mills / 1,000`

Currency will display to cents in the detailed City table. Calculations retain the full mill-rate precision until final display rounding. High-level takeaways may use whole-dollar amounts when explicitly described as approximate.

## Clarity, Accessibility, and Responsive Behavior

- Use semantic theme tokens already established by the dashboard clarity work; do not introduce hard-coded light-mode text or surface colors.
- Use text labels for authorization and service purpose, not color alone.
- Keep table headers visible and meaningful: **City service**, **Who authorized it**, **Mills**, and **Your annual amount**.
- At Android phone width, convert or reflow the table without horizontal page overflow; the service label and dollar amount remain the strongest visual signals.
- Preserve keyboard access, form labels, visible focus, screen-reader table semantics, and readable contrast in light and dark modes.
- Explain that the estimate excludes special assessments, exemptions, administrative fees, and parcel-specific additions.
- Mention a Downtown Development Authority levy only as a possible parcel-specific addition unless the estimator gains reliable parcel-location data. Do not add it to every resident's City subtotal.

## Source Links

Add the Approved Budget, Genesee County L-4029, and Michigan property-tax estimator to the Property Taxes dashboard's official-source links. Links must identify what a resident will find rather than using generic text such as "Learn more."

## Validation and Error Handling

- Reject missing, duplicate, non-numeric, or negative City levy component data through the existing runtime panel validator.
- Treat a blank or invalid taxable-value input as zero for display without producing `NaN`, negative tax amounts, or broken layout.
- Verify that City components sum exactly to 13.2948 mills and that voter-approved components sum exactly to 9.2948 mills.
- Keep the existing published complete-bill rates and their vintage explicit until a complete 2026 authority schedule is available from an official source.

## Tests and Verification

Implementation will begin with failing tests for:

- the FY2026-27 City levy constants and totals;
- the generated JSON component contract;
- runtime validation of well-formed and malformed components;
- personalized dollar calculations at $50,000 taxable value;
- separation of FY2026-27 City results from 2025 complete-bill results; and
- required official-source links and resident-facing authorization labels.

Then run the project's strict web checks, Python tests, pin-editor tests, and CodeQL/security checks. Visually verify the Property Taxes dashboard on the comparison server at desktop and Android phone widths in both light and dark modes, including taxable-value edits and each property-type option.

## Non-goals

- No parcel lookup or address collection.
- No claim that the estimator is an official tax bill.
- No preliminary reconstruction of every 2026 County, school, or overlapping-authority rate.
- No change to issue #94, branch protections, or unrelated dashboards.
- No push, pull request, or publication until the comparison is approved.
