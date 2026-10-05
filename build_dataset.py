"""Build a large pool of real US street addresses with ground-truth ZIP codes.

Source: Overture Maps "addresses" theme, US rows, which come from the USDOT
National Address Database (NAD) - authoritative address points (one per real
structure/site) contributed by state and local governments. Each point carries
its own ZIP and USPS postal city, so every address here exists as recorded.

Overture files are spatially sorted, so a random parquet row group is a random
neighborhood-sized chunk of the country. We draw random all-US row groups
(roughly address-density weighted, so populous areas show up more) and take a
handful of addresses from each.

Each address gets a difficulty tier from how many ZIPs its city has:
easy = 1 (one-ZIP town), medium = 2-9, hard = 10+ (big cities).

Filters: plain numeric house numbers, no unit/apartment, 5-digit ZIP that
GeoNames confirms exists in the same state, and no address string that maps
to more than one ZIP.

Usage:
    uv run build_dataset.py --row-groups 300 --per-group 70 --out data/addresses.csv
"""

import argparse
import csv
import io
import random
import re
import ssl
import sys
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import certifi
import pyarrow.fs as pafs
import pyarrow.parquet as pq

RELEASE = "2026-09-23.0"
BUCKET_DIR = f"overturemaps-us-west-2/release/{RELEASE}/theme=addresses/type=address/"
GEONAMES_URL = "https://download.geonames.org/export/zip/US.zip"
CACHE = Path("cache")
SSL_CTX = ssl.create_default_context(cafile=certifi.where())
COLUMNS = ["country", "street", "number", "unit", "postcode", "postal_city", "address_levels", "sources"]

S3 = pafs.S3FileSystem(anonymous=True, region="us-west-2")


def load_zip_states() -> tuple[dict[str, str], dict[tuple[str, str], set[str]]]:
    """ZIP -> state, and (city, state) -> set of ZIPs, from GeoNames."""
    path = CACHE / "geonames_US.zip"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(GEONAMES_URL, timeout=120, context=SSL_CTX) as r:
            path.write_bytes(r.read())
    out, city_zips = {}, {}
    with zipfile.ZipFile(path) as z, z.open("US.txt") as f:
        for line in io.TextIOWrapper(f, encoding="utf-8"):
            cols = line.split("\t")
            out[cols[1]] = cols[4]
            city_zips.setdefault((cols[2].lower(), cols[4]), set()).add(cols[1])
    return out, city_zips


def tier(n_zips: int) -> str:
    """Difficulty by how many ZIPs share the city name: one-ZIP towns are free if you know the town."""
    return "easy" if n_zips <= 1 else "medium" if n_zips < 10 else "hard"


def us_row_groups() -> list[tuple[str, int]]:
    """(file, row_group) pairs whose country column is entirely 'US', from footer stats only."""
    files = sorted(i.path for i in S3.get_file_info(pafs.FileSelector(BUCKET_DIR)) if i.path.endswith(".parquet"))

    def scan(path):
        md = pq.ParquetFile(path, filesystem=S3).metadata
        ci = md.schema.names.index("country")
        out = []
        for g in range(md.num_row_groups):
            st = md.row_group(g).column(ci).statistics
            if st is not None and st.has_min_max and st.min == "US" and st.max == "US":
                out.append((path, g))
        return out

    with ThreadPoolExecutor(16) as ex:
        return [rg for res in ex.map(scan, files) for rg in res]


UPPER_TOKENS = {"N", "S", "E", "W", "NE", "NW", "SE", "SW", "US", "SR", "FM", "CR", "II", "III", "IV"}


def tidy(s: str) -> str:
    """NAD is mixed-case ("ALLOWAY Road"); normalize to how people write addresses."""
    words = []
    for w in s.split():
        if w.upper() in UPPER_TOKENS:
            words.append(w.upper())
        elif re.fullmatch(r"\d+(ST|ND|RD|TH)", w, re.I):
            words.append(w.lower())
        else:
            words.append(w[:1].upper() + w[1:].lower())
    return " ".join(words)


