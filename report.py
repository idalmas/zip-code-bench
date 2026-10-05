"""Leaderboard outputs, all rebuilt from results/summary.csv (the durable record).

    results/summary.csv     one row per (model, run), append-only
    results/LEADERBOARD.md  ranked tables, grouped by sample
    site/index.html         the same leaderboard as a plain web page

run_eval.py calls this after every model; run `uv run report.py` to rebuild by hand.
"""

import csv
import html
import json
from datetime import datetime
from pathlib import Path

RESULTS = Path("results")
SUMMARY = RESULTS / "summary.csv"
LEADERBOARD_MD = RESULTS / "LEADERBOARD.md"
SITE = Path("site/index.html")
DATA = Path("data/addresses.csv")
TIERS = ("easy", "medium", "hard")
TIER_HELP = {"easy": "town has 1 ZIP", "medium": "city has 2-9 ZIPs", "hard": "city has 10+ ZIPs"}

FIELDS = ["timestamp", "model", "effort", "sample", "n", "seed", "exact", "prefix3", "exact_pct", "prefix3_pct",
          *[f"{t}_{k}" for t in TIERS for k in ("n", "pct")],
          "errors", "unparsed", "cost_usd", "mean_latency_s", "details"]


def read_summary() -> list[dict]:
    if not SUMMARY.exists():
        return []
    with open(SUMMARY, newline="") as f:
        return list(csv.DictReader(f))


def backfill(row: dict, tier_of: dict[str, str]) -> dict:
    """Older rows predate tiers/sample labels; fill them from the per-item log."""
    row.setdefault("sample", "")
    if not row["sample"]:
        row["sample"] = f"{row['n']} random, seed {row['seed']}"
    if not row.get("easy_n") and Path(row["details"]).exists():
        items = [json.loads(line) for line in open(row["details"])]
        for t in TIERS:
            sub = [r for r in items if tier_of.get(r["address"]) == t]
            row[f"{t}_n"] = len(sub)
            row[f"{t}_pct"] = round(100 * sum(r["exact"] for r in sub) / len(sub), 1) if sub else ""
    return row


