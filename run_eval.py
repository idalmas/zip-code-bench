"""ZIP code recall eval: give a model a real US street address, ask for the ZIP.

- Samples N addresses at random from the big pool (data/addresses.csv).
- Each address is its own fresh, single-turn request via OpenRouter: no shared
  conversation, no few-shot examples, no tools, no web plugin.
- Scores exact 5-digit match, plus 3-digit prefix (same USPS sectional
  center) as a "close" metric.

Usage:
    cp .env.example .env   # then paste your OpenRouter key
    uv run run_eval.py                                    # 40 addresses, google/gemini-3.1-flash-lite
    uv run run_eval.py --per-tier 40 --seed 7 --model openai/gpt-6-luna --effort low
"""

import argparse
import csv
import json
import os
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import openai
from dotenv import load_dotenv

import report

PROMPT = """What is the 5-digit ZIP code for this US address?

{address}

Answer from your own knowledge; you have no tools or internet access. If unsure, give your single best guess. Respond with only the 5-digit ZIP code."""

# Model variants/families that search the web on their own; using them would defeat the eval.
SEARCHING_MODELS = re.compile(r":online$|^perplexity/|search", re.I)


def parse_zip(text: str, address: str) -> str | None:
    """The model's answer: the last 5-digit run in the reply, so "ZIP: 14850", ZIP+4, and
    "not 77450, it's 77449" all parse. The address's own house number is skipped, since a
    5-digit one ("20830 Clay Landing Ln") quoted back is not an answer."""
    house = address.split()[0]
    found = [z for z in re.findall(r"(?<!\d)\d{5}(?!\d)", text) if z != house]
    return found[-1] if found else None


def ask(client: openai.OpenAI, model: str, effort: str | None, address: str) -> dict:
    # Brand-new request per address: one user message, no history, no tools.
    extra = {"reasoning": {"effort": effort}} if effort else {}
    t0 = time.time()
    resp = client.chat.completions.create(
        model=model,
        max_tokens=16000,
        messages=[{"role": "user", "content": PROMPT.format(address=address)}],
        extra_body=extra,
    )
    choice = resp.choices[0]
    text = choice.message.content or ""
    usage = resp.usage.model_dump() if resp.usage else {}
    return {
        "pred": parse_zip(text, address),
        "raw": text,
        "finish_reason": choice.finish_reason,
        "served_by": resp.model,
        "provider": getattr(resp, "provider", None),
        "web_annotations": bool(getattr(choice.message, "annotations", None)),
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "cost": usage.get("cost"),
        "latency_s": round(time.time() - t0, 2),
    }


TIERS = ("easy", "medium", "hard")


def run_one(client, model, effort, row):
    try:
        res = ask(client, model, effort, row["address"])
    except openai.APIError as e:
        res = {"error": f"{type(e).__name__}: {e}", "pred": None}
        if getattr(e, "status_code", None) == 402:
            res["out_of_credits"] = True
    res |= {"address": row["address"], "gold": row["zip"], "state": row["state"], "tier": row.get("tier", "")}
    res["exact"] = res["pred"] == row["zip"]
    res["prefix3"] = bool(res["pred"]) and res["pred"][:3] == row["zip"][:3]
    return res


