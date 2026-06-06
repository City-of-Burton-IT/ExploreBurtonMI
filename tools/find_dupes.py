# Find same-site name-variant duplicates in public/data.geojson.
#
# The pipeline already collapses IDENTICAL names within 120 m (merge.dedupe_
# proximity). What slips through is name VARIANTS at one address -- "Chase" vs
# "Chase Bank", "Hungry Howie's" vs "Hungry Howie's Pizza". This is a one-time
# DISCOVERY tool: it groups records by normalized address, finds variant clusters,
# tiers them by confidence, and recommends which record to hide (keeping the most
# complete one). It changes nothing -- it prints a report so a human signs off on
# the actual removals, which are then encoded as explicit hide-overrides in
# pipeline/data/overrides.json (auditable + refresh-safe).
#
#   python tools/find_dupes.py            # human-readable report
#   python tools/find_dupes.py --json     # machine-readable proposal (high-conf only)
#
# Stdlib only.
from __future__ import annotations

import json
import os
import re
import sys

DATA = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public", "data.geojson"))

# Tokens that don't distinguish one business from another at the same address.
GENERIC = {
    "the", "of", "and", "a", "an",
    "inc", "llc", "co", "corp", "corporation", "company", "ltd",
    "store", "shop", "outlet",
    "pizza", "restaurant", "cafe",
    "bank",
}
# Fields whose presence makes a record "more complete" (the survivor of a merge).
VALUE_FIELDS = ("phone", "website", "hours", "description", "category")

DIR_MAP = {"north": "n", "south": "s", "east": "e", "west": "w"}
ST_MAP = {
    "road": "rd", "street": "st", "avenue": "ave", "av": "ave", "drive": "dr",
    "boulevard": "blvd", "highway": "hwy", "court": "ct", "lane": "ln",
    "place": "pl", "parkway": "pkwy", "circle": "cir", "trail": "trl",
}


def norm_addr(addr: str) -> str:
    """Aggressively normalize an address so spelling variants group together."""
    a = (addr or "").lower()
    a = re.sub(r"\b(\d{5})-\d{4}\b", r"\1", a)        # drop the +4 ZIP
    a = re.sub(r"[.,]", " ", a)
    toks = []
    for t in a.split():
        t = DIR_MAP.get(t, t)
        t = ST_MAP.get(t, t)
        toks.append(t)
    return " ".join(toks).strip()


def core_tokens(name: str) -> list:
    """Reduce a name to its distinguishing tokens (lowercased, generic words and
    store-number/parenthetical noise removed)."""
    n = (name or "").lower()
    n = n.replace("&", " and ")
    n = re.sub(r"\(.*?\)", " ", n)                    # "(MIF 04)"
    n = re.sub(r"#\s*\w+", " ", n)                    # "#44371"
    n = re.sub(r"[^a-z0-9 ]", " ", n)                 # apostrophes, hyphens, slashes
    toks = [t for t in n.split() if t and t not in GENERIC and not t.isdigit()]
    return toks


def completeness(props: dict) -> int:
    return sum(1 for f in VALUE_FIELDS if str(props.get(f) or "").strip())


def name_quality(name: str) -> tuple:
    """Sort key for "cleanest name": no digits, no parens, then shorter."""
    has_num = 1 if re.search(r"\d", name or "") else 0
    has_paren = 1 if "(" in (name or "") else 0
    return (has_num, has_paren, len(name or ""))


def classify(a_tokens: list, b_tokens: list) -> str:
    """'high' = same core (variant), 'eyes' = one core contained in / overlaps the
    other (related, needs a human), '' = unrelated."""
    if not a_tokens or not b_tokens:
        return ""
    sa, sb = set(a_tokens), set(b_tokens)
    if a_tokens == b_tokens:
        return "high"
    if sa <= sb or sb <= sa:
        return "eyes"
    overlap = len(sa & sb) / len(sa | sb)
    return "eyes" if overlap >= 0.5 else ""


