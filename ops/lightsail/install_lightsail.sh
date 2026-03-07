#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/pred-infra"
SERVICE_NAME="pred-infra-pipeline.service"
TIMER_NAME="pred-infra-pipeline.timer"

echo "[1/7] Install system dependencies..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip logrotate rsync

echo "[2/7] Sync repo to ${APP_DIR}..."
sudo mkdir -p "${APP_DIR}"
sudo rsync -a --delete ./ "${APP_DIR}/"
sudo chown -R ubuntu:ubuntu "${APP_DIR}"

echo "[3/7] Create venv and install package..."
cd "${APP_DIR}"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .

echo "[4/7] Prepare env file..."
if [[ ! -f "${APP_DIR}/.env" ]]; then
  cp "${APP_DIR}/configs/db.env.example" "${APP_DIR}/.env"
  echo "Created ${APP_DIR}/.env from template. Fill real DB credentials."
fi

echo "[5/7] Install systemd unit/timer..."
sudo cp "${APP_DIR}/ops/lightsail/systemd/${SERVICE_NAME}" "/etc/systemd/system/${SERVICE_NAME}"
sudo cp "${APP_DIR}/ops/lightsail/systemd/${TIMER_NAME}" "/etc/systemd/system/${TIMER_NAME}"
sudo systemctl daemon-reload
sudo systemctl enable --now "${TIMER_NAME}"

echo "[6/7] Install logrotate..."
sudo cp "${APP_DIR}/ops/lightsail/logrotate/pred-infra" /etc/logrotate.d/pred-infra

echo "[7/7] Check timer status..."
systemctl status "${TIMER_NAME}" --no-pager || true
systemctl list-timers --all | grep pred-infra || true

echo "lightsail_install=ok"
