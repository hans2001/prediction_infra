#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import deque
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pred_infra.storage.postgres import load_db_url, prepare_runtime_db_url  # noqa: E402
from pred_infra.storage.runtime_state import (  # noqa: E402
    count_pipeline_metrics,
    fetch_latest_pipeline_run,
    fetch_recent_pipeline_metrics,
)

try:
    import psycopg
except ModuleNotFoundError:  # pragma: no cover - optional dependency behavior
    psycopg = None


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>pred-infra control tower</title>
  <style>
    :root {
      --bg: #071018;
      --bg-2: #0b1723;
      --panel: rgba(14, 26, 39, 0.88);
      --panel-2: rgba(9, 18, 28, 0.92);
      --border: rgba(137, 163, 186, 0.18);
      --text: #edf5fb;
      --muted: #8ea5b8;
      --ok: #31d97c;
      --warn: #ffbd54;
      --bad: #ff6969;
      --live: #57b6ff;
      --accent: #92f0d6;
      --shadow: 0 20px 50px rgba(0, 0, 0, 0.32);
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(87, 182, 255, 0.18), transparent 22%),
        radial-gradient(circle at top right, rgba(146, 240, 214, 0.16), transparent 24%),
        linear-gradient(180deg, var(--bg) 0%, var(--bg-2) 100%);
      min-height: 100vh;
      overflow-x: hidden;
    }

    .shell {
      max-width: 1400px;
      margin: 0 auto;
      padding: 28px 20px 48px;
      overflow-x: clip;
    }

    .hero, .section-head, .banner, .kpi-grid, .grid-2, .grid-3 {
      display: grid;
      gap: 16px;
    }

    .hero > *,
    .section-head > *,
    .banner > *,
    .kpi-grid > *,
    .grid-2 > *,
    .grid-3 > * {
      min-width: 0;
    }

    .hero {
      grid-template-columns: 1.5fr 1fr;
      align-items: end;
      margin-bottom: 18px;
    }

    h1, h2, h3, p { margin: 0; }
    h1 {
      font-size: clamp(2.2rem, 4.5vw, 4rem);
      line-height: 0.94;
      letter-spacing: -0.05em;
    }

    .hero p {
      color: var(--muted);
      margin-top: 10px;
      max-width: 760px;
      line-height: 1.5;
    }

    .hero-meta {
      justify-self: end;
      text-align: right;
      color: var(--muted);
      font-size: 0.94rem;
    }

    .card, .panel, .banner {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 20px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
      min-width: 0;
      overflow: hidden;
    }

    .banner {
      grid-template-columns: auto 1fr auto;
      align-items: center;
      padding: 16px 18px;
      margin-bottom: 18px;
    }

    .banner-title {
      font-size: 1.15rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .banner-copy {
      color: var(--muted);
      line-height: 1.45;
    }

    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 9px;
      border-radius: 999px;
      padding: 8px 14px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      white-space: nowrap;
    }

    .status-pill::before {
      content: "";
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: currentColor;
      box-shadow: 0 0 18px currentColor;
    }

    .healthy { color: var(--ok); background: rgba(49, 217, 124, 0.12); }
    .running { color: var(--live); background: rgba(87, 182, 255, 0.12); }
    .stale { color: var(--warn); background: rgba(255, 189, 84, 0.14); }
    .failed { color: var(--bad); background: rgba(255, 105, 105, 0.14); }
    .unknown { color: var(--muted); background: rgba(142, 165, 184, 0.12); }

    .kpi-grid {
      grid-template-columns: repeat(4, minmax(0, 1fr));
      margin-bottom: 18px;
    }

    .card, .panel {
      padding: 18px;
    }

    .label {
      color: var(--muted);
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      margin-bottom: 10px;
    }

    .value {
      font-size: 1.45rem;
      font-weight: 650;
      line-height: 1.15;
      overflow-wrap: anywhere;
      word-break: break-word;
    }

    .subvalue {
      color: var(--muted);
      margin-top: 8px;
      font-size: 0.92rem;
      line-height: 1.4;
      overflow-wrap: anywhere;
      word-break: break-word;
    }

    .grid-2 { grid-template-columns: 1.15fr 0.85fr; margin-bottom: 18px; }
    .grid-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); margin-bottom: 18px; }

    .section-head {
      grid-template-columns: 1fr auto;
      align-items: center;
      margin-bottom: 14px;
    }

    h2 {
      font-size: 1rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .section-meta {
      color: var(--muted);
      font-size: 0.9rem;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.95rem;
      table-layout: fixed;
    }

    th, td {
      text-align: left;
      padding: 10px 0;
      border-bottom: 1px solid rgba(137, 163, 186, 0.12);
      vertical-align: top;
      overflow-wrap: anywhere;
      word-break: break-word;
    }

    th {
      color: var(--muted);
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-weight: 600;
      width: 30%;
    }

    .mono {
      font-family: "IBM Plex Mono", "SFMono-Regular", monospace;
      font-size: 0.84rem;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      word-break: break-word;
    }

    .hint {
      color: var(--muted);
      line-height: 1.45;
      font-size: 0.93rem;
    }

    .artifact {
      border: 1px solid rgba(137, 163, 186, 0.12);
      border-radius: 14px;
      padding: 14px;
      background: var(--panel-2);
      min-width: 0;
      overflow: hidden;
    }

    .artifact h3 {
      font-size: 0.92rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 10px;
    }

    .artifact .path {
      color: var(--accent);
      word-break: break-all;
    }

    .artifact .body {
      color: var(--muted);
      line-height: 1.45;
      margin-top: 8px;
      font-size: 0.92rem;
      overflow-wrap: anywhere;
      word-break: break-word;
    }

    .callout {
      padding: 14px 16px;
      border-radius: 14px;
      border: 1px solid rgba(137, 163, 186, 0.12);
      background: var(--panel-2);
      line-height: 1.45;
      color: var(--muted);
      margin-bottom: 12px;
      overflow-wrap: anywhere;
      word-break: break-word;
    }

    pre {
      margin: 0;
      padding: 16px;
      border-radius: 16px;
      background: #03111b;
      color: #d8f8ea;
      overflow-x: hidden;
      overflow-y: auto;
      max-height: 500px;
      border: 1px solid rgba(146, 240, 214, 0.14);
      font-family: "IBM Plex Mono", "SFMono-Regular", monospace;
      font-size: 0.84rem;
      line-height: 1.45;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      word-break: break-word;
    }

    .small-pill {
      display: inline-block;
      padding: 4px 8px;
      border-radius: 999px;
      background: rgba(137, 163, 186, 0.12);
      color: var(--text);
      font-size: 0.8rem;
      white-space: nowrap;
    }

    a {
      color: var(--accent);
      text-decoration: none;
      overflow-wrap: anywhere;
      word-break: break-word;
    }

    @media (max-width: 1100px) {
      .hero, .grid-2, .grid-3 { grid-template-columns: 1fr; }
      .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .hero-meta { justify-self: start; text-align: left; }
    }

    @media (max-width: 700px) {
      .kpi-grid { grid-template-columns: 1fr; }
      .banner { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <div class="hero">
      <div>
        <h1>Pred-Infra Control Tower</h1>
        <p>Live operational view for the daily cron pipeline and the tracked pair-lock shortlist loop. This page reads machine-written run state, metrics history, report artifacts, and the scheduler log so the distinction between scheduler health and structural-candidate collection stays explicit.</p>
      </div>
      <div class="hero-meta">
        <div id="streamStatus">stream: connecting</div>
        <div>display timezone: America/New_York</div>
        <div id="refreshStamp">waiting for first payload</div>
      </div>
    </div>

    <div class="banner" id="banner">
      <div class="banner-title" id="bannerTitle">Scheduler Status</div>
      <div class="banner-copy" id="bannerCopy">Waiting for monitor payload.</div>
      <div><span class="status-pill unknown" id="bannerPill">unknown</span></div>
    </div>

    <div class="kpi-grid">
      <div class="card">
        <div class="label">Health</div>
        <div class="value" id="healthText">n/a</div>
        <div class="subvalue" id="healthSub">n/a</div>
      </div>
      <div class="card">
        <div class="label">Current Step</div>
        <div class="value" id="currentStep">idle</div>
        <div class="subvalue" id="currentStepSub">no active run</div>
      </div>
      <div class="card">
        <div class="label">Last Success</div>
        <div class="value" id="lastSuccess">n/a</div>
        <div class="subvalue" id="lastSuccessSub">n/a</div>
      </div>
      <div class="card">
        <div class="label">Next Expected Run</div>
        <div class="value" id="nextExpected">n/a</div>
        <div class="subvalue" id="nextExpectedSub">n/a</div>
      </div>
      <div class="card">
        <div class="label">Schedule Drift</div>
        <div class="value" id="scheduleDrift">n/a</div>
        <div class="subvalue" id="scheduleDriftSub">n/a</div>
      </div>
      <div class="card">
        <div class="label">Last Run Total</div>
        <div class="value" id="lastRunTotal">n/a</div>
        <div class="subvalue" id="lastRunTotalSub">n/a</div>
      </div>
      <div class="card">
        <div class="label">Watcher Health</div>
        <div class="value" id="watcherHealth">n/a</div>
        <div class="subvalue" id="watcherHealthSub">n/a</div>
      </div>
      <div class="card">
        <div class="label">Watcher Decision</div>
        <div class="value" id="watcherDecision">n/a</div>
        <div class="subvalue" id="watcherDecisionSub">n/a</div>
      </div>
      <div class="card">
        <div class="label">Scheduled Paper Obs</div>
        <div class="value" id="scheduledPaperObs">n/a</div>
        <div class="subvalue" id="scheduledPaperObsSub">cron and baseline paper rows</div>
      </div>
      <div class="card">
        <div class="label">Total Watcher Cycles</div>
        <div class="value" id="totalWatcherCycles">n/a</div>
        <div class="subvalue" id="totalWatcherCyclesSub">watcher history</div>
      </div>
      <div class="card">
        <div class="label">Pair-Lock Obs</div>
        <div class="value" id="pairLockObs">n/a</div>
        <div class="subvalue" id="pairLockObsSub">tracked shortlist evidence</div>
      </div>
      <div class="card">
        <div class="label">Tracked Loop</div>
        <div class="value" id="trackedLoopHealth">n/a</div>
        <div class="subvalue" id="trackedLoopHealthSub">latest pair-lock paper run</div>
      </div>
    </div>

    <div class="grid-2">
      <div class="panel">
        <div class="section-head">
          <h2>Operator Readout</h2>
          <div class="section-meta" id="operatorMeta">waiting</div>
        </div>
        <div class="callout" id="operatorSummary">Waiting for first payload.</div>
        <table>
          <tbody id="detailsBody"></tbody>
        </table>
      </div>

      <div class="panel">
        <div class="section-head">
          <h2>How To Read This</h2>
          <div class="section-meta">operational interpretation</div>
        </div>
        <div class="callout"><strong>Running</strong> means cron fired and the pipeline is mid-flight. Watch <span class="mono">Current Step</span>, <span class="mono">Last Output</span>, and the log tail.</div>
        <div class="callout"><strong>On schedule</strong> means the last successful run completed within the expected interval window. This is the default healthy state between cron executions.</div>
        <div class="callout"><strong>Overdue</strong> means no recent success landed on time. First check whether cron fired, then inspect the latest error, log tail, and recent run history.</div>
        <div class="callout"><strong>Failed</strong> means the latest run exited non-zero. The root cause is usually visible in <span class="mono">Last Error</span> and the last 20-50 lines of the log.</div>
      </div>
    </div>

    <div class="grid-2">
      <div class="panel">
        <div class="section-head">
          <h2>Step Timeline</h2>
          <div class="section-meta">latest run only</div>
        </div>
        <table>
          <thead>
            <tr><th>Step</th><th>Status</th><th>Finished</th><th>Duration</th></tr>
          </thead>
          <tbody id="stepsBody"></tbody>
        </table>
      </div>

      <div class="panel">
        <div class="section-head">
          <h2>Recent Runs</h2>
          <div class="section-meta" id="runsMeta">latest history</div>
        </div>
        <table>
          <thead>
            <tr><th>Timestamp</th><th>Status</th><th>Total</th><th>Executed Steps</th></tr>
          </thead>
          <tbody id="runsBody"></tbody>
        </table>
      </div>
    </div>

    <div class="grid-2">
      <div class="panel">
        <div class="section-head">
          <h2>Tracked Pair Loop</h2>
          <div class="section-meta" id="trackedLoopMeta">triaged shortlist monitor</div>
        </div>
        <div class="callout" id="trackedLoopSummary">Tracked pair loop data not available yet.</div>
        <table>
          <tbody id="trackedLoopDetailsBody"></tbody>
        </table>
      </div>

      <div class="panel">
        <div class="section-head">
          <h2>Top Pair-Lock Candidates</h2>
          <div class="section-meta">from current triage report</div>
        </div>
        <table>
          <thead>
            <tr><th>Pair</th><th>Recommendation</th><th>Lock Edge</th><th>Obs</th></tr>
          </thead>
          <tbody id="triageCandidatesBody"></tbody>
        </table>
      </div>
    </div>

    <div class="grid-2">
      <div class="panel">
        <div class="section-head">
          <h2>Scout Re-Entry Candidates</h2>
          <div class="section-meta">from scout candidate file</div>
        </div>
        <table>
          <thead>
            <tr><th>Pair</th><th>Recommendation</th><th>Lock Edge</th><th>Obs</th></tr>
          </thead>
          <tbody id="scoutCandidatesBody"></tbody>
        </table>
      </div>
    </div>

    <div class="grid-2">
      <div class="panel">
        <div class="section-head">
          <h2>Quote Diagnostics</h2>
          <div class="section-meta">stale-risk review</div>
        </div>
        <table>
          <thead>
            <tr><th>Pair</th><th>Risk</th><th>Reason</th><th>Same-State Run</th></tr>
          </thead>
          <tbody id="quoteDiagnosticsBody"></tbody>
        </table>
      </div>
    </div>

    <div class="grid-2">
      <div class="panel">
        <div class="section-head">
          <h2>Watcher Status</h2>
          <div class="section-meta" id="watcherMeta">paper-only signal loop</div>
        </div>
        <div class="callout" id="watcherSummary">Watcher data not available yet.</div>
        <table>
          <tbody id="watcherDetailsBody"></tbody>
        </table>
      </div>

      <div class="panel">
        <div class="section-head">
          <h2>Recent Watcher Cycles</h2>
          <div class="section-meta">latest event log rows</div>
        </div>
        <table>
          <thead>
            <tr><th>Timestamp</th><th>Decision</th><th>Reason</th><th>Candidates</th><th>Best Edge</th></tr>
          </thead>
          <tbody id="watcherEventsBody"></tbody>
        </table>
      </div>
    </div>

    <div class="grid-3">
      <div class="artifact">
        <h3>Latest Integrity Report</h3>
        <div class="path" id="integrityPath">n/a</div>
        <div class="body" id="integrityBody">Waiting for artifact discovery.</div>
      </div>
      <div class="artifact">
        <h3>Latest Probability Report</h3>
        <div class="path" id="probabilityPath">n/a</div>
        <div class="body" id="probabilityBody">Waiting for artifact discovery.</div>
      </div>
      <div class="artifact">
        <h3>Latest Validation Report</h3>
        <div class="path" id="validationPath">n/a</div>
        <div class="body" id="validationBody">Waiting for artifact discovery.</div>
      </div>
    </div>

    <div class="grid-2">
      <div class="panel">
        <div class="section-head">
          <h2>Recent Metrics</h2>
          <div class="section-meta">history from pipeline_state.db</div>
        </div>
        <table>
          <thead>
            <tr><th>Timestamp</th><th>Total</th><th>Step Count</th><th>Longest Step</th></tr>
          </thead>
          <tbody id="metricsBody"></tbody>
        </table>
      </div>

      <div class="panel">
        <div class="section-head">
          <h2>Live Log Tail</h2>
          <div class="section-meta" id="logMeta">tailing log</div>
        </div>
        <pre id="logTail">Waiting for log output.</pre>
      </div>
    </div>
  </div>

  <script>
    let stream;
    let fallbackPoll;
    const DISPLAY_TIME_ZONE = "America/New_York";

    function fmtDate(value) {
      if (!value) return "n/a";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return value;
      return date.toLocaleString([], {
        hour12: false,
        timeZone: DISPLAY_TIME_ZONE,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        timeZoneName: "short",
      });
    }

    function fmtSecs(value) {
      if (value === null || value === undefined) return "n/a";
      const num = Number(value);
      if (!Number.isFinite(num)) return "n/a";
      if (num < 60) return `${num.toFixed(1)}s`;
      const mins = Math.floor(num / 60);
      const secs = Math.round(num % 60);
      return `${mins}m ${secs}s`;
    }

    function fmtMaybePct(value) {
      if (value === null || value === undefined) return "n/a";
      const num = Number(value);
      if (!Number.isFinite(num)) return "n/a";
      return `${(num * 100).toFixed(1)}%`;
    }

    function ago(value) {
      if (value === null || value === undefined) return "n/a";
      return `${fmtSecs(value)} ago`;
    }

    function pickClass(name) {
      if (name === "active") return "healthy";
      if (name === "waiting_for_fills") return "stale";
      if (name === "missing") return "failed";
      return ["healthy", "running", "stale", "failed"].includes(name) ? name : "unknown";
    }

    function renderBanner(derived) {
      const title = document.getElementById("bannerTitle");
      const copy = document.getElementById("bannerCopy");
      const pill = document.getElementById("bannerPill");
      const klass = pickClass(derived.health);
      pill.className = `status-pill ${klass}`;
      pill.textContent = derived.health_text || "unknown";
      if (derived.health === "running") {
        title.textContent = "Run In Progress";
        copy.textContent = "Cron fired and the pipeline is actively executing. Watch current step, last output, and the log tail for live movement.";
      } else if (derived.health === "healthy") {
        title.textContent = "Scheduler Healthy";
        copy.textContent = "Latest full run completed on time. Between scheduled runs, this is the normal resting state.";
      } else if (derived.health === "stale") {
        title.textContent = "Scheduler Overdue";
        copy.textContent = "The expected run window passed without a fresh success. Check cron firing, service health, and any failure evidence below.";
      } else if (derived.health === "failed") {
        title.textContent = "Latest Run Failed";
        copy.textContent = "The most recent pipeline exited non-zero. Inspect last error, step timeline, and log tail immediately.";
      } else {
        title.textContent = "Scheduler Status";
        copy.textContent = "State is unknown. Usually this means the monitor has not yet seen a completed run artifact.";
      }
    }

    function renderKpis(payload) {
      const status = payload.status || {};
      const derived = payload.derived || {};
      const watcher = payload.watcher_status || {};
      const counts = payload.counts || {};
      const tracked = payload.tracked_pair_loop || {};
      document.getElementById("healthText").textContent = derived.health_text || "n/a";
      document.getElementById("healthSub").textContent = `state=${status.status || "unknown"} | updated ${ago(derived.seconds_since_update)}`;
      document.getElementById("currentStep").textContent = status.current_step || "idle";
      document.getElementById("currentStepSub").textContent = status.last_output_line || "no active output";
      document.getElementById("lastSuccess").textContent = fmtDate(status.last_success_at_utc);
      document.getElementById("lastSuccessSub").textContent = ago(derived.seconds_since_last_success);
      document.getElementById("nextExpected").textContent = fmtDate(derived.next_expected_run_utc);
      document.getElementById("nextExpectedSub").textContent = derived.until_next_expected_run_seconds >= 0 ? `due in ${fmtSecs(derived.until_next_expected_run_seconds)}` : `late by ${fmtSecs(Math.abs(derived.until_next_expected_run_seconds || 0))}`;
      document.getElementById("scheduleDrift").textContent = fmtSecs(derived.schedule_drift_seconds);
      document.getElementById("scheduleDriftSub").textContent = derived.health === "stale" ? "outside expected window" : "within expected window";
      document.getElementById("lastRunTotal").textContent = fmtSecs(status.total_sec);
      document.getElementById("lastRunTotalSub").textContent = `run_id=${status.run_id || "n/a"}`;
      document.getElementById("watcherHealth").textContent = watcher.health || watcher.status || "n/a";
      document.getElementById("watcherHealthSub").textContent = watcher.updated_at_utc ? `updated ${fmtDate(watcher.updated_at_utc)}` : "watcher not started";
      document.getElementById("watcherDecision").textContent = watcher.last_decision || "n/a";
      document.getElementById("watcherDecisionSub").textContent = watcher.last_reason_code || "no watcher decision yet";
      document.getElementById("scheduledPaperObs").textContent = counts.scheduled_paper_observations ?? "n/a";
      document.getElementById("scheduledPaperObsSub").textContent = counts.total_pipeline_runs ? `${counts.total_pipeline_runs} pipeline runs stored` : "no pipeline rows yet";
      document.getElementById("totalWatcherCycles").textContent = counts.total_watcher_cycles ?? "n/a";
      document.getElementById("totalWatcherCyclesSub").textContent = counts.total_watcher_cycles ? "persisted watcher cycle rows" : "no watcher cycles yet";
      document.getElementById("pairLockObs").textContent = tracked.pair_lock_observations ?? "n/a";
      document.getElementById("pairLockObsSub").textContent = tracked.triage_candidate_count ? `${tracked.triage_candidate_count} triaged candidates` : "no triage candidates yet";
      document.getElementById("trackedLoopHealth").textContent = tracked.health || "n/a";
      document.getElementById("trackedLoopHealthSub").textContent = tracked.latest_report_path || "no tracked pair report yet";
    }

    function renderDetails(payload) {
      const status = payload.status || {};
      const derived = payload.derived || {};
      const returnsSummary = payload.returns_summary || {};
      const strategyCounts = returnsSummary.strategy_counts || {};
      document.getElementById("operatorMeta").textContent = `expected interval ${derived.expected_interval_minutes || "n/a"} min`;
      document.getElementById("operatorSummary").textContent = derived.operator_summary || "No summary available.";
      const rows = [
        ["Run ID", status.run_id || "n/a"],
        ["Run Status", status.status || "n/a"],
        ["Started", fmtDate(status.started_at_utc)],
        ["Updated", fmtDate(status.updated_at_utc)],
        ["Finished", fmtDate(status.finished_at_utc)],
        ["Last Error", status.last_error || "none"],
        ["Last Output", status.last_output_line || "none"],
        ["Scheduled Paper Observations", returnsSummary.scheduled_observations ?? "n/a"],
        ["Fast-Loop Paper Observations", returnsSummary.fast_loop_observations ?? "n/a"],
        ["All Non-Bootstrap Observations", returnsSummary.total_observations ?? "n/a"],
        ["Strategy Counts", Object.entries(strategyCounts).map(([k, v]) => `${k}:${v}`).join(" | ") || "none"],
        ["Current Command", (status.current_command || []).join(" ") || "none"],
        ["Host / PID", `${status.hostname || "n/a"} / ${status.pid || "n/a"}`],
        ["Expected Interval", `${derived.expected_interval_minutes || "n/a"} min`],
      ];
      document.getElementById("detailsBody").innerHTML = rows.map(
        ([label, value]) => `<tr><th>${label}</th><td class="${label.includes("Command") || label.includes("Output") ? "mono" : ""}">${value}</td></tr>`
      ).join("");
    }

    function renderSteps(steps) {
      const body = document.getElementById("stepsBody");
      if (!steps.length) {
        body.innerHTML = '<tr><td colspan="4">no completed steps yet</td></tr>';
        return;
      }
      body.innerHTML = steps.map((step) => {
        const klass = pickClass(step.status === "success" ? "healthy" : step.status);
        const label = step.status === "success" ? "ok" : step.status;
        return `<tr><td>${step.step}</td><td><span class="small-pill ${klass}">${label}</span></td><td>${fmtDate(step.finished_at_utc)}</td><td>${fmtSecs(step.duration_sec)}</td></tr>`;
      }).join("");
    }

    function renderRuns(runs) {
      const body = document.getElementById("runsBody");
      document.getElementById("runsMeta").textContent = `${runs.length} recent rows`;
      if (!runs.length) {
        body.innerHTML = '<tr><td colspan="4">no run history yet</td></tr>';
        return;
      }
      body.innerHTML = runs.map((run) => {
        const klass = pickClass(run.health_hint || (run.status === "success" ? "healthy" : run.status));
        return `<tr><td>${fmtDate(run.timestamp_utc)}</td><td><span class="small-pill ${klass}">${run.status}</span></td><td>${fmtSecs(run.total_sec)}</td><td>${run.executed_steps.join(", ")}</td></tr>`;
      }).join("");
    }

    function renderWatcher(payload) {
      const watcher = payload.watcher_status || {};
      const events = payload.watcher_events || [];
      document.getElementById("watcherMeta").textContent = watcher.interval_seconds ? `interval ${watcher.interval_seconds}s` : "paper-only signal loop";
      document.getElementById("watcherSummary").textContent = watcher.operator_summary || "Watcher status file not found yet. Install and start the watcher service to populate this panel.";
      const rows = [
        ["Status", watcher.status || "n/a"],
        ["Health", watcher.health || "n/a"],
        ["Last Decision", watcher.last_decision || "n/a"],
        ["Last Reason", watcher.last_reason_code || "n/a"],
        ["Last Candidate Count", watcher.last_candidate_count ?? "n/a"],
        ["Last Best Edge", watcher.last_best_edge ?? "n/a"],
        ["Last Net Return", watcher.last_net_return ?? "n/a"],
        ["Consecutive Failures", watcher.consecutive_failures ?? "n/a"],
        ["Last Success", fmtDate(watcher.last_success_at_utc)],
        ["Last Error", watcher.last_error || "none"],
      ];
      document.getElementById("watcherDetailsBody").innerHTML = rows.map(
        ([label, value]) => `<tr><th>${label}</th><td>${value}</td></tr>`
      ).join("");

      const body = document.getElementById("watcherEventsBody");
      if (!events.length) {
        body.innerHTML = '<tr><td colspan="5">no watcher events available</td></tr>';
        return;
      }
      body.innerHTML = events.map((event) => `<tr><td>${fmtDate(event.timestamp_utc)}</td><td>${event.decision || "n/a"}</td><td>${event.reason_code || "n/a"}</td><td>${event.candidate_count ?? "n/a"}</td><td>${event.best_edge ?? "n/a"}</td></tr>`).join("");
    }

    function renderTrackedPairLoop(payload) {
      const tracked = payload.tracked_pair_loop || {};
      document.getElementById("trackedLoopMeta").textContent = tracked.latest_report_path ? `latest report ${tracked.latest_report_path}` : "triaged shortlist monitor";
      document.getElementById("trackedLoopSummary").textContent = tracked.operator_summary || "Tracked pair loop data not available yet.";
      const details = [
        ["Health", tracked.health || "n/a"],
        ["Pair-Lock Obs", tracked.pair_lock_observations ?? "n/a"],
        ["Triaged Candidates", tracked.triage_candidate_count ?? "n/a"],
        ["Scout Candidates", tracked.scout_candidate_count ?? "n/a"],
        ["Quote Review-Now Pairs", tracked.quote_review_now_count ?? "n/a"],
        ["Quote Watch Pairs", tracked.quote_watch_count ?? "n/a"],
        ["Latest Provable Locks", tracked.latest_summary?.provable_lock_count ?? "n/a"],
        ["Latest Paper Fills", tracked.latest_paper_execution_summary?.filled_count ?? "n/a"],
        ["Latest Mean Realized Edge", tracked.latest_paper_execution_summary?.mean_realized_net_edge ?? "n/a"],
        ["Triage Report", tracked.triage_path || "n/a"],
        ["Scout File", tracked.scout_path || "n/a"],
        ["Quote Diagnostics", tracked.quote_diagnostics_path || "n/a"],
        ["Candidate Ledger", tracked.candidate_ledger_path || "n/a"],
        ["Paper Ledger", tracked.paper_ledger_path || "n/a"],
      ];
      document.getElementById("trackedLoopDetailsBody").innerHTML = details.map(
        ([label, value]) => `<tr><th>${label}</th><td class="${String(value).includes("/") ? "mono" : ""}">${value}</td></tr>`
      ).join("");

      const candidates = tracked.selected_candidates || [];
      const body = document.getElementById("triageCandidatesBody");
      if (!candidates.length) {
        body.innerHTML = '<tr><td colspan="4">no triage candidates yet</td></tr>';
      } else {
        body.innerHTML = candidates.map((row) => `<tr><td>${row.pair_id || "n/a"}</td><td>${row.recommendation || "n/a"}</td><td>${row.best_lock_edge ?? "n/a"}</td><td>${row.observations ?? "n/a"}</td></tr>`).join("");
      }

      const scoutCandidates = tracked.scout_candidates || [];
      const scoutBody = document.getElementById("scoutCandidatesBody");
      if (!scoutCandidates.length) {
        scoutBody.innerHTML = '<tr><td colspan="4">no scout candidates yet</td></tr>';
      } else {
        scoutBody.innerHTML = scoutCandidates.map((row) => `<tr><td>${row.pair_id || "n/a"}</td><td>${row.recommendation || "n/a"}</td><td>${row.best_lock_edge ?? "n/a"}</td><td>${row.observations ?? "n/a"}</td></tr>`).join("");
      }

      const diagnostics = tracked.quote_diagnostics || [];
      const diagnosticsBody = document.getElementById("quoteDiagnosticsBody");
      if (!diagnostics.length) {
        diagnosticsBody.innerHTML = '<tr><td colspan="4">no quote diagnostics yet</td></tr>';
        return;
      }
      diagnosticsBody.innerHTML = diagnostics.map((row) => `<tr><td>${row.pair_id || "n/a"}</td><td>${row.stale_risk || "n/a"}</td><td>${row.stale_reason || "n/a"}</td><td>${row.longest_identical_state_run ?? "n/a"}</td></tr>`).join("");
    }

    function renderArtifacts(artifacts) {
      const integrity = artifacts.integrity || {};
      const probability = artifacts.probability || {};
      const validation = artifacts.validation || {};
      document.getElementById("integrityPath").textContent = integrity.path || "n/a";
      document.getElementById("integrityBody").textContent = integrity.summary || "No integrity report found.";
      document.getElementById("probabilityPath").textContent = probability.path || "n/a";
      document.getElementById("probabilityBody").textContent = probability.summary || "No probability report found.";
      document.getElementById("validationPath").textContent = validation.path || "n/a";
      document.getElementById("validationBody").textContent = validation.summary || "No validation report found.";
    }

    function renderMetrics(metrics) {
      const body = document.getElementById("metricsBody");
      if (!metrics.length) {
        body.innerHTML = '<tr><td colspan="4">no metrics available</td></tr>';
        return;
      }
      body.innerHTML = metrics.map((row) => {
        const steps = Object.entries(row.timings_sec || {});
        steps.sort((a, b) => b[1] - a[1]);
        const longest = steps[0] ? `${steps[0][0]} (${fmtSecs(steps[0][1])})` : "n/a";
        return `<tr><td>${fmtDate(row.timestamp_utc)}</td><td>${fmtSecs(row.total_sec)}</td><td>${steps.length}</td><td>${longest}</td></tr>`;
      }).join("");
    }

    function renderLog(payload) {
      document.getElementById("logTail").textContent = payload.log_tail || "log file empty";
      document.getElementById("logMeta").textContent = `last ${payload.log_line_count || 0} lines`;
    }

    function render(payload) {
      renderBanner(payload.derived || {});
      renderKpis(payload);
      renderDetails(payload);
      renderSteps((payload.status || {}).completed_steps || []);
      renderRuns(payload.recent_runs || []);
      renderArtifacts(payload.latest_artifacts || {});
      renderMetrics(payload.metrics || []);
      renderTrackedPairLoop(payload);
      renderWatcher(payload);
      renderLog(payload);
      document.getElementById("refreshStamp").textContent = `last payload ${new Date().toLocaleTimeString()}`;
    }

    async function fetchSnapshot() {
      const response = await fetch("/api/monitor?log_lines=140&metric_limit=10&run_limit=10", { cache: "no-store" });
      render(await response.json());
    }

    function startFallbackPolling() {
      if (fallbackPoll) return;
      fallbackPoll = setInterval(fetchSnapshot, 3000);
    }

    function startStream() {
      stream = new EventSource("/api/stream?log_lines=140&metric_limit=10&run_limit=10");
      stream.onopen = () => {
        document.getElementById("streamStatus").textContent = "stream: live";
        if (fallbackPoll) {
          clearInterval(fallbackPoll);
          fallbackPoll = null;
        }
      };
      stream.onmessage = (event) => {
        render(JSON.parse(event.data));
      };
      stream.onerror = () => {
        document.getElementById("streamStatus").textContent = "stream: reconnecting";
        startFallbackPolling();
      };
    }

    fetchSnapshot();
    startStream();
  </script>
</body>
</html>
"""


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def utc_now() -> datetime:
    return datetime.now(UTC)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def tail_lines(path: Path, limit: int) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        lines = deque(f, maxlen=limit)
    return [line.rstrip("\n") for line in lines]


def read_recent_metrics(limit: int, db_url: str = "", db_path: Path | None = None) -> list[dict[str, Any]]:
    return fetch_recent_pipeline_metrics(limit, db_url=db_url, db_path=db_path)


def read_recent_jsonl(path: Path, limit: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: deque[dict[str, Any]] = deque(maxlen=limit)
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return list(rows)[::-1]


def read_recent_csv(path: Path, limit: int) -> list[dict[str, str]]:
    if not path.exists():
        return []
    rows: deque[dict[str, str]] = deque(maxlen=limit)
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rows.append({str(k): str(v) for k, v in row.items()})
    return list(rows)[::-1]


def count_jsonl_rows(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def summarize_returns_history(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "total_observations": 0,
            "scheduled_observations": 0,
            "fast_loop_observations": 0,
            "strategy_counts": {},
        }
    total = 0
    scheduled = 0
    fast_loop = 0
    strategy_counts: dict[str, int] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("source", "").strip() == "bootstrap_example":
                continue
            strategy = row.get("strategy", "").strip()
            if not strategy:
                continue
            source = row.get("source", "").strip()
            total += 1
            if source == "paper_fast_pair_lock":
                fast_loop += 1
            else:
                scheduled += 1
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
    return {
        "total_observations": total,
        "scheduled_observations": scheduled,
        "fast_loop_observations": fast_loop,
        "strategy_counts": dict(sorted(strategy_counts.items())),
    }


def summarize_pair_lock_returns(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"total_observations": 0, "strategy_counts": {}}
    total = 0
    strategy_counts: dict[str, int] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("source", "").strip() == "bootstrap_example":
                continue
            strategy = row.get("strategy", "").strip()
            if not strategy.startswith("pair_lock_"):
                continue
            total += 1
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
    return {"total_observations": total, "strategy_counts": dict(sorted(strategy_counts.items()))}


def latest_file(reports_dir: Path, pattern: str) -> Path | None:
    matches = sorted(reports_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def summarize_artifact(path: Path | None, kind: str, repo_root: Path) -> dict[str, Any]:
    if path is None:
        return {"path": None, "summary": None}
    repo_root = repo_root.resolve()
    path = path.resolve()
    payload = read_json(path)
    try:
        rel_path = str(path.relative_to(repo_root))
    except ValueError:
        rel_path = str(path)
    summary = "available"
    if kind == "integrity":
        agg = payload.get("aggregate", {})
        summary = (
            f"pass={agg.get('pass')} | rows={agg.get('rows')} | "
            f"stale_rows={agg.get('stale_rows')} | duplicate_rows={agg.get('duplicate_rows')} | "
            f"missing_required_rows={agg.get('missing_required_rows')}"
        )
    elif kind == "probability":
        summary = (
            f"strategy={payload.get('focus_strategy')} | observations={payload.get('focus_observations')} | "
            f"p_profit={payload.get('p_profit')} | p_ruin={payload.get('p_ruin')} | pbo={payload.get('pbo')}"
        )
    elif kind == "validation":
        summary = (
            f"strategy={payload.get('focus_strategy')} | go_live_candidate={payload.get('go_live_candidate')} | "
            f"failed_rules={len(payload.get('failed_rules', []))} | sharpe={payload.get('metrics', {}).get('sharpe')}"
        )
    return {"path": rel_path, "summary": summary, "generated_at_utc": payload.get("generated_at_utc")}


def discover_artifacts(reports_dir: Path, repo_root: Path) -> dict[str, Any]:
    return {
        "integrity": summarize_artifact(latest_file(reports_dir, "integrity_report_*.json"), "integrity", repo_root),
        "probability": summarize_artifact(latest_file(reports_dir, "probability_report_*.json"), "probability", repo_root),
        "validation": summarize_artifact(latest_file(reports_dir, "validation_report_*.json"), "validation", repo_root),
        "leaderboard": summarize_artifact(latest_file(reports_dir, "strategy_leaderboard_*.json"), "validation", repo_root),
    }


def summarize_tracked_pair_loop(reports_dir: Path, repo_root: Path) -> dict[str, Any]:
    refined_triage_path = reports_dir / "cross_venue_pair_lock_triage_refined.json"
    default_triage_path = reports_dir / "cross_venue_pair_lock_triage.json"
    scout_path = reports_dir / "cross_venue_pair_lock_scout_candidates.json"
    quote_diagnostics_path = reports_dir / "pair_lock_quote_diagnostics.json"
    triage_path = refined_triage_path if refined_triage_path.exists() else default_triage_path
    candidate_ledger_path = reports_dir / "triaged_pair_candidates.csv"
    paper_ledger_path = reports_dir / "triaged_pair_paper_execution.csv"
    latest_fast_loop_report = latest_file(reports_dir, "tracked_pair_fast_loop_*.json")
    triage = read_json(triage_path)
    scout = read_json(scout_path)
    quote_diagnostics_report = read_json(quote_diagnostics_path)
    latest_report = read_json(latest_fast_loop_report) if latest_fast_loop_report else {}
    recent_paper_rows = read_recent_csv(paper_ledger_path, 8)
    pair_lock_returns = summarize_pair_lock_returns(repo_root / "data" / "returns" / "returns_history.csv")
    selected_candidates = triage.get("selected_candidates", []) if isinstance(triage, dict) else []
    scout_candidates = scout.get("selected_candidates", []) if isinstance(scout, dict) else []
    quote_diagnostics_rows = quote_diagnostics_report.get("pair_rows", []) if isinstance(quote_diagnostics_report, dict) else []
    if not isinstance(selected_candidates, list):
        selected_candidates = []
    if not isinstance(scout_candidates, list):
        scout_candidates = []
    if not isinstance(quote_diagnostics_rows, list):
        quote_diagnostics_rows = []
    filled_recent = [row for row in recent_paper_rows if row.get("status") == "filled"]
    review_now_rows = [
        row for row in quote_diagnostics_rows if isinstance(row, dict) and row.get("stale_risk") == "review_now"
    ]
    watch_rows = [row for row in quote_diagnostics_rows if isinstance(row, dict) and row.get("stale_risk") == "watch"]

    summary = latest_report.get("paper_execution_summary", {}) if isinstance(latest_report, dict) else {}
    report_summary = latest_report.get("summary", {}) if isinstance(latest_report, dict) else {}
    operator_summary = (
        f"Latest tracked loop report saw {report_summary.get('provable_lock_count', 0)} provable locks, "
        f"{summary.get('filled_count', 0)} paper fills, and {pair_lock_returns['total_observations']} pair-lock observations in returns history."
        if latest_report
        else "No tracked pair loop report found yet. Run the triaged fast loop to populate this panel."
    )
    health = "active" if latest_report else "missing"
    if latest_report and not filled_recent:
        health = "waiting_for_fills"

    return {
        "health": health,
        "operator_summary": operator_summary,
        "triage_path": str(triage_path) if triage_path.exists() else "",
        "scout_path": str(scout_path) if scout_path.exists() else "",
        "quote_diagnostics_path": str(quote_diagnostics_path) if quote_diagnostics_path.exists() else "",
        "latest_report_path": str(latest_fast_loop_report) if latest_fast_loop_report else "",
        "candidate_ledger_path": str(candidate_ledger_path) if candidate_ledger_path.exists() else "",
        "paper_ledger_path": str(paper_ledger_path) if paper_ledger_path.exists() else "",
        "pair_lock_observations": pair_lock_returns["total_observations"],
        "pair_lock_strategy_counts": pair_lock_returns["strategy_counts"],
        "triage_candidate_count": len(selected_candidates),
        "scout_candidate_count": len(scout_candidates),
        "quote_review_now_count": len(review_now_rows),
        "quote_watch_count": len(watch_rows),
        "recent_fills": filled_recent[:5],
        "selected_candidates": selected_candidates[:5],
        "scout_candidates": scout_candidates[:5],
        "quote_diagnostics": quote_diagnostics_rows[:5],
        "latest_summary": report_summary,
        "latest_paper_execution_summary": summary,
    }


def load_primary_watcher_view(reports_dir: Path, run_limit: int) -> tuple[dict[str, Any], list[dict[str, Any]], int]:
    pair_lock_status_path = reports_dir / "pair_lock_watcher_status.json"
    pair_lock_events_path = reports_dir / "pair_lock_watcher_events.jsonl"
    legacy_status_path = reports_dir / "watcher_status.json"
    legacy_events_path = reports_dir / "watcher_events.jsonl"

    if pair_lock_status_path.exists() or pair_lock_events_path.exists():
        status = read_json(pair_lock_status_path)
        events = read_recent_jsonl(pair_lock_events_path, run_limit)
        return status, events, count_jsonl_rows(pair_lock_events_path)

    status = read_json(legacy_status_path)
    events = read_recent_jsonl(legacy_events_path, run_limit)
    return status, events, count_jsonl_rows(legacy_events_path)


def derive_health(status: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    expected_interval_minutes = int(status.get("expected_interval_minutes") or 15)
    expected_delta = timedelta(minutes=expected_interval_minutes)
    updated_at = parse_iso(status.get("updated_at_utc"))
    finished_at = parse_iso(status.get("finished_at_utc"))
    started_at = parse_iso(status.get("started_at_utc"))
    last_success = parse_iso(status.get("last_success_at_utc"))
    reference_finish = last_success or finished_at or started_at
    next_expected = reference_finish + expected_delta if reference_finish else None

    seconds_since_update = (now - updated_at).total_seconds() if updated_at else None
    seconds_since_start = (now - started_at).total_seconds() if started_at else None
    seconds_since_finish = (now - finished_at).total_seconds() if finished_at else None
    seconds_since_last_success = (now - last_success).total_seconds() if last_success else None
    until_next_expected = (next_expected - now).total_seconds() if next_expected else None
    schedule_drift = max(0.0, -until_next_expected) if until_next_expected is not None else None

    run_status = status.get("status")
    health = "unknown"
    health_text = "unknown"
    if not status:
        operator_summary = "No pipeline run exists in the local metrics database yet. Run the pipeline once before relying on this dashboard."
    elif run_status == "running":
        health = "running"
        health_text = "running"
        operator_summary = (
            f"Pipeline is mid-run and currently executing {status.get('current_step') or 'an unknown step'}. "
            "A moving last-output line indicates the child command is still making progress."
        )
    elif run_status == "failed":
        health = "failed"
        health_text = "failed"
        operator_summary = (
            f"The latest run failed. Root cause hint: {status.get('last_error') or 'inspect the log tail for the stack trace'}."
        )
    elif run_status == "success":
        if until_next_expected is not None and until_next_expected >= -expected_interval_minutes * 30:
            health = "healthy" if until_next_expected >= 0 else "stale"
            health_text = "on schedule" if until_next_expected >= 0 else "overdue"
        operator_summary = (
            "The latest completed run succeeded. "
            + (
                f"Next expected run is around {next_expected.isoformat()}."
                if next_expected
                else "Next expected run cannot be derived yet."
            )
        )
    else:
        operator_summary = "State is unknown. Inspect the local metrics database and scheduler log to determine whether the scheduler has run."

    return {
        "health": health,
        "health_text": health_text,
        "expected_interval_minutes": expected_interval_minutes,
        "seconds_since_update": seconds_since_update,
        "seconds_since_start": seconds_since_start,
        "seconds_since_finish": seconds_since_finish,
        "seconds_since_last_success": seconds_since_last_success,
        "next_expected_run_utc": next_expected.isoformat() if next_expected else None,
        "until_next_expected_run_seconds": until_next_expected,
        "schedule_drift_seconds": schedule_drift,
        "operator_summary": operator_summary,
    }


def build_recent_runs(status: dict[str, Any], metrics: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    if status.get("run_id"):
        timestamp = status.get("finished_at_utc") or status.get("started_at_utc")
        if status.get("status") == "failed":
            runs.append(
                {
                    "timestamp_utc": timestamp,
                    "status": "failed",
                    "total_sec": status.get("total_sec"),
                    "executed_steps": [step.get("step") for step in status.get("completed_steps", [])],
                    "health_hint": "failed",
                }
            )
    for row in metrics:
        runs.append(
            {
                "timestamp_utc": row.get("timestamp_utc"),
                "status": row.get("status", "success"),
                "total_sec": row.get("total_sec"),
                "executed_steps": list((row.get("timings_sec") or {}).keys()),
                "health_hint": "healthy",
            }
        )
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[Any, Any]] = set()
    for row in runs:
        key = (row.get("timestamp_utc"), row.get("status"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped[:limit]


def build_payload(
    reports_dir: Path,
    repo_root: Path,
    log_lines: int,
    metric_limit: int,
    run_limit: int,
    db_url: str = "",
    db_path: Path | None = None,
) -> dict[str, Any]:
    returns_summary = summarize_returns_history(repo_root / "data" / "returns" / "returns_history.csv")
    tracked_pair_loop = summarize_tracked_pair_loop(reports_dir, repo_root)
    watcher_status, watcher_events, total_watcher_cycles = load_primary_watcher_view(reports_dir, run_limit)
    log_tail = tail_lines(reports_dir / "cron_pipeline.log", log_lines)
    runtime_warning = ""
    active_db_url = db_url
    try:
        status = fetch_latest_pipeline_run(db_url=active_db_url, db_path=db_path)
        metrics = read_recent_metrics(metric_limit, db_url=active_db_url, db_path=db_path)
        total_pipeline_runs = count_pipeline_metrics(db_url=active_db_url, db_path=db_path)
    except (ModuleNotFoundError, OSError, RuntimeError) as exc:
        active_db_url = ""
        status = fetch_latest_pipeline_run(db_path=db_path)
        metrics = read_recent_metrics(metric_limit, db_path=db_path)
        total_pipeline_runs = count_pipeline_metrics(db_path=db_path)
        runtime_warning = f"runtime_state_db_fallback=sqlite reason={type(exc).__name__}: {exc}"
    except Exception as exc:
        if psycopg is not None and isinstance(exc, psycopg.Error):
            active_db_url = ""
            status = fetch_latest_pipeline_run(db_path=db_path)
            metrics = read_recent_metrics(metric_limit, db_path=db_path)
            total_pipeline_runs = count_pipeline_metrics(db_path=db_path)
            runtime_warning = f"runtime_state_db_fallback=sqlite reason={type(exc).__name__}: {exc}"
        else:
            raise
    return {
        "generated_at_utc": utc_now().isoformat(),
        "status": status,
        "watcher_status": watcher_status,
        "watcher_events": watcher_events,
        "counts": {
            "total_pipeline_runs": total_pipeline_runs,
            "total_watcher_cycles": total_watcher_cycles,
            "scheduled_paper_observations": returns_summary["scheduled_observations"],
            "fast_loop_paper_observations": returns_summary["fast_loop_observations"],
            "total_paper_observations": returns_summary["total_observations"],
            "total_pair_lock_observations": tracked_pair_loop["pair_lock_observations"],
        },
        "returns_summary": returns_summary,
        "tracked_pair_loop": tracked_pair_loop,
        "derived": derive_health(status),
        "metrics": metrics,
        "recent_runs": build_recent_runs(status, metrics, run_limit),
        "latest_artifacts": discover_artifacts(reports_dir, repo_root),
        "log_tail": "\n".join(log_tail),
        "log_line_count": len(log_tail),
        "runtime_state_db_warning": runtime_warning,
        "runtime_state_backend": "postgres" if active_db_url else "sqlite",
    }


class MonitorHandler(BaseHTTPRequestHandler):
    reports_dir: Path
    repo_root: Path
    db_url: str = ""
    db_path: Path | None = None

    def _send_json(self, payload: dict[str, Any], status_code: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self) -> None:
        body = HTML.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        log_lines = int(query.get("log_lines", ["140"])[0])
        metric_limit = int(query.get("metric_limit", ["10"])[0])
        run_limit = int(query.get("run_limit", ["10"])[0])

        if parsed.path == "/":
            self._send_html()
            return

        if parsed.path == "/api/monitor":
            self._send_json(
                build_payload(
                    self.reports_dir,
                    self.repo_root,
                    log_lines,
                    metric_limit,
                    run_limit,
                    db_url=self.db_url,
                    db_path=self.db_path,
                )
            )
            return

        if parsed.path == "/api/stream":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            try:
                while True:
                    payload = build_payload(
                        self.reports_dir,
                        self.repo_root,
                        log_lines,
                        metric_limit,
                        run_limit,
                        db_url=self.db_url,
                        db_path=self.db_path,
                    )
                    frame = f"data: {json.dumps(payload, ensure_ascii=True)}\n\n".encode("utf-8")
                    self.wfile.write(frame)
                    self.wfile.flush()
                    time.sleep(2)
            except (BrokenPipeError, ConnectionResetError):
                return

        self._send_json({"error": "not found"}, status_code=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve a live monitor for pred-infra pipeline runs.")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--db-url", default="", help="runtime-state DATABASE_URL override")
    parser.add_argument("--db-path", default="", help="deprecated local SQLite runtime-state DB override")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    reports_dir = repo_root / "data" / "reports"
    try:
        db_url = load_db_url(args.db_url)
    except ValueError:
        db_url = ""
    if db_url:
        db_url, runtime_warning = prepare_runtime_db_url(repo_root, db_url)
        if runtime_warning:
            print(runtime_warning, file=sys.stderr)
    db_path = Path(args.db_path) if args.db_path else None
    handler = type(
        "PredInfraMonitorHandler",
        (MonitorHandler,),
        {"reports_dir": reports_dir, "repo_root": repo_root, "db_url": db_url, "db_path": db_path},
    )
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"serving pipeline monitor on http://{args.host}:{args.port}")
    print(f"reading reports from {reports_dir}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
