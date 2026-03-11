# MacBook Host Checklist

This document covers the lowest-cost path of using a personal MacBook as the always-on host for `pred-infra`.

Use this only when the priority is avoiding monthly cloud spend.
This is operationally weaker than a dedicated server, but stronger than letting the laptop sleep and collecting only intermittently.

## When This Is Acceptable

Use a MacBook host when:

- the budget target is effectively `$0/month`
- the machine can stay plugged in
- the machine can stay awake during the collection windows that matter
- the current goal is paper evidence, not unattended production-grade uptime

Do not treat it as equivalent to a real server if:

- you need unattended overnight continuity every day
- you expect reboots, lid-closing, or travel interruptions
- the machine is also your primary daily workstation

## Hardware Fit

An M2 MacBook with `8 GB` RAM is sufficient for the current repo workload:

- sequential fetch
- 15-minute daily pipeline
- shortlist-only pair-lock fast loop
- local SQLite state
- local logs and reports

The risk is not CPU.
The risk is sleep, interruption, and operator drift.

## Current Repo Constraint

The repo's persistent-service helpers are Linux-specific:

- [scripts/install_local_fast_loop.sh](/home/hans2/prediction_infra/scripts/install_local_fast_loop.sh)
- [scripts/install_local_monitor.sh](/home/hans2/prediction_infra/scripts/install_local_monitor.sh)
- [ops/lightsail/systemd/pred-infra-pipeline.service](/home/hans2/prediction_infra/ops/lightsail/systemd/pred-infra-pipeline.service)

They rely on `systemd` and should not be treated as the Mac path.

On macOS, the usable path is:

- `cron` for the 15-minute pipeline
- `tmux` for the long-running fast loop
- `caffeinate` or macOS power settings to prevent sleep

## Minimal Mac Setup

1. Keep the machine connected to power.
2. Disable automatic sleep while on power.
3. Keep the repo and `.venv` on local disk.
4. Install cron with [scripts/install_local_cron.sh](/home/hans2/prediction_infra/scripts/install_local_cron.sh).
5. Run the fast loop inside `tmux`.
6. Keep sleep blocked while the fast loop is active.
7. Do not run extra services unless they are needed for current evidence collection.

## Recommended Operating Mode

Run:

- the 15-minute cron pipeline
- the tracked-pair fast loop

Do not run continuously unless needed:

- the local monitor web service
- generic watcher research services
- database sync paths

This keeps the laptop focused on `edge`, `reliability`, and cost control.

## Fast Loop On macOS

The repo already supports a `tmux`-based launcher via [scripts/start_tracked_pair_fast_loop.sh](/home/hans2/prediction_infra/scripts/start_tracked_pair_fast_loop.sh).

On macOS, start it with sleep inhibition disabled inside the script and use `caffeinate` outside the script:

```bash
INHIBIT_SLEEP=0 caffeinate -dims bash scripts/start_tracked_pair_fast_loop.sh
```

Check status with:

```bash
bash scripts/status_tracked_pair_fast_loop.sh
```

This is the closest Mac equivalent to the Linux `systemd-inhibit` path.

## Daily Pipeline On macOS

Install the local cron schedule:

```bash
bash scripts/install_local_cron.sh
```

Important limitation:

- cron runs only while the machine is on
- sleep pauses scheduled runs
- reboot pauses runs until the machine comes back

## Power And Reliability Rules

Use these rules if the MacBook is acting as the host:

- stay plugged in
- keep the lid open unless you have separately verified closed-lid awake behavior
- disable sleep on power
- disable automatic OS update/restart windows during collection hours
- keep enough free disk for logs, snapshots, and reports
- avoid heavy unrelated workloads while the fast loop is running

## What This Hurts Compared With A Server

Compared with a dedicated always-on VM, a MacBook host is worse on:

- uninterrupted overnight continuity
- unattended restart behavior
- operational predictability
- protection against accidental interruption

Compared with not using a long-lived host at all, it is much better for:

- fast-loop continuity
- evidence density for `cross_venue_pair_lock`
- scheduled pipeline continuity while the machine is left awake

## Recommended Default For This Repo

If monthly spend must stay at `$0`, use the MacBook as the host for now.

Run only the minimum:

- local cron pipeline
- `tmux`-based fast loop

Do not add a cloud box until the strategy evidence justifies paying for continuity.
