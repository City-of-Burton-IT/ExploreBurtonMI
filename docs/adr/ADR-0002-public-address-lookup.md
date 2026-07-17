# ADR-0002: Publish a minimized City situs-address lookup for on-device reverse geocoding

**Date:** 2026-07-17
**Status:** accepted
**Decision owner:** City of Burton IT

## Context

The Report an Issue experience can suggest the nearest street address after a
resident drops a map pin. Explore Burton is a static application, so a server-side
City geocoder would add a new service, availability dependency, resident-location
request log, and public attack surface.

The internal build input is a City-maintained assessing export from BS&A. Assessing
exports can contain owner, parcel, value, and tax fields that are not necessary for
this feature. The raw source file is therefore gitignored and never published.

## Decision

Publish a minimized lookup generated from City of Burton assessing situs addresses,
with coordinates geocoded through the U.S. Census batch geocoder. The public file
contains only tuples of latitude, longitude, and normalized situs address. It must
not contain owner names, parcel identifiers, assessed values, tax data, email,
telephone, account numbers, or source-system identifiers.

The browser or native app downloads the committed lookup lazily and performs the
nearest-address calculation on-device. A dropped pin is not sent to the City or a
third-party geocoder unless and until the resident submits a report through the
separate, disclosed issue-report workflow.

The source CSV remains local and gitignored. A rebuild replaces the public snapshot;
raw exports are not retained in Git. The lookup is refreshed when the assessing
address roll materially changes and is reviewed with the same public-data diff gate
as other generated map data.

## Required controls

- `tools/build_address_points.py` reads only the situs-address fields needed to
  construct the normalized address and Census geocoding request.
- The generated schema remains a three-value tuple. Tests fail if the shape changes
  or an object/property payload is introduced without a new review.
- The privacy notice names the City assessing-situs source, explains on-device use,
  and distinguishes suggestion from submission.
- The raw export stays covered by `.gitignore` and staged-secret/PII preflight.
- Any future join to owner, parcel, value, utility, or account data requires a new ADR
  and explicit data-owner review before publication.

## Alternatives considered

| Alternative | Why not selected |
|---|---|
| Send the dropped coordinate to a public geocoder | Discloses resident-selected locations and adds a runtime third-party dependency |
| Operate a City reverse-geocoding API | Adds an unnecessary public service, logs, authentication/rate-limiting work, and availability burden |
| Use a less precise street-centroid list | Reduces disclosure but produces materially worse suggestions near intersections and dense streets |
| Remove address suggestions | Most private option, but makes accurate issue reports harder and increases staff triage work |

## Consequences

The application can suggest addresses offline and without transmitting the dropped
location. Exact situs addresses are downloadable as public data, so source authority,
field minimization, schema tests, and transparent disclosure are permanent controls.
If City policy or the source-data basis changes, remove or replace the lookup rather
than silently broadening its fields.
