from pred_infra.eval.validation import evaluate_thresholds, summarize_returns


def test_summarize_returns_basic() -> None:
    returns = [0.01, -0.005, 0.004, 0.003]
    summary = summarize_returns(returns)
    assert summary["observations"] == 4.0
    assert "sharpe" in summary
    assert 0.0 <= summary["max_drawdown"] <= 1.0


def test_evaluate_thresholds_flags_failures() -> None:
    metrics = {
        "observations": 100.0,
        "mean_return": 0.0001,
        "sharpe": 0.02,
        "p_profit": 0.52,
        "p_ruin": 0.30,
        "pbo": 0.50,
        "conservative_score": 0.10,
        "max_drawdown": 0.25,
    }
    gates = {
        "min_observations": 300,
        "min_sharpe": 0.05,
        "min_p_profit": 0.55,
        "max_p_ruin": 0.25,
        "max_pbo": 0.45,
        "min_conservative_score": 0.2,
        "max_drawdown": 0.2,
    }
    decision = evaluate_thresholds(metrics, gates)
    assert not decision.passed
    assert len(decision.failed_rules) >= 5