def migrate() -> None:
    """If summary.csv has an older header, rewrite it once with the current columns."""
    rows = read_summary()
    if not rows or list(rows[0].keys()) == FIELDS:
        return
    tier_of = {}
    if DATA.exists():
        with open(DATA, newline="") as f:
            tier_of = {r["address"]: r.get("tier", "") for r in csv.DictReader(f)}
    rows = [backfill(r, tier_of) for r in rows]
    with open(SUMMARY, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def append_summary(row: dict) -> None:
    RESULTS.mkdir(exist_ok=True)
    migrate()
    new = not SUMMARY.exists()
    with open(SUMMARY, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)
    write_all()


def boards() -> list[tuple[str, list[dict]]]:
    """One board per sample; within it, the latest run per (model, effort), ranked."""
    groups: dict[str, dict[tuple, dict]] = {}
    for r in read_summary():
        if int(r["n"]) < 10 or int(r["errors"]) > 0:  # smoke tests, and runs with failed requests
            continue
        groups.setdefault(r["sample"], {})[(r["model"], r["effort"])] = r  # later rows win
    out = []
    for label, latest in groups.items():
        rows = sorted(latest.values(), key=lambda r: (-float(r["exact_pct"]), -float(r["prefix3_pct"])))
        out.append((label, rows))
    # Tiered boards first, then most recent.
    out.sort(key=lambda g: ("per tier" not in g[0], -max(datetime.fromisoformat(r["timestamp"]).timestamp() for r in g[1])))
    return out


def pct(v: str) -> str:
    return f"{float(v):.1f}%" if v not in ("", None) else "–"


def write_markdown(groups) -> None:
    lines = ["# ZIP code bench leaderboard", "",
             "Exact 5-digit ZIP accuracy. Tiers: " + ", ".join(f"**{t}** = {h}" for t, h in TIER_HELP.items()) + ".",
             "Generated from `summary.csv`; latest run per model in each sample. Runs with failed requests are left out.", ""]
    for label, rows in groups:
        lines += [f"## {label}", "", "| # | model | exact | easy | medium | hard | first 3 digits | cost | details |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for i, r in enumerate(rows, 1):
            name = Path(r["details"]).name
            lines.append(f"| {i} | {r['model']}{'' if r['effort'] == 'default' else ' (' + r['effort'] + ')'} "
                         f"| **{pct(r['exact_pct'])}** | {pct(r['easy_pct'])} | {pct(r['medium_pct'])} | {pct(r['hard_pct'])} "
                         f"| {pct(r['prefix3_pct'])} | ${float(r['cost_usd']):.4f} | [log](runs/{name}) |")
        lines.append("")
    LEADERBOARD_MD.write_text("\n".join(lines))


PAGE_HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ZIP Code Bench</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;600;800&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* One narrow column: heading, a line of context, then one plain table per sample. */
:root {
  --bg: #f5f7fa; --surface: #ffffff; --fg: #18202b; --muted: #5d6b7c; --rule: #d9e0e8;
  --accent: #24548f; --bar: #c9d8ea;
  --sans: "Public Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #11161d; --surface: #171e27; --fg: #e4e9ef; --muted: #93a1b2; --rule: #2a3440;
  --accent: #82b0e6; --bar: #2b4565; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #11161d; --surface: #171e27; --fg: #e4e9ef; --muted: #93a1b2; --rule: #2a3440;
  --accent: #82b0e6; --bar: #2b4565; color-scheme: dark }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 15px/1.5 var(--sans); -webkit-font-smoothing: antialiased; }
main { max-width: 880px; margin: 0 auto; padding-inline: 16px; padding-block: 40px 56px; display: grid; gap: 28px; }
h1 { font-size: 30px; font-weight: 800; letter-spacing: -0.01em; margin: 0; text-wrap: balance; }
h1 span { font-family: var(--mono); font-weight: 500; color: var(--accent); }
.lede { margin: 6px 0 0; color: var(--muted); max-width: 65ch; }
section { display: grid; gap: 10px; }
h2 { font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); margin: 0; }
.wrap { overflow-x: auto; background: var(--surface); border: 1px solid var(--rule); border-radius: 6px; }
table { border-collapse: collapse; width: 100%; min-width: 620px; }
th, td { padding: 9px 12px; text-align: right; border-bottom: 1px solid var(--rule); white-space: nowrap; }
tr:last-child td { border-bottom: 0; }
th { font-size: 12px; font-weight: 600; color: var(--muted); }
th small { display: block; font-weight: 400; }
th:nth-child(2), td:nth-child(2) { text-align: left; }
td { font-family: var(--mono); font-size: 13px; font-variant-numeric: tabular-nums; }
td.model { font-family: var(--sans); font-size: 14px; }
td.rank { color: var(--muted); width: 1%; }
td.score { font-weight: 500; color: var(--accent); }
.bar { display: block; height: 3px; margin-top: 4px; background: var(--bar); border-radius: 2px; }
.bar i { display: block; height: 100%; background: var(--accent); border-radius: 2px; }
footer { color: var(--muted); font-size: 13px; }
</style>
</head>
<body>
"""


def write_site(groups) -> None:
    e = html.escape
    parts = [PAGE_HEAD, "<main>",
             '<header><h1>ZIP Code Bench <span>#####</span></h1>',
             '<p class="lede">Each model gets a real US street address from the National Address Database and has to '
             "name its 5-digit ZIP code from memory. One fresh request per address, no tools, no web search.</p></header>"]
    tier_th = "".join(f"<th>{t}<small>{TIER_HELP[t]}</small></th>" for t in TIERS)
    for label, rows in groups:
        parts += [f"<section><h2>{e(label)} &middot; {rows[0]['n']} addresses</h2>", '<div class="wrap"><table>',
                  f"<thead><tr><th>#</th><th>Model</th><th>Exact ZIP</th>{tier_th}<th>First 3<small>digits right</small></th><th>Cost</th></tr></thead><tbody>"]
        for i, r in enumerate(rows, 1):
            name = r["model"] + ("" if r["effort"] == "default" else f" ({r['effort']})")
            parts.append(
                f'<tr><td class="rank">{i}</td><td class="model">{e(name)}</td>'
                f'<td class="score">{pct(r["exact_pct"])}<span class="bar"><i style="width:{float(r["exact_pct"])}%"></i></span></td>'
                + "".join(f"<td>{pct(r[f'{t}_pct'])}</td>" for t in TIERS)
                + f"<td>{pct(r['prefix3_pct'])}</td><td>${float(r['cost_usd']):.3f}</td></tr>")
        parts.append("</tbody></table></div></section>")
    parts += [f"<footer>Updated {datetime.now():%Y-%m-%d %H:%M}. Addresses cover the 39 states in the National "
                 "Address Database; California, Georgia, Michigan and a few others are not included. Scores are about "
                 "&plusmn;9 points overall and &plusmn;15 per tier at 95% confidence.<br>Data: USDOT National Address "
                 "Database (public domain) via Overture Maps; ZIP table from GeoNames (CC BY 4.0).</footer></main>",
                  "</body>", "</html>"]
    SITE.parent.mkdir(exist_ok=True)
    SITE.write_text("\n".join(parts) + "\n")


def write_all() -> None:
    migrate()
    groups = boards()
    write_markdown(groups)
    write_site(groups)


if __name__ == "__main__":
    write_all()
    print(f"rebuilt {LEADERBOARD_MD} and {SITE}")
