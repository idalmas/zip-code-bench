# zip-code-bench

Can a model name the ZIP code of a real US street address from memory, with no tools?

Each model gets a real address such as `2942 Shadow Trail Drive, Houston, TX`. It is sent as one fresh request,
with no history, no tools and no web search, and has to answer with the 5-digit ZIP. Results are in
[`results/LEADERBOARD.md`](results/LEADERBOARD.md), and the same leaderboard is at `site/index.html`.

## Quick start

```bash
cp .env.example .env          # then paste your OpenRouter key
uv run build_dataset.py       # one-time, ~1 min: ~14k real addresses -> data/addresses.csv
uv run run_eval.py --per-tier 40 --seed 7 --model google/gemini-3.1-flash-lite openai/gpt-6-luna
uv run report.py              # rebuild the leaderboard from results/summary.csv
uv run python -m unittest     # answer-parser tests
```

Useful flags for `run_eval.py`:

| Flag | What it does |
|---|---|
| `--model A B C` | Any OpenRouter model IDs. All models get the same sample. |
| `--per-tier N` | Sample N addresses from each difficulty tier. `-n N` samples at random instead. |
| `--tier hard` | Sample only one tier. |
| `--seed S` | Pick the sample. The same seed and dataset give the same addresses. |
| `--effort low` | Reasoning effort, passed through OpenRouter. If omitted, each model uses its own default. |
| `--max-cost 5` | Stop before starting another model once the run has spent this many USD. |

The leaderboard uses `--per-tier 40 --seed 7` (120 addresses).

## How it works

**Data** (`build_dataset.py`).
- Addresses come from the USDOT National Address Database (NAD): official address points collected from state
  and local governments. We read them through the Overture Maps open data release.
- Each point carries its own ZIP and postal city. That ZIP is the answer the model is graded against.
- We keep only plain numeric house numbers with no unit, and only ZIPs that GeoNames confirms exist in the same
  state. Any address recorded with two different ZIPs is dropped.
- Addresses are drawn from 300 random neighborhood-sized chunks of the data, so places with more addresses show up
  more often.

**Tiers.** Each address is tagged by how many ZIPs its city has:

| Tier | City has | Why it matters |
|---|---|---|
| easy | 1 ZIP | Knowing the town is enough. |
| medium | 2-9 ZIPs | You need to know roughly where in town the street is. |
| hard | 10+ ZIPs | Big cities, where you need street-level knowledge. |

**Grading** (`run_eval.py`).
- The answer is the last 5-digit number in the reply, so "ZIP: 14850", "14850-1234" and "not 77450, it's 77449"
  all parse. The address's own house number is skipped.
- `exact` means all 5 digits match, and it is the headline score. `first 3` means the first 3 digits match, i.e.
  the same USPS regional sorting center.
- A reply with no 5-digit number counts as wrong. This includes refusals and models that run out of tokens while
  reasoning.
- If any request in a run fails (API error, out of credits), that run is left off the leaderboard. It is still
  recorded in `results/summary.csv`. Gemini 3.1 Pro, DeepSeek V4 Pro, Mistral Medium 3.5 and Kimi K3 are missing for
  this reason: the account ran out of credits partway through their runs.

**Outputs** (`report.py`). Every run is written to disk:
- `results/summary.csv` is the permanent record, with one row per model per run.
- `results/runs/*.jsonl` holds every reply, parsed answer, cost and latency.
- `results/LEADERBOARD.md` and `site/index.html` are generated from the summary after every model.

## Limitations

- **Sample size.** With 120 addresses, overall scores are about ±9 points at 95% confidence, and each tier (40
  addresses) about ±15. Only large gaps are meaningful. Ranks in the middle of the table can reshuffle on another
  seed.
- **Missing states.** NAD has no data for several states, including California, Georgia, Michigan, Massachusetts,
  Colorado, Oregon and Nevada, and Florida and Minnesota are thin. Scores say nothing about those states.
- **Some expected ZIPs may be wrong.** They come from local government records and were not checked against USPS. In
  6 of the 120 leaderboard addresses, nearly every model agrees on a different ZIP. Several of these sit on ZIP
  boundaries, such as Richmond St in Appleton, WI, or in townships that use neighboring towns' ZIPs. Each one costs
  every model about 0.8 points, so absolute scores are slightly low, but the ranking is barely affected.
- **Tier boundaries are approximate.** City ZIP counts come from GeoNames, which includes PO-box-only and
  single-business ZIPs. Some "medium" towns really have one ZIP for street addresses, which makes that tier a bit
  easier than its label suggests.
- **The city is in the prompt.** That is how real addresses are written, but it makes one-ZIP towns trivial, which
  is why scores are split by tier.
- **The prompt asks for a best guess.** Models are told to guess when unsure, so the benchmark measures recall, not
  whether a model knows when to say it doesn't know.
- **Memorized address or street knowledge?** The benchmark can't yet tell these apart. Every house number is real;
  a planned control with real streets and made-up house numbers would separate the two.
- **One sample per address,** at each provider's default temperature, so there is some run-to-run noise. "Default"
  effort also means different things for different models: some reason by default and others don't.
- **The pool depends on Overture's data.** The build reads Overture release `2026-09-23.0`. Overture removes old
  releases after a while, and once this one is gone, a rebuild from a newer release will give a different set of
  addresses.

## Data sources and credits

- **Addresses:** [USDOT National Address Database](https://www.transportation.gov/gis/national-address-database),
  US public domain, accessed through the [Overture Maps Foundation](https://overturemaps.org) addresses theme
  (release `2026-09-23.0`). Each record's source and license are listed in its `sources` field. The NAD records
  used here are public domain.
- **ZIP to city/state table:** [GeoNames](https://www.geonames.org) postal codes, licensed
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). It is used to validate ZIPs and assign tiers.
- **Models:** called through [OpenRouter](https://openrouter.ai). Costs on the leaderboard are what OpenRouter
  billed.

The address pool (`data/`) is not committed: rebuild it with `uv run build_dataset.py`. It contains real
residential addresses from public records, with no names or other personal details.

## License

Code is MIT-licensed (see [LICENSE](LICENSE)). Data keeps its original licenses (see above).
