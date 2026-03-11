# Always-On Host Longlist

This document separates host-selection reasoning from the actual deployment runbook.

Use it when deciding where `pred-infra` should run as a single always-on box.
Use [docs/always-on-host-plan.md](/home/hans2/prediction_infra/docs/always-on-host-plan.md) when you are ready to deploy.

## Selection Criteria

For the current repo stage, the right host should optimize for:

- one cheap always-on Linux VM
- predictable monthly spend
- enough RAM headroom for sequential fetch, the fast loop, monitor, logs, and SQLite
- simple SSH + `systemd` operations
- low operational overhead

It does not need:

- autoscaling
- managed database
- containers
- load balancer
- multi-node failover

## Current Recommendation

Default choice:

- Amazon Lightsail
- Ubuntu LTS
- `2 GB RAM / 2 vCPU / 60 GB SSD`

Why it remains the default:

- the repo already has Lightsail-oriented install assets
- fixed-price single-box deployment matches the current operating model
- `systemd` deployment is straightforward
- it keeps spend discipline aligned with the current evidence stage

## Viable Longlist

### 1. Amazon Lightsail

Status:

- recommended default

Best fit when:

- you want the lowest-friction path from laptop to always-on host
- fixed monthly pricing matters more than infra flexibility
- the team wants the smallest change from the current ops docs

Main tradeoff:

- less flexible than a full cloud VM stack if the system later needs more custom networking or managed services

### 2. Small General-Purpose VPS

Examples:

- DigitalOcean Droplet
- Linode/Akamai shared CPU instance
- Hetzner Cloud VM

Status:

- viable alternative

Best fit when:

- the team wants a plain Linux box and is comfortable owning more of the setup details
- a non-AWS provider is preferred

Main tradeoffs:

- current repo docs and helper scripts are more AWS/Lightsail-specific than VPS-generic
- provider choice drift creates extra ops work before it creates edge

### 3. AWS EC2

Status:

- acceptable but not preferred

Best fit when:

- the team already has AWS account standards that require EC2 instead of Lightsail

Main tradeoffs:

- more moving parts than needed for one small always-on collector
- easier to overbuild into security groups, EBS choices, and future-service debates

### 4. Platform-As-A-Service / Container Hosts

Examples:

- Fly.io
- Render
- Railway

Status:

- not recommended now

Why not now:

- the repo is built around persistent local files, SQLite state, and `systemd`
- long-running timers and local operational artifacts fit a VM better than an app platform

### 5. Managed Kubernetes / Multi-Service Cloud Layout

Status:

- reject for current stage

Why this is wrong now:

- cost and complexity move faster than evidence quality
- it solves scale and orchestration problems the repo does not have

## Decision Rule

Choose:

- Lightsail if you want the default path
- a small VPS only if there is a concrete reason to avoid AWS
- EC2 only if an AWS policy constraint forces it

Do not choose:

- managed database
- container-first hosting
- multi-host layouts

until one strategy family has durable paper evidence worth protecting with more infrastructure.
