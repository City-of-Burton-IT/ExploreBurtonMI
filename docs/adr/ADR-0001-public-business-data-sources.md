# ADR-0001: Source public business data only from redistributable or city-owned datasets

**Date:** 2026-06-04
**Status:** accepted
**Session context:** A push loaded ~1,549 records from the AtoZdatabases commercial reference product onto the live public map; review found the vendor license prohibits public republication, so the data was removed and a redistribution-rights rule was set for all future sources.

## Context

Explore Burton is a public, unauthenticated `.gov` site that serves its full
dataset as a downloadable `public/data.geojson`. Any data published there is, by
construction, reproduced and given away to anyone.

The AtoZdatabases export that was briefly published is licensed for **personal
use only**; its Terms state *"You may not sell, reproduce or give away the
information,"* and its product model is authenticated patron lookups with a
1,000-record export cap (the publish exceeded the cap at 1,549 and also exposed
88 home-based / residential addresses). Being a licensed *institution* grants
patron-access rights, not redistribution rights. Facts about businesses are not
copyrightable (*Feist*), but the binding constraint here is the **subscription
contract**, which forbids reproduction regardless — so AtoZ cannot even be used
as a seed/search index for a public deliverable.

The site therefore needs a sourcing rule that guarantees every published record
comes from data the City is legally free to redistribute publicly.

## Decision

Public business/place listings are sourced **only** from datasets that are either
**city-owned public records**, **open-licensed for redistribution**, or
**contributed with consent**. AtoZdatabases (and any personal-use / no-reproduce
licensed reference product) is excluded from the published build entirely.

Approved sources for the replacement business layer:

| Source | License / basis | Role |
|---|---|---|
| City business-registration / business-license roll | City-owned public record | Authoritative core (current, address-bound, renewed annually) |
| OpenStreetMap | ODbL (redistribute with attribution) | Already in the pipeline; fills gaps |
| **Overture Maps Foundation — Places theme** | CDLA-Permissive 2.0 (Overture Maps Foundation / Linux Foundation; founding members Meta, Microsoft, Amazon, TomTom) | Modern open global POI dataset; GeoParquet, queryable via DuckDB, clip to Burton bbox/boundary |
| **Foursquare Open Source Places (FSQ OS Places)** | Apache-2.0 (open-sourced Nov 2024; also contributed into Overture) | Millions of redistributable POIs; Parquet on S3, clip to boundary |
| "Claim / add your business" submission form | Opt-in consent | Keeps listings current; owner-maintained |

License terms for Overture and Foursquare must be re-confirmed at build time
(open dataset licenses and access paths evolve).

## Alternatives considered

| Option | Why rejected |
|---|---|
| Republish the AtoZ export | Vendor T&C: "personal use only … may not reproduce or give away"; exceeded the 1,000-record export cap; exposed residential addresses |
| Use AtoZ as a seed list, re-verify each record via Google/web, then publish | Contract forbids reproduction/derivative use regardless of re-sourcing; *Feist* (facts uncopyrightable) does not override an agreed personal-use contract; Google Places ToS also restricts caching/redistribution |
| Buy a commercial feed licensed for redistribution (Data Axle, HERE, TomTom, Precisely) | Viable but costs money; deferred until the free + owned sources prove insufficient |
| Link out to the authenticated AtoZ portal instead of hosting data | Compliant and worth offering as a convenience link, but does not populate the City's own map layer |

## Consequences

**Positive:**

- Every published record is legally redistributable; no third-party license
  exposure on a public `.gov` site.
- City-owned registration data is more authoritative and current than a purchased
  commercial list.
- The existing pipeline already provides geocoding (Census), boundary clipping,
  public-safe validation, and proximity dedup — the replacement is mostly a new
  ingest module feeding the same machinery.

**Negative / trade-offs:**

- Overture/Foursquare are cloud-hosted GeoParquet datasets; ingesting them adds a
  DuckDB (or equivalent Parquet/cloud-query) dependency the current pipeline does
  not have.
- Coverage/freshness of open POI data varies; a consent-based claim form is needed
  to keep listings accurate.

**Follow-on decisions needed:**

- The residential-exclusion rule still applies to city-owned data: a
  business-registration roll also contains home-based businesses at residential
  addresses. Owning the data makes publishing it *legal*, not necessarily *wise* —
  keep the home-based filter.
- A separate build/ADR will define the Parquet ingest tooling (DuckDB vs Overture
  CLI vs cloud query) and the Overture/FSQ category-to-Burton-category mapping.

## Update — 2026-06-04 (implementation)

Resolved during the implementation spec
([planning/specs/2026-06-04-overture-ingest.md](../../planning/specs/2026-06-04-overture-ingest.md)):

- **Foursquare Open Places dropped** — Overture Places already incorporates
  Foursquare's open data (donated to Overture in 2024), so a separate FSQ ingest
  would mostly deduplicate the same POIs. Overture is the single open-POI source.
- **Ingest tooling = Approach C (out-of-band extract + committed snapshot).** The
  binary readers (overturemaps/DuckDB) live in `tools/extract_overture.py`; the
  pipeline stays pure-Python and reads a committed
  `pipeline/data/overture_places.geojson`. Chosen to honor the pipeline's
  no-binary-dependency / Python-3.14 constraint and to keep each snapshot
  diff-reviewable before it ships.