def cluster_address_group(group: list) -> list:
    """Within one address, return variant clusters (each a list of features that
    are name-variants of each other), tagged with the strongest tier in the cluster."""
    cores = [core_tokens(f["properties"].get("name", "")) for f in group]
    n = len(group)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        parent[find(x)] = find(y)

    tiers: dict = {}
    for i in range(n):
        for j in range(i + 1, n):
            tier = classify(cores[i], cores[j])
            if tier:
                union(i, j)
                tiers[(i, j)] = tier

    clusters: dict = {}
    for i in range(n):
        clusters.setdefault(find(i), []).append(i)

    out = []
    for idxs in clusters.values():
        if len(idxs) < 2:
            continue
        # strongest tier among any joined pair inside this cluster
        tier = "high"
        for i in idxs:
            for j in idxs:
                if i < j and (i, j) in tiers and tiers[(i, j)] == "eyes":
                    tier = "eyes"
        out.append((tier, [group[i] for i in idxs]))
    return out


def pick_survivor(features: list) -> tuple:
    """Return (survivor, [to_hide]). Survivor = most complete record, tie-broken by
    cleanest name."""
    ranked = sorted(
        features,
        key=lambda f: (-completeness(f["properties"]), name_quality(f["properties"].get("name", ""))),
    )
    return ranked[0], ranked[1:]


def main() -> int:
    as_json = "--json" in sys.argv
    d = json.load(open(DATA, encoding="utf-8"))
    by_addr: dict = {}
    for f in d["features"]:
        a = norm_addr(f["properties"].get("address", ""))
        if a:
            by_addr.setdefault(a, []).append(f)

    high, eyes = [], []
    for addr, group in by_addr.items():
        if len(group) < 2:
            continue
        for tier, cluster in cluster_address_group(group):
            survivor, to_hide = pick_survivor(cluster)
            entry = {"addr": addr, "survivor": survivor, "hide": to_hide}
            (high if tier == "high" else eyes).append(entry)

    if as_json:
        proposal = {}
        for e in high:
            keep = e["survivor"]["properties"]
            for h in e["hide"]:
                missing = [f for f in VALUE_FIELDS if str(h["properties"].get(f) or "").strip()
                           and not str(keep.get(f) or "").strip()]
                proposal[h["id"]] = {
                    "hidden": True,
                    "_why": f"Duplicate of {e['survivor']['id']} ({keep.get('name')}) at {e['addr']}.",
                    **({"_survivor_missing": missing} if missing else {}),
                }
        print(json.dumps(proposal, indent=2, ensure_ascii=False))
        return 0

    def show(title, entries):
        print(f"\n{'='*70}\n{title}  ({len(entries)} clusters, "
              f"{sum(len(e['hide']) for e in entries)} records to hide)\n{'='*70}")
        for e in sorted(entries, key=lambda x: x["addr"]):
            s = e["survivor"]["properties"]
            print(f"\n  {e['addr']}")
            print(f"    KEEP  {s.get('name')!r}  [{s.get('category')}]  "
                  f"fields={completeness(s)}  id={e['survivor']['id']}")
            for h in e["hide"]:
                hp = h["properties"]
                gain = [f for f in VALUE_FIELDS if str(hp.get(f) or "").strip()
                        and not str(s.get(f) or "").strip()]
                tag = f"  (has {', '.join(gain)} the kept one lacks!)" if gain else ""
                print(f"    hide  {hp.get('name')!r}  [{hp.get('category')}]  "
                      f"fields={completeness(hp)}  id={h['id']}{tag}")

    show("TIER 1 -- HIGH CONFIDENCE (same core name, generic suffix only)", high)
    show("TIER 2 -- NEEDS EYES (related names; confirm before hiding)", eyes)
    print(f"\nTotal: {sum(len(e['hide']) for e in high)} high-confidence + "
          f"{sum(len(e['hide']) for e in eyes)} needs-eyes records flagged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
