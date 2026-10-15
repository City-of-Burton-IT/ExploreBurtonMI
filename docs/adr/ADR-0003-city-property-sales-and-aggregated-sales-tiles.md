# ADR-0003: Publish City-owned property for sale, aggregated home-sale tiles, and business sites

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
- **Cells** are the 23 Census block groups that cover Burton (TIGERweb current
  vintage, clipped to the city). A 2026-10-15 coverage test on the live Sales
  table showed a 400 m hex grid puts only 42% of sales in a cell with five or
  more, while every block group holds at least seven in a 24-month window and
  the median block group holds 26. Hexes are not used.
- **Suppression**: a cell shows values only when it holds **at least five**
  qualifying sales in the window. Cells below the threshold render as "too few
  sales to show" with a count bucket ("1 to 4"), never a price.
- **Published per cell**: sale count, median price, median price per square
  foot, and the change versus the prior 24-month window. No parcel numbers, addresses, dates or individual prices leave the
  build machine.
- **Window**: trailing 24 months, labelled with the export date.
- **Qualifying sales**: property class 4xx, `terms` code `03-ARM'S LENGTH` or
  `19-MULTI PARCEL ARM'S LENGTH` (the Assessor's own terms coding; the
  `useInECF` flag is a different, much narrower study flag and is not used),
  `confidential` not set, improved parcels only (`isVacantLandSale` = 0), and
  a recorded price above zero. The Assessor's coding decides what is a sale;
  the City adds no price floor of its own (a 2026-10-15 check found only six
  zero-price rows and seven improved sales under $20,000 in 24 months, too few
  to move any block-group median). A multi-parcel sale counts once, keyed on
  its recorded liber and page. About 600 sales qualify per 24 months. Finished floor area (`resb_floorarea`) is
  present on nearly every qualifying sale, so price per square foot is
  publishable.
- Commercial and industrial sales are out of scope for this ADR because their
  low volume makes single transactions identifiable even in aggregate.

### Part C: Sites for Business (approved 2026-10-15)

Publish two parcel-level overlays and one dashboard from the Assessing roll so a
business can find land or a building in Burton:

- **Vacant commercial and industrial sites**: property classes 202 and 302.
- **Commercial and industrial buildings**: property classes 201 and 301. The roll
  does not know which buildings are for lease or sale; the layer is an inventory
  and says so.

**Published per parcel**: parcel number, situs address, property class, lot size
in acres, frontage, zoning district, and coordinates. **Not published**: owner
name or mailing address, assessed or taxable value, tax status, sale history, or
any flag from the roll beyond the class code. This is the parcel-level join that
ADR-0002 reserved for explicit approval; the data owner approved it on
2026-10-15 on the basis that every field is already public on BS&A Online and no
person is identified.

**Commercial sale prices** are not aggregated by neighbourhood. A 2026-10-15
check found 48 arms-length commercial and industrial sales in 24 months across
the whole city, with a single sale at $5.6 million; any block-group median would
effectively name one transaction. The business dashboard carries one citywide
line only, the count of commercial and industrial buildings that changed hands
in the trailing 24 months, with no prices.

### Part D: New homes permitted, and context joins (2026-10-15)

- **New homes permitted overlay**: one pin per new-home building permit since
  2015 (the three new-home categories the permits dashboard already uses), with
  the situs address, issue year and unit count only. No owner, applicant,
  contractor, permit number, value or description. This is the first time an
  address from the Permits table is published; the permits dashboard itself
  stays aggregate-only, and its note now says so.
- **Context joins, no new data published**: each home-sales block group carries
  the school district containing its sales centroid and an estimated annual tax
  bill on its median home (taxable value = half the sale price, City mills and
  the district's published homestead rate from the Property Taxes estimator);
  each business site within about 150 m of an MDOT-counted road carries that
  road's daily vehicle count from the existing traffic overlay.

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
