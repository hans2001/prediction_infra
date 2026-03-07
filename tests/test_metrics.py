from pred_infra.eval.metrics import brier_score, log_loss, max_drawdown


def test_brier_score() -> None:
    probs = [0.8, 0.2]
    outcomes = [1, 0]
    assert brier_score(probs, outcomes) < 0.1


def test_log_loss() -> None:
    probs = [0.8, 0.2]
    outcomes = [1, 0]
    assert log_loss(probs, outcomes) < 0.3


def test_max_drawdown() -> None:
    equity = [100.0, 103.0, 101.0, 99.0, 105.0]
    assert max_drawdown(equity) == 4.0
