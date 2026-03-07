from pred_infra.eval.probability import (
    conservative_real_profit_score,
    estimate_pbo,
    estimate_profit_probability,
    estimate_ruin_probability,
)


def test_profit_probability_range() -> None:
    values = [0.01, -0.002, 0.004, 0.003, -0.001, 0.002]
    prob = estimate_profit_probability(values, n_trials=200, block_size=2, seed=11)
    assert 0.0 <= prob <= 1.0


def test_ruin_probability_range() -> None:
    values = [0.01, -0.02, 0.005, -0.01, 0.004, -0.005]
    prob = estimate_ruin_probability(values, n_trials=200, block_size=2, seed=13)
    assert 0.0 <= prob <= 1.0


def test_pbo_range() -> None:
    strategy_returns = {
        "a": [0.01, -0.004, 0.003, 0.002, -0.001, 0.004, -0.002, 0.003, 0.001, -0.001] * 3,
        "b": [0.002, -0.003, 0.002, 0.001, -0.002, 0.003, -0.001, 0.001, 0.001, -0.002] * 3,
        "c": [-0.001, -0.004, 0.001, 0.0, -0.003, 0.001, -0.002, 0.0, 0.001, -0.003] * 3,
    }
    result = estimate_pbo(strategy_returns, n_splits=20, seed=17)
    assert 0.0 <= result.pbo <= 1.0
    assert result.splits_used == 20


def test_conservative_score_range() -> None:
    score = conservative_real_profit_score(0.6, 0.2, 0.3)
    assert 0.0 <= score <= 1.0
