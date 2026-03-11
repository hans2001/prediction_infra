# Always-On Host Plan

This document defines the lowest-cost sensible path for moving `pred-infra` off a sleeping laptop and onto an always-on host.

Provider-selection detail now lives in [docs/always-on-host-longlist.md](/home/hans2/prediction_infra/docs/always-on-host-longlist.md) so this file can stay deployment-focused.

The goal is not "cloud architecture".
The goal is uninterrupted evidence collection for the current primary mission:

- baseline pipeline health
- continuous `cross_venue_pair_lock` fast-loop collection
- local dashboard access for operators

## Recommendation

Default recommendation:

- provider: Amazon Lightsail
- region: `us-east-1` or the nearest low-latency US region
- OS: Ubuntu LTS
- instance plan: `2 GB RAM / 2 vCPU / 60 GB SSD`
- budget target: `~$12-15/month`

Why this is the default:

- it matches the current single-box `systemd` deployment model
- it keeps spend predictable
- the repo already includes Lightsail install assets
- `2 GB` gives safer RAM headroom than the current laptop path

## Machine Choice

### Recommended starting box

Use:

- Linux/Unix bundle with public IPv4
- `2 GB RAM`
- `2 vCPU`
- `60 GB SSD`
- `3 TB` transfer

Official pricing references say this plan is `$12/month`, while the smaller public-IPv4 plans are `$5/month` for `512 MB` and `$7/month` for `1 GB`. AWS also documents baseline CPU performance of `20%` for the `$12` plan, versus `10%` for the `$7` plan and `5%` for the `$5` plan.

Why not start at `1 GB`:

- the repo already hit memory-pressure failure modes in fetch
- the fast loop, monitor, timer, Python env, logs, and SQLite all on one host make `1 GB` the wrong place to be cheap
- saving `$5/month` is not worth another round of false failures

### Lowest acceptable floor

If spend must be minimized aggressively, use:

- Linux/Unix bundle with public IPv4
- `1 GB RAM`
- `2 vCPU`
- `40 GB SSD`
- `2 TB` transfer

Cost: `$7/month`

This is acceptable only for a short pilot if:

- fetch remains sequential
- snapshot limits stay conservative
- the fast loop remains shortlist-only
- memory is monitored closely

### What not to request

Do not request at this stage:

- `4 GB+` instances
- Lightsail managed databases
- Lightsail container service
- Lightsail load balancer
- block storage add-ons
- CDN

Those are cost multipliers without edge value right now.

## Cost Estimate

### Recommended monthly budget

For the recommended `2 GB` Lightsail instance:

- instance: `$12/month`
- snapshots: `~$1-3/month` if retention is kept tight
- total target: `~$13-15/month`

### Aggressive low-cost pilot

For the `1 GB` instance:

- instance: `$7/month`
- snapshots: `~$1-2/month`
- total target: `~$8-9/month`

### Optional costs to avoid

Do not enable these unless the board explicitly approves them:

- managed database: starts at `$15/month`
- load balancer: `$18/month`
- container service: starts at `$7/month`
- block storage: `$0.10/GB/month`
- snapshots: `$0.05/GB/month`
- outbound transfer overage: starts at `$0.09/GB`

These come from the official Lightsail pricing page and are exactly why this project should stay single-instance and SQLite-first for now.

## Spend Guardrails

The company should explicitly choose a "do not provision" posture for now.

### Provisioning policy

Until one strategy family survives meaningful paper evidence, do not provision:

- RDS or Lightsail managed database
- load balancer
- container service
- CDN
- extra block storage
- second instance
- standby / failover instance

### Database policy

Use:

- local SQLite runtime state
- local files for reports
- local `returns_history.csv`

Do not use by default:

- `--db-write`
- external Postgres
- managed database provisioning

Rationale:

- current workload does not justify the cost
- local state is already the fallback path
- keeping state local reduces both spend and operational complexity

## What Runs On The Host

Run only three things:

1. `pred-infra-pipeline.timer`
2. `pred-infra-fast-loop.service`
3. `pred-infra-monitor.service`

That is enough to support the current mission.

Do not run the old generic watcher as a first-class service on the host for now.
The pair-lock fast loop is the meaningful watcher-equivalent path for the current primary family.

## Recommended Host Layout

Use one box only:

- repo at `/opt/pred-infra`
- Python venv in `/opt/pred-infra/.venv`
- reports under `/opt/pred-infra/data/reports`
- returns under `/opt/pred-infra/data/returns`
- systemd units under `/etc/systemd/system`

Keep the dashboard bound to:

- `127.0.0.1:8787`

Access it through SSH tunneling instead of exposing it publicly.

## Migration Plan

### Phase 1: Cheap pilot

1. Create one Lightsail Ubuntu instance.
2. Attach only the default disk that comes with the bundle.
3. SSH in as `ubuntu`.
4. Clone or rsync the repo to `/opt/pred-infra`.
5. Run `bash ops/lightsail/install_lightsail.sh`.
6. Install and enable the monitor service.
7. Install and enable the fast-loop service.
8. Verify that:
   - timer runs
   - fast loop stays active
   - returns history grows
   - dashboard shows pair-lock activity

Success criteria for Phase 1:

- at least `7 days` of uninterrupted baseline pipeline health
- at least `7 days` of continuous pair-lock observation collection
- no memory-kill events
- monthly projected spend still within budget

### Phase 2: Stable collection

After the pilot:

1. keep one retained snapshot policy only
2. keep logs rotated
3. review CPU, memory, and disk weekly
4. only then decide whether `1 GB` is too small or `2 GB` is enough

### Phase 3: Only if evidence improves

Only after one family survives extended paper evidence should the team consider:

- external database
- second host
- failover
- more storage

## Deployment Checklist

Before migration:

- confirm `pred-infra-fast-loop.service` is the primary evidence collector
- confirm generic watcher is not the primary structural-edge path
- confirm `--db-write` is not enabled
- confirm scheduler defaults still focus on approved families only
- confirm snapshot limits remain conservative

After migration:

- `systemctl status pred-infra-pipeline.timer --no-pager`
- `systemctl status pred-infra-pipeline.service --no-pager`
- `systemctl status pred-infra-fast-loop.service --no-pager`
- `systemctl status pred-infra-monitor.service --no-pager`
- `journalctl -u pred-infra-fast-loop.service -n 100 --no-pager`
- `python3 scripts/status_report.py`

## Codebase Measures That Already Help Control Spend

The repo already has several useful controls:

- scheduled fetches use conservative per-source snapshot limits
- fetch runs sequentially instead of the older higher-pressure path
- maker-family and generic watcher-family auto-upserts are disabled by default
- the fast loop is shortlist-based, not full-universe polling
- the dashboard is local-only by default
- runtime state can stay on SQLite instead of requiring external Postgres

These controls should remain in place on the first host.

## Additional Guardrails To Keep

Operationally, keep these defaults:

- `top_n=5` for the fast loop
- `sleep_sec=5` for the fast loop unless APIs prove stable at a faster cadence
- one instance only
- one snapshot retention policy only
- no public dashboard exposure
- no managed DB
- no second strategy family promoted into default automation without explicit approval

## Strong Recommendation

Request one always-on VM, not a broader cloud stack.

Start with:

- `2 GB / 2 vCPU / 60 GB SSD`
- no managed database
- no load balancer
- no containers
- no CDN
- no extra block storage

If the board wants the lowest-risk cheap move, the default provider choice remains Lightsail.
