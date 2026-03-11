# Cross-Venue Research

Cross-venue parity is only meaningful if the two markets refer to the same underlying event.

The current repo did not have a market-matching layer, so this workflow adds two stages:

1. automatic pair suggestions from the latest Kalshi and Polymarket snapshots
2. ontology-first strict-match evaluation across all stored snapshots
3. candidate triage into the experiment log and paper queue

## Command

```bash
.venv/bin/python scripts/research_cross_venue_pairs.py \
  --out data/reports/cross_venue_pairs.json
```

With a curated mapping file:

```bash
.venv/bin/python scripts/research_cross_venue_pairs.py \
  --pair-map configs/cross_venue_pairs.example.csv \
  --out data/reports/cross_venue_pairs.json
```

The default path now prefers `configs/contract_ontology.csv`. A manual pair map is only needed when you intentionally want to override ontology-backed matching.

## What The Report Means

- `suggestion_scan`: candidate same-event pairs from the latest snapshots using title-token overlap and close-time proximity
- `ontology_eval`: historical mid/ask/bid gap summaries for ontology-backed strict same-event pairs

## Candidate Triage

After generating the ontology-backed report, push the family through the governed candidate funnel:

```bash
.venv/bin/python scripts/triage_cross_venue_family.py \
  --research-report data/reports/cross_venue_pairs.json \
  --binary-lock-report data/reports/cross_venue_binary_lock.json \
  --out data/reports/cross_venue_pair_lock_triage.json
```

If you want the top variants appended to the family experiment ledger:

```bash
.venv/bin/python scripts/triage_cross_venue_family.py \
  --research-report data/reports/cross_venue_pairs.json \
  --binary-lock-report data/reports/cross_venue_binary_lock.json \
  --log-experiments \
  --out data/reports/cross_venue_pair_lock_triage.json
```

## Paper Tracking The Ranked Shortlist

The tracked-pair fast loop can now consume the triage report directly instead of scanning the full ontology universe:

```bash
.venv/bin/python scripts/run_tracked_pair_fast_loop.py \
  --contract-ontology configs/contract_ontology.csv \
  --triage-report data/reports/cross_venue_pair_lock_triage.json \
  --top-n 5 \
  --iterations 2 \
  --sleep-sec 15
```

That is the preferred path for turning the current best structural candidates into actual return observations.

After the loop has accumulated evidence, tighten the active shortlist with:

```bash
python3 scripts/analyze_pair_lock_fast_loop.py
```

That writes:

- `data/reports/pair_lock_fast_loop_analysis.json`
- `data/reports/pair_lock_fast_loop_pair_summary.csv`
- `data/reports/cross_venue_pair_lock_triage_refined.json`
- `data/reports/cross_venue_pair_lock_scout_candidates.json`

Use the refined triage file to keep dense observation focused on pairs that still show support in the current fast-loop evidence.
Use the scout candidates file as the smaller periodic re-entry set for broader exploration.

## Why Manual Mapping Exists

On current local data, automatic title overlap is weak.
That suggests the market universes do not line up cleanly enough for blind matching.

A curated pair map is therefore the defensible path before any parity claim.
