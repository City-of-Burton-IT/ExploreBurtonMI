# City Property for Sale: Purchasing self-service setup

How the Purchasing Department keeps the "City Property for Sale" dashboard and map
overlay current without touching Git. Same shape as the listing-request apply path
(#66): SharePoint list, Power Automate flow, `repository_dispatch`, GitHub Actions,
review pull request, merge publishes.

Code side is done (`tools/sync_city_property.py`, `.github/workflows/apply-city-property.yml`,
`tools/build_city_property.py`). This page is the M365 side, which must be created
in the GCC tenant by hand (`make.gov.powerautomate.us`, site `/sites/ITDepartment`).

## 1. SharePoint list

Site: IT Department (`burtonmi.sharepoint.com/sites/ITDepartment`).
List name: **Explore Burton City Property for Sale**.
Grant Purchasing staff Edit; everyone else Read.

| Column (internal name) | Type | Required | Notes |
|---|---|---|---|
| Title | Single line | yes | Rename the display name to **Parcel**. BS&A parcel number, e.g. `59-12-776-262` |
| Address | Single line | yes | Situs street line, e.g. `1234 E BRISTOL RD`; a lot with no number: `VACANT E BRISTOL RD` |
| Track | Choice | yes | `No bid`, `Bid Required` |
| Status | Choice | yes | `Available`, `Sale pending`, `Sold` (default `Available`) |
| Price | Number (0 decimals) | no | Asking price (No bid) or minimum bid; blank means "Sealed bid" |
| LotSize | Single line | no | e.g. `60 x 120 ft` or `0.41 acre` |
| Zoning | Single line | no | e.g. `R-1` |
| Listed | Date only | no | Date the parcel went on the list |
| SoldDate | Date only | only when Sold | Council approval date |
| SoldPrice | Number (0 decimals) | only when Sold | |
| Photo | Single line | no | Filename under `public/property/` (IT adds the file) |
| Note | Single line | no | One public sentence, e.g. "Corner lot, utilities at street" |
| PacketUrl | Hyperlink | yes | The offer form or bid packet for this parcel, `https://` only |

Validation the workflow enforces (a bad row stops the publish, nothing goes live):
Track and Status must be one of the choices; PacketUrl must start with `https://`;
dates ISO; Price and SoldPrice numeric; a Sold row needs SoldDate; one row per parcel.
Rows sold more than a year ago drop off the public site automatically; delete them
from the list whenever convenient.

## 2. Power Automate flow

Name: **Explore Burton: publish City Property list**. Owner: the IT service account
used by the listing flow. Run as a cloud flow in the GCC environment.

1. **Trigger**: SharePoint "When an item is created or modified" on the list above.
   Add a trigger condition so edits by the flow itself do not loop (not needed here;
   the flow never writes back) and a **Concurrency control** of 1.
2. **Delay** 2 minutes (lets a person finish a batch of edits so one dispatch covers them).
3. **Get items** (SharePoint) on the same list, Top Count 500, no filter.
4. **Select**: map each item to a flat object with exactly these keys:
   `Parcel` (Title), `Address`, `Track` (Track Value), `Status` (Status Value), `Price`,
   `LotSize`, `Zoning`, `Listed`, `SoldDate`, `SoldPrice`, `Photo`, `Note`,
   `PacketUrl` (PacketUrl Url). Choice and hyperlink columns must be flattened to
   their `Value` / `Url`; the sync tool also accepts the raw objects, but flat is cleaner.
5. **HTTP** action:
   - Method `POST`
   - URI `https://api.github.com/repos/City-of-Burton-IT/ExploreBurtonMI/dispatches`
   - Headers: `Accept: application/vnd.github+json`, `Authorization: Bearer <token>`,
     `User-Agent: ExploreBurton-PA`
   - Body:

     ```json
     { "event_type": "apply-city-property", "client_payload": { "rows": @{body('Select')} } }
     ```

   The token is a fine-grained GitHub PAT scoped to this one repository with
   **Contents: Read and write** (needed for `repository_dispatch`), expiring, stored in
   the flow's HTTP action (or an environment variable secret). The listing flow
   already holds one; reuse or rotate it, never paste it anywhere else.
6. Optional **Send an email** to Purchasing and IT: "List sent for publication; IT
   will merge the review within one business day."

Turn the flow off to stop publishing instantly (kill switch). Run history is the
usage log.

## 3. What happens on the GitHub side

`apply-city-property.yml` runs on the dispatch, validates every row with the same
reader the builder uses, rewrites `pipeline/data/city-property-sales.csv`, rebuilds
`public/city-property.geojson` and `public/info-cityproperty.json`, pushes a branch
`automation/city-property-<run>` and opens a PR (with `LISTING_PR_TOKEN`) or links
the compare page in the run summary. **Merging the PR publishes.** IT reviews the
diff: it is the complete public list, so a wrong row is obvious.

Parcels with no street number are placed from the committed parcel-centroid table
by parcel number, so the parcel number in the list must be the BS&A number.

## 4. First-run checklist

- [ ] Create the list with the columns above; add one real parcel from the current No-Bid page.
- [ ] Create the flow; run it once by editing that row.
- [ ] Confirm the Actions run `Apply City Property for Sale list` succeeded and a review branch or PR exists.
- [ ] Merge; within minutes the dashboard shows the parcel and the overlay pin or outline.
- [ ] Hand Purchasing a one-paragraph note: edit the list, wait for IT's merge, the site updates. Status to Sold and the SoldDate when Council approves.

## 5. Later

- Auto-merge for this path once Purchasing has a few clean runs (the PR gate becomes optional).
- Lot outlines instead of pins (the parcel-polygons file is local only today; the
  builder would read it like `build_business_sites.py` does).
- Photos: a document library on the same site, copied into `public/property/` by the workflow.