def save_run(model, effort, seed, sample_label, results) -> dict:
    """Write per-item JSONL and append one row to summary.csv."""
    (report.RESULTS / "runs").mkdir(parents=True, exist_ok=True)
    n = len(results)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    details = report.RESULTS / "runs" / f"{stamp}_{model.replace('/', '_')}_{effort or 'default'}_n{n}_s{seed}.jsonl"
    with open(details, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    lat = [r["latency_s"] for r in results if "latency_s" in r]
    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "model": model,
        "effort": effort or "default",
        "sample": sample_label,
        "n": n,
        "seed": seed,
        "exact": sum(r["exact"] for r in results),
        "prefix3": sum(r["prefix3"] for r in results),
        "exact_pct": round(100 * sum(r["exact"] for r in results) / n, 1),
        "prefix3_pct": round(100 * sum(r["prefix3"] for r in results) / n, 1),
        "errors": sum(1 for r in results if "error" in r),
        "unparsed": sum(1 for r in results if "error" not in r and r["pred"] is None),
        "cost_usd": round(sum(r.get("cost") or 0 for r in results), 5),
        "mean_latency_s": round(sum(lat) / len(lat), 2) if lat else "",
        "details": str(details),
    }
    for t in TIERS:
        sub = [r for r in results if r["tier"] == t]
        row[f"{t}_n"] = len(sub)
        row[f"{t}_pct"] = round(100 * sum(r["exact"] for r in sub) / len(sub), 1) if sub else ""
    report.append_summary(row)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/addresses.csv")
    ap.add_argument("-n", type=int, default=40, help="addresses to sample at random (ignored with --per-tier)")
    ap.add_argument("--per-tier", type=int, default=None,
                    help="sample this many from each difficulty tier (easy/medium/hard) instead")
    ap.add_argument("--tier", choices=TIERS, default=None, help="only sample from one tier")
    ap.add_argument("--seed", type=int, default=None, help="sampling seed (random if omitted)")
    ap.add_argument("--model", nargs="+", default=["google/gemini-3.1-flash-lite"],
                    help="one or more OpenRouter model ids; all get the same sample")
    ap.add_argument("--effort", default=None, choices=["minimal", "low", "medium", "high", "xhigh", "max"],
                    help="reasoning effort (omit for the model's default)")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--max-cost", type=float, default=None,
                    help="stop before starting another model once this run has spent this many USD")
    args = ap.parse_args()

    for m in args.model:
        if SEARCHING_MODELS.search(m):
            sys.exit(f"refusing {m!r}: it has web search built in")
    load_dotenv()  # picks up .env if present; real env vars take precedence
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key or key.startswith("sk-or-v1-your"):
        sys.exit("set OPENROUTER_API_KEY in .env (see .env.example) or your environment")

    with open(args.data, newline="") as f:
        pool = list(csv.DictReader(f))
    if args.tier:
        pool = [r for r in pool if r["tier"] == args.tier]
    seed = args.seed if args.seed is not None else random.randrange(1 << 30)
    if args.per_tier:
        sample = []
        for t in TIERS:
            bucket = [r for r in pool if r["tier"] == t]
            sample += random.Random(f"{seed}:{t}").sample(bucket, min(args.per_tier, len(bucket)))
        label = f"{args.per_tier} per tier, seed {seed}"
    else:
        sample = random.Random(seed).sample(pool, min(args.n, len(pool)))
        label = f"{len(sample)} random{' ' + args.tier if args.tier else ''}, seed {seed}"
    client = openai.OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key, max_retries=5)

    all_failed, spent = True, 0.0
    for model in args.model:
        if args.max_cost is not None and spent >= args.max_cost:
            print(f"\nstopping: spent ${spent:.2f} >= --max-cost ${args.max_cost:.2f}; skipped from {model} on")
            break
        print(f"\n=== {model}  ({label}; effort={args.effort or 'default'})", flush=True)
        with ThreadPoolExecutor(args.concurrency) as ex:
            results = list(ex.map(lambda r: run_one(client, model, args.effort, r), sample))

        for r in results:
            mark = "✓" if r["exact"] else ("~" if r["prefix3"] else "✗")
            note = r.get("error") or (f"unparsed: {r['raw'][:60]!r}" if r["pred"] is None else "")
            print(f" {mark} {r['tier']:6} {r['gold']}  pred={r['pred'] or '-':5}  {r['address']}  {note}")
        if any(r.get("web_annotations") for r in results):
            print("WARNING: some responses carried web citations - results are contaminated")

        row = save_run(model, args.effort, seed, label, results)
        all_failed &= row["errors"] == row["n"]
        spent += row["cost_usd"]
        if any(r.get("out_of_credits") for r in results):
            print("\nstopping: OpenRouter account is out of credits (402). Top up, then re-run; "
                  "this model's row is marked incomplete on the leaderboard.")
            break
        tiers = "  ".join(f"{t} {row[f'{t}_pct']}%" for t in TIERS if row[f"{t}_n"])
        print(f"exact {row['exact']}/{row['n']} = {row['exact_pct']}%   [{tiers}]   "
              f"errors={row['errors']}  cost=${row['cost_usd']:.4f}", flush=True)

    print(f"\nsaved: {report.SUMMARY}, {report.LEADERBOARD_MD}, {report.SITE}, per-item logs in {report.RESULTS / 'runs'}/")
    sys.exit(1 if all_failed else 0)


if __name__ == "__main__":
    main()
