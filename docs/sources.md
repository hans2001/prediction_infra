# Sources

As of 2026-03-07, these are the primary references used for platform constraints, infra design, and evaluation methodology.

## Official Platform Docs

### Kalshi
- API intro: https://docs.kalshi.com/getting_started/introduction
- Demo environment: https://docs.kalshi.com/getting_started/demo_environment
- WebSocket quick start: https://docs.kalshi.com/getting_started/quick_start_websockets
- Rate limits: https://docs.kalshi.com/getting_started/rate_limits
- Fees (help): https://help.kalshi.com/en/articles/13823805-fees
- Fee schedule PDF: https://kalshi.com/docs/kalshi-fee-schedule.pdf
- Liquidity incentives: https://help.kalshi.com/en/articles/14287212-what-is-the-liquidity-incentive-program

### Polymarket
- Docs home: https://docs.polymarket.com/
- Endpoints overview: https://docs.polymarket.com/quickstart/endpoints-overview
- CLOB auth: https://docs.polymarket.com/developers/CLOB/authentication
- Market channel (WS): https://docs.polymarket.com/developers/CLOB/websocket/market-channel
- Trading fees: https://docs.polymarket.com/polymarket-learn/trading/fees
- Rewards: https://docs.polymarket.com/polymarket-learn/trading/rewards
- Trading restrictions: https://docs.polymarket.com/polymarket-learn/trading/restrictions
- Market resolution: https://docs.polymarket.com/polymarket-learn/markets/market-resolution
- US product page: https://polymarket.com/usa
- Polymarket US docs: https://docs.polymarket.us/

## Research Papers (Evaluation and Tuning)
- Wolfers, J., & Zitzewitz, E. (2004). Prediction Markets. DOI: https://doi.org/10.1257/0895330042632741
- Avellaneda, M., & Stoikov, S. (2008). High-frequency trading in a limit order book. DOI: https://doi.org/10.1080/14697680701381228
- Brier, G. W. (1950). Verification of forecasts expressed in terms of probability. DOI: https://doi.org/10.1175/1520-0493(1950)078%3C0001:VOFEIT%3E2.0.CO;2
- Gneiting, T., & Raftery, A. E. (2007). Strictly Proper Scoring Rules, Prediction, and Estimation. DOI: https://doi.org/10.1198/016214506000001437
- Bailey, D. H., Borwein, J., Lopez de Prado, M., & Zhu, Q. J. (2014). The Probability of Backtest Overfitting. SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253
- White, H. (2000). A Reality Check for Data Snooping. DOI: https://doi.org/10.1111/1468-0262.00152

## Usage Rule
For any strategy claim, link:
1. the exact platform rule/fee/resolution source
2. the exact evaluation metric definition
3. the experiment artifact (backtest or paper-trading result)