def addresses_for_group(path: str, group: int, per_group: int, zip_states, seed: int) -> list[dict]:
    rng = random.Random(f"{seed}:{path}:{group}")
    rows = pq.ParquetFile(path, filesystem=S3).read_row_group(group, columns=COLUMNS).to_pylist()
    rng.shuffle(rows)
    out = []
    for r in rows:
        number, street, unit = (r["number"] or "").strip(), (r["street"] or "").strip(), r["unit"]
        zip5 = (r["postcode"] or "").strip()[:5]
        city = (r["postal_city"] or "").strip()
        state = r["address_levels"][0]["value"] if r["address_levels"] else ""
        city = re.sub(rf",?\s+{state}$", "", city, flags=re.I) if state else city  # "Jackson, WI" -> "Jackson"
        if unit or not street or not city or not re.fullmatch(r"[1-9]\d*", number):
            continue
        if not re.fullmatch(r"\d{5}", zip5) or zip_states.get(zip5) != state:
            continue  # ZIP must be a real ZIP in this state
        src = r["sources"][0] if r["sources"] else {}
        out.append({
            "address": f"{number} {tidy(street)}, {tidy(city)}, {state}",
            "zip": zip5,
            "state": state,
            "source": f"{src.get('provider', '')}:{src.get('record_id', '')}",
        })
        if len(out) >= per_group:
            break
    return out


def city_key(r: dict) -> tuple[str, str]:
    return r["address"].rsplit(", ", 2)[1].lower(), r["state"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--row-groups", type=int, default=300, help="random neighborhood-sized chunks to draw from")
    ap.add_argument("--per-group", type=int, default=70)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--out", default="data/addresses.csv")
    args = ap.parse_args()

    zip_states, city_zips = load_zip_states()
    groups = us_row_groups()
    chosen = random.Random(args.seed).sample(groups, min(args.row_groups, len(groups)))
    print(f"{len(groups)} all-US row groups in Overture {RELEASE}, sampling {len(chosen)}", file=sys.stderr)

    rows = []
    with ThreadPoolExecutor(args.workers) as ex:
        futs = [ex.submit(addresses_for_group, p, g, args.per_group, zip_states, args.seed) for p, g in chosen]
        for i, fut in enumerate(as_completed(futs), 1):
            try:
                rows.extend(fut.result())
            except Exception as e:
                print(f"\n  skip row group: {e}", file=sys.stderr)
            if i % 25 == 0 or i == len(futs):
                print(f"  {i}/{len(futs)} row groups, {len(rows)} addresses", file=sys.stderr)

    # Drop address strings recorded with more than one ZIP; dedupe the rest.
    zips: dict[str, set[str]] = {}
    for r in rows:
        zips.setdefault(r["address"], set()).add(r["zip"])
    rows = list({r["address"]: r for r in rows if len(zips[r["address"]]) == 1}.values())
    # Tier = ZIPs for this city per GeoNames, or seen in our own pool if GeoNames has more/doesn't know it.
    pool_zips: dict[tuple[str, str], set[str]] = {}
    for r in rows:
        pool_zips.setdefault(city_key(r), set()).add(r["zip"])
    for r in rows:
        k = city_key(r)
        r["city_zips"] = max(len(city_zips.get(k, ())), len(pool_zips[k]))
        r["tier"] = tier(r["city_zips"])
    rows.sort(key=lambda r: (r["state"], r["zip"], r["address"]))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["address", "zip", "state", "tier", "city_zips", "source"])
        w.writeheader()
        w.writerows(rows)
    counts = {t: sum(r["tier"] == t for r in rows) for t in ("easy", "medium", "hard")}
    print(f"tiers: {counts}", file=sys.stderr)
    print(f"wrote {len(rows)} addresses across {len({r['state'] for r in rows})} states to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
