# Turn the find_dupes report into explicit hide-overrides in
# pipeline/data/overrides.json (auditable, refresh-safe, NOT a live heuristic).
#
# Decisions encoded here (reviewed against the find_dupes report):
#   * Hide the non-survivor in every same-site name-variant cluster (Tier 1 + 2).
#   * PROTECT genuinely distinct co-located POIs (e.g. the dog park at a church).
#   * BIG-BOX: collapse department pins into the main store, but enrich the
#     survivor with a `services` list (shown in the detail popup) and a multi-value
#     `category` (so a "Pharmacy" filter still surfaces Walmart).
#
#   python tools/apply_dupe_overrides.py            # dry run: print what would change
#   python tools/apply_dupe_overrides.py --write     # merge into overrides.json
#
# Stdlib only.
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import find_dupes as fd  # noqa: E402

OVERRIDES = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "pipeline", "data", "overrides.json")
)

# Co-located POIs that are genuinely distinct, never hide these even though they
# share an address with a survivor.
PROTECT = {
    "overture:c4925a6a-3c14-4d1d-8879-9d7c379b6a1b",  # Burton Dog Park (at Our Risen Lord Lutheran Church)
}

# Big-box survivors: extra properties merged onto the kept record so collapsing the
# department pins loses nothing a resident would search for.
BIGBOX_ENRICH = {
    "osm:way/628515087": {  # Walmart Supercenter
        "category": ["Grocery & Food", "Health & Medical", "Automotive", "Retail & Shopping"],
        "services": [
            "Pharmacy", "Auto Center", "Tire & Lube Express", "Bakery",
            "Photo Center", "Wireless Services", "Grocery Pickup & Delivery",
        ],
        "_why": "Big-box: collapsed 9 department pins into one. services + multi-category "
                "kept so e.g. a Pharmacy/Automotive filter still surfaces Walmart.",
    },
    "osm:way/678727214": {  # The Home Depot
        "category": ["Retail & Shopping", "Automotive"],
        "services": ["Tool & Truck Rental", "Home Services"],
        "_why": "Big-box: collapsed department pins into one; services + multi-category kept.",
    },
    "overture:20363e70-906b-489d-9ca7-c718bd047268": {  # Jcpenney -> JCPenney
        "name": "JCPenney",
        "services": ["Sephora"],
        "_why": "Collapsed Sephora-inside-JCPenney into the store; service kept in the popup.",
    },
}


def build_decisions():
    d = json.load(open(fd.DATA, encoding="utf-8"))
    by_addr: dict = {}
    for f in d["features"]:
        a = fd.norm_addr(f["properties"].get("address", ""))
        if a:
            by_addr.setdefault(a, []).append(f)

    hides, protected = [], []
    for group in by_addr.values():
        if len(group) < 2:
            continue
        for _tier, cluster in fd.cluster_address_group(group):
            survivor, to_hide = fd.pick_survivor(cluster)
            for h in to_hide:
                if h["id"] in PROTECT:
                    protected.append(h)
                    continue
                hides.append((h, survivor))
    return hides, protected


def main() -> int:
    write = "--write" in sys.argv
    hides, protected = build_decisions()

    new_overrides: dict = {}
    for h, survivor in hides:
        new_overrides[h["id"]] = {
            "hidden": True,
            "_why": f"Duplicate of {survivor['id']} ({survivor['properties'].get('name')}) "
                    f"at {h['properties'].get('address')}.",
        }
    for sid, props in BIGBOX_ENRICH.items():
        new_overrides[sid] = props

    print(f"{len(hides)} records to hide, {len(protected)} protected, "
          f"{len(BIGBOX_ENRICH)} big-box survivors enriched.")
    for h in protected:
        print(f"  PROTECTED (kept): {h['properties'].get('name')!r}  {h['id']}")

    existing = json.load(open(OVERRIDES, encoding="utf-8"))
    added = hidden_merged = enrich_skipped = 0
    for k, v in new_overrides.items():
        if k not in existing:
            existing[k] = v
            added += 1
        elif v.get("hidden") and not existing[k].get("hidden"):
            # Record carries a prior enrichment override (phone/website) but is a
            # confirmed duplicate: fold hidden:true in (its props become moot once
            # hidden, and the surviving record already carries the same/better data).
            existing[k] = {**existing[k], "hidden": True, "_why": v["_why"]}
            hidden_merged += 1
        else:
            # A survivor we tried to re-enrich, or already hidden: leave as-is.
            enrich_skipped += 1
    print(f"\nMerge: {added} new, {hidden_merged} hidden merged into existing enrichment, "
          f"{enrich_skipped} left as-is.")

    if not write:
        print("\n(dry run: pass --write to save)")
        return 0

    with open(OVERRIDES, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(existing, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"Wrote {OVERRIDES}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
