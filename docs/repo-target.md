# Repo Target

## Objective
Maximize risk-adjusted net return from prediction-market strategies using a strict pipeline:
data -> backtest -> paper -> tiny live -> scale.

## Strategy Ranking (ROI-Weighted)
Scores are relative and should be re-estimated monthly from paper/live data.

1. Single-venue market making + incentives
   - Why: repeatable microstructure edge + incentive capture
   - Main risks: inventory drift, adverse selection, spread compression
2. Single-venue structural arbitrage/parity
   - Why: math-driven mispricing checks are testable
   - Main risks: hidden fees/slippage, stale books
3. Cross-venue arbitrage (Polymarket <-> Kalshi)
   - Why: sometimes clear basis gaps
   - Main risks: contract mismatch, settlement rule mismatch, transfer latency
4. Whale-follow/copy-trading
   - Why: can occasionally identify informed flow
   - Main risks: lag, survivorship bias, hidden hedge positions, crowding

Between "cross-venue arb" and "whale-follow", current default is:
1. cross-venue arb
2. whale-follow

## Phase Plan
1. Phase 0 (Week 1-2): data quality baseline
   - fetch market snapshots
   - normalize schema
   - timestamp and integrity checks
2. Phase 1 (Week 2-4): evaluation engine
   - backtest/paper ledger
   - fees/slippage model
   - calibration and PnL metrics
3. Phase 2 (Week 4-6): strategy iteration
   - run A/B for top two strategies
   - compute net edge stability
4. Phase 3: controlled live trial
   - tiny size only
   - hard daily loss cap and kill switch
5. Phase 4: optional AI integration
   - only after stable positive net results

## What We Mean By "Strong Dev Infra"
For this project, it includes:
- reliable public market-data endpoints
- authenticated trading APIs with clear key management
- websocket feeds for low-latency market updates
- documented rate limits
- documented fees + settlement/resolution rules
- demo/sandbox or low-risk testing path

## Hard Gates Before Scaling
- 30+ day paper net PnL > 0 after fees/slippage
- max drawdown below configured threshold
- stable fill assumptions vs observed fills
- no unresolved data integrity failures
