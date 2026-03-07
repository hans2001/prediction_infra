from __future__ import annotations


def binary_pair_edge(
    yes_ask: float,
    no_ask: float,
    fee_per_contract: float = 0.0,
    slippage_per_contract: float = 0.0,
) -> float:
    """
    Returns expected locked edge per $1 payout for buying both YES and NO.
    Positive value suggests a potential arbitrage after modeled costs.
    """
    gross_cost = yes_ask + no_ask
    total_cost = gross_cost + 2 * (fee_per_contract + slippage_per_contract)
    return 1.0 - total_cost


def edge_bps(edge: float) -> float:
    return edge * 10_000
