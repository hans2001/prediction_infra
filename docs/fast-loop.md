# Fast Loop

This is now the primary evidence engine for the `cross_venue_pair_lock` family.

The daily cron pipeline is still useful for baseline health and broad snapshots, but the fast loop is the path that should accumulate dense observations for shortlist structural candidates.

## Design

1. Use a vetted pair map.
2. Pull Kalshi tracked order books by ticker.
3. Pull Polymarket tracked CLOB books by YES/NO token IDs.
4. Normalize executable YES/NO bid/ask quotes.
5. Run strict binary-lock screening immediately.

## Default Mode

Default local assumptions now are:

- triage-backed shortlist, not the full pair universe
- `top_n=5`
- `sleep_sec=5`
- sleep inhibition enabled while the loop is active

If [data/reports/cross_venue_pair_lock_triage_refined.json](/home/hans2/prediction_infra/data/reports/cross_venue_pair_lock_triage_refined.json) exists, the local launchers now prefer it over the broader triage file.
That lets the loop keep collecting on the currently supported shortlist instead of polling stale candidates.
The refined shortlist is now capped to the strongest deduped candidates by default, so repeated identical polls do not automatically earn more active budget.

## Commands

Fetch one tracked quote snapshot:

```bash
.venv/bin/python scripts/fetch_tracked_pair_quotes.py \
  --pair-map configs/cross_venue_pairs_nhl_metro.seed.csv
```

Run the fast loop once:

```bash
.venv/bin/python scripts/run_tracked_pair_fast_loop.py \
  --pair-map configs/cross_venue_pairs_nhl_metro.seed.csv \
  --iterations 1
```

Run a simple paper-survival check:

```bash
.venv/bin/python scripts/run_tracked_pair_fast_loop.py \
  --pair-map configs/cross_venue_pairs_nhl_metro.seed.csv \
  --iterations 2 \
  --sleep-sec 3 \
  --min-size 10 \
  --max-total-cost 0.999
```

Run the persistent local loop without allowing the machine to sleep:

```bash
bash scripts/start_tracked_pair_fast_loop.sh
```

Install it as a persistent user service:

```bash
bash scripts/install_local_fast_loop.sh 5 5
```

Refresh the active shortlist from current fast-loop evidence:

```bash
python3 scripts/analyze_pair_lock_fast_loop.py
```

The analyzer now keeps two views on purpose:
- raw poll counts, for load/coverage visibility
- effective run-level counts, where consecutive identical quote states collapse into one observation

Refined shortlist selection uses the effective run-level evidence, not raw repeated poll volume.

Refresh pair-level quote-staleness diagnostics for the current kept pairs:

```bash
python3 scripts/analyze_pair_lock_quote_diagnostics.py
python3 scripts/analyze_pair_lock_fast_loop.py
```

That also writes a scout list at [cross_venue_pair_lock_scout_candidates.json](/home/hans2/prediction_infra/data/reports/cross_venue_pair_lock_scout_candidates.json) so broader candidates are not forgotten just because they are no longer in the dense loop.
The quote diagnostics write [pair_lock_quote_diagnostics.json](/home/hans2/prediction_infra/data/reports/pair_lock_quote_diagnostics.json), which is used to demote stale-risk pairs out of the active refined shortlist.

Important:
- a sleeping laptop will suspend the process tree; the loop cannot continue through actual sleep
- the installed user service runs continuously while the machine is awake
- `scripts/start_tracked_pair_fast_loop.sh` uses `systemd-inhibit` when launched interactively, which is the local path that can block sleep while the loop is active
- for uninterrupted overnight collection, use an always-on server

## Why This Scales Better

- no title matching in the hot path
- no full Polymarket universe scan for executable NO quotes
- only tracked pair IDs are polled
- output is immediately usable by the strict binary-lock proof

## Execution Quality

The loop now also:
- captures top-of-book ask sizes for the executable YES and NO legs
- filters out tiny opportunities with `--min-size`
- keeps only candidates under `--max-total-cost`
- drops candidates when the tracked Polymarket book is too old
- treats severe next-snapshot size collapse as a paper miss, even if nominal size stays above the hard minimum
- paper-checks whether a candidate still survives on the next poll
- writes watcher-style pair-lock status and event artifacts for persistence monitoring

Execution realism defaults now include:
- `--max-polymarket-book-age-sec 20`
- `--min-size-survival-ratio 0.6`

That means the paper lane is now explicitly harsher on stale books and fragile size than the earlier raw timeout-survival check.

Watcher-style artifacts emitted by the fast loop:
- `data/reports/pair_lock_watcher_status.json`
- `data/reports/pair_lock_watcher_events.jsonl`
- `data/reports/pair_lock_watcher_opportunities.jsonl`

## Current Limitation

The loop still depends on the slow-path triage artifact.
That is intentional. Matching and ranking belong in the slow path; dense observation belongs in the hot path.

The refined triage file is a narrow execution-time filter, not a replacement for the broader research triage.
The scout file is the re-entry lane for names that should still be checked periodically without consuming the main fast-loop budget.
The quote diagnostics file is the guardrail against mistaking repeated or stale book states for real persistent structural edge.
