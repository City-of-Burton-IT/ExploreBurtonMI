# ADR-0003: Publish City-owned property for sale and aggregated home-sale tiles

**Date:** 2026-10-15
**Status:** proposed
**Decision owner:** City of Burton IT, with the Purchasing Department (listings)
and the Assessor (sales data) as data owners

## Context

Residents and prospective buyers ask Explore Burton for an MLS-style view of
property. Live MLS listings are not open data: Realcomp and the local Realtor
association license them under IDX rules, and Zillow, Redfin and Realtor.com
forbid redisplay. ADR-0001 therefore rules them out.

Two adjacent datasets are City records and carry no licence problem:

1. **City-owned property for sale.** The Purchasing Department already lists
   tax-reverted and surplus parcels on burtonmi.gov in two tracks, "No Bid" at a
   Council-set asking price and "Bid Required" by sealed bid. Council approves
   every sale. The City is the seller and owns the data and photos.
2. **Recorded arms-length sales.** The Assessing roll in BS&A records the sale
   date, price and property class for every transfer; the Assessor already uses
   them for the annual sales study. Sale prices are public record in Michigan.

ADR-0002 requires a new ADR before any publication joins parcel identifiers to
value or ownership data. This is that ADR.

## Decision

### Part A: City-owned property for sale

Publish a committed GeoJSON of parcels the City is currently offering for sale,
rendered as a toggleable map overlay and a "City Property for Sale" dashboard
with a card table and links to the Purchasing pages and the offer or bid packet.

- **Source** is a curated CSV, `pipeline/data/city-property-sales.csv`,
  maintained by Purchasing. It is committed because every row is a City-owned
  parcel the City has already published for sale.
- **Fields** per row: parcel number, situs address, sale track (`offer` or
  `bid`), asking price or "Sealed bid", lot size, zoning, status
  (`available`, `pending`, `sold`), listed date, optional sold date and sold
  price, optional photo filename, optional note, packet URL.
- **Allowed in the public file**: all of the above. The owner is the City of
  Burton, so no private person's name or value appears. Sold rows stay in the
  file for one year as a public track record, then drop.
- **Not allowed**: any parcel the City does not own, any former owner's name,
  any tax-delinquency history, buyer names for sold parcels.
- Coordinates come from the existing Census batch geocoder path used by
  `tools/build_address_points.py`, clipped to the city boundary.

### Part B: Aggregated home-sale tiles

Publish price and volume of recent arms-length residential sales only as
**aggregates over spatial cells**, never as individual points.

- **Source** is an Assessing sales export (parcel, class, sale date, price,
  situs address), dropped at `pipeline/data/sales-source.csv`, which is
  gitignored exactly like the address-points source.
- **Cells** are a hexagonal grid of about 400 m across the city boundary, or
  Census block groups where the hex grid would be too sparse. The build tool
  picks the cell size; the output names it.
- **Suppression**: a cell shows values only when it holds **at least five**
  qualifying sales in the window. Cells below the threshold render as "too few
  sales to show" with a count bucket ("1 to 4"), never a price.
- **Published per cell**: sale count, median price, median price per square
  foot when square footage is in the export, and the change versus the prior
  window. No parcel numbers, addresses, dates or individual prices leave the
  build machine.
- **Window**: trailing 24 months, labelled with the export date.
- **Qualifying sales**: residential class, arms-length as flagged by the
  Assessor's sales-study codes, price above a floor the Assessor sets to
  exclude nominal transfers.
- Commercial and industrial sales are out of scope for this ADR because their
  low volume makes single transactions identifiable even in aggregate.

### Shared controls

- Both builds live in `tools/` with pytest coverage and use the shared `lib`
  helpers, `assert_shape` fail-loud checks and atomic writes.
- Both outputs carry a `generated` date and a `source` string the dashboards
  show as "Data as of".
- The Open Data page offers the aggregated tiles and the for-sale list as CSV
  like every other dashboard.
- The privacy notice gains a paragraph naming both sources and the suppression
  rule.
- Any change to the suppression threshold, the cell size or the field list
  requires an update to this ADR and data-owner review.

## Alternatives considered

| Alternative | Why not selected |
|---|---|
| Embed an IDX feed of live MLS listings | Requires a brokerage sponsor and Realcomp vendor agreement; a contract, not a data source, and outside ADR-0001 |
| Scrape or API-pull Zillow, Redfin or Realtor.com | Terms of service forbid it; no public API exists |
| Publish individual sale points with address and price | Public record, but tells every neighbour what a household paid and invites re-identification; aggregation gives the same market signal |
| Link out only | Keeps the City's own for-sale inventory invisible on its own map |
| Publish only the for-sale list and skip sales entirely | Loses the market-context story that makes the inventory attractive to buyers |

## Consequences

Prospective buyers and businesses see every parcel the City is selling, with the
same zoning, school-district and traffic context the map already carries, and a
neighbourhood-level view of what homes sell for. Purchasing gains a single CSV to
maintain instead of hand-editing a web page; a later SharePoint-list and Power
Automate commit path can replace the CSV without a UI change.

The sales tiles are a derived product. If the Assessor changes the arms-length
codes or the export shape, the build fails loudly rather than publishing a wrong
median. The five-sale floor means some cells in low-turnover neighbourhoods will
never show a price, and the dashboard says so.
