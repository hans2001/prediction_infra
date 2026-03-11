#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PAIR_MAP="${PAIR_MAP:-}"
CONTRACT_ONTOLOGY="${CONTRACT_ONTOLOGY:-$ROOT/configs/contract_ontology.csv}"
DEFAULT_REFINED_TRIAGE="$ROOT/data/reports/cross_venue_pair_lock_triage_refined.json"
DEFAULT_TRIAGE="$ROOT/data/reports/cross_venue_pair_lock_triage.json"
TRIAGE_REPORT="${TRIAGE_REPORT:-}"
if [[ -z "$TRIAGE_REPORT" ]]; then
  if [[ -f "$DEFAULT_REFINED_TRIAGE" ]]; then
    TRIAGE_REPORT="$DEFAULT_REFINED_TRIAGE"
  else
    TRIAGE_REPORT="$DEFAULT_TRIAGE"
  fi
fi
TOP_N="${TOP_N:-5}"
ALLOWED_RECOMMENDATIONS="${ALLOWED_RECOMMENDATIONS:-start_paper_tracking,collect_more_paper_evidence,eligible_for_paper_review}"
ITERATIONS="${ITERATIONS:-0}"
SLEEP_SEC="${SLEEP_SEC:-5}"
MIN_SIZE="${MIN_SIZE:-10}"
MAX_TOTAL_COST="${MAX_TOTAL_COST:-0.999}"
LOG_PATH="${LOG_PATH:-$ROOT/data/reports/tracked_pair_fast_loop_long.log}"
SESSION_NAME="${SESSION_NAME:-tracked_pair_fast_loop_triaged}"
CONTINUOUS="${CONTINUOUS:-1}"
INHIBIT_SLEEP="${INHIBIT_SLEEP:-1}"
INHIBIT_WHY="${INHIBIT_WHY:-pred-infra tracked pair fast loop is collecting paper observations}"

mkdir -p "$(dirname "$LOG_PATH")"

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux is required for a persistent local loop" >&2
  exit 1
fi

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  echo "tmux session already exists: $SESSION_NAME" >&2
  exit 1
fi

printf -v CMD "%q " \
  ".venv/bin/python" \
  "scripts/run_tracked_pair_fast_loop.py" \
  "--sleep-sec" "$SLEEP_SEC" \
  "--min-size" "$MIN_SIZE" \
  "--max-total-cost" "$MAX_TOTAL_COST"

if [[ -n "$PAIR_MAP" ]]; then
  printf -v CMD "%s%q %q " "$CMD" "--pair-map" "$PAIR_MAP"
else
  printf -v CMD "%s%q %q " "$CMD" "--contract-ontology" "$CONTRACT_ONTOLOGY"
fi

if [[ -n "$TRIAGE_REPORT" ]]; then
  printf -v CMD "%s%q %q %q %q %q %q " \
    "$CMD" \
    "--triage-report" "$TRIAGE_REPORT" \
    "--top-n" "$TOP_N" \
    "--allowed-recommendations" "$ALLOWED_RECOMMENDATIONS"
fi

if [[ "$CONTINUOUS" == "1" ]]; then
  printf -v CMD "%s%q " "$CMD" "--continuous"
else
  printf -v CMD "%s%q %q " "$CMD" "--iterations" "$ITERATIONS"
fi

if [[ "$INHIBIT_SLEEP" == "1" ]]; then
  if command -v systemd-inhibit >/dev/null 2>&1; then
    printf -v CMD "%q --what=%q --why=%q /usr/bin/bash -lc %q" \
      "systemd-inhibit" \
      "sleep" \
      "$INHIBIT_WHY" \
      "cd '$ROOT' && ${CMD} >> '$LOG_PATH' 2>&1"
    tmux new-session -d -s "$SESSION_NAME" "$CMD"
    echo "$SESSION_NAME"
    exit 0
  else
    echo "warning: systemd-inhibit not found; sleep will not be blocked" >&2
  fi
fi

tmux new-session -d -s "$SESSION_NAME" \
  "cd '$ROOT' && ${CMD} >> '$LOG_PATH' 2>&1"

echo "$SESSION_NAME"
