#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
UNIT_DIR="${HOME}/.config/systemd/user"
UNIT_FILE="${UNIT_DIR}/pred-infra-fast-loop.service"
PYTHON_BIN="${APP_DIR}/.venv/bin/python"
SLEEP_SEC="${1:-5}"
TOP_N="${2:-5}"
REFINED_TRIAGE_REL="data/reports/cross_venue_pair_lock_triage_refined.json"
DEFAULT_TRIAGE_REL="data/reports/cross_venue_pair_lock_triage.json"
TRIAGE_REPORT_REL="${DEFAULT_TRIAGE_REL}"

if [[ -f "${APP_DIR}/${REFINED_TRIAGE_REL}" ]]; then
  TRIAGE_REPORT_REL="${REFINED_TRIAGE_REL}"
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "missing virtualenv python at ${PYTHON_BIN}"
  echo "create it first with: python3 -m venv .venv && .venv/bin/pip install -e . pytest"
  exit 1
fi

mkdir -p "${UNIT_DIR}"

cat > "${UNIT_FILE}" <<EOF
[Unit]
Description=pred-infra triaged tracked pair fast loop
After=default.target

[Service]
Type=simple
WorkingDirectory=${APP_DIR}
ExecStart=/usr/bin/bash -lc 'cd "${APP_DIR}" && "${PYTHON_BIN}" scripts/run_tracked_pair_fast_loop.py --contract-ontology configs/contract_ontology.csv --triage-report ${TRIAGE_REPORT_REL} --top-n ${TOP_N} --sleep-sec ${SLEEP_SEC} --continuous'
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now pred-infra-fast-loop.service

echo "installed local fast loop service"
echo "service: pred-infra-fast-loop.service"
echo "sleep_sec: ${SLEEP_SEC}"
echo "top_n: ${TOP_N}"
echo "triage_report: ${TRIAGE_REPORT_REL}"
echo "note: the user service runs continuously while the machine is awake; use scripts/start_tracked_pair_fast_loop.sh if you need an interactive sleep inhibitor"
systemctl --user status pred-infra-fast-loop.service --no-pager
