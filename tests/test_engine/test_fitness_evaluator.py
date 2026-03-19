# tests/test_engine/test_fitness_evaluator.py
import numpy as np
import pytest
from tecs.engine.fitness_evaluator import FitnessEvaluator


def test_weighted_fitness():
    ev = FitnessEvaluator(w_e=0.4, w_b=0.4, w_f=0.2)
    fitness = ev.compute(
        emergence={"betti_0": 0.5, "order_parameter_r": 0.6},
        benchmark={"concept": 0.8, "contradiction": 0.7, "analogy": 0.6},
        cost=0.3,
    )
    assert 0.0 <= fitness <= 1.0


def test_handles_empty_metrics():
    ev = FitnessEvaluator(w_e=0.4, w_b=0.4, w_f=0.2)
    fitness = ev.compute(emergence={}, benchmark={}, cost=0.0)
    # Only efficiency contributes: 0.2 * 1.0 = 0.2
    assert fitness == pytest.approx(0.2, abs=0.01)


def test_normalize_metric():
    ev = FitnessEvaluator()
    ev.update_history({"x": 0.3})
    ev.update_history({"x": 0.5})
    ev.update_history({"x": 0.7})
    normalized = ev.normalize_metric(0.5, "x")
    assert 0.0 <= normalized <= 1.0


def test_fitness_clipped_to_unit_range():
    ev = FitnessEvaluator(w_e=0.4, w_b=0.4, w_f=0.2)
    fitness = ev.compute(
        emergence={"betti_0": 1.0, "betti_1": 1.0},
        benchmark={"concept": 1.0},
        cost=0.0,
    )
    assert fitness <= 1.0
    assert fitness >= 0.0


def test_high_cost_lowers_fitness():
    ev = FitnessEvaluator(w_e=0.4, w_b=0.4, w_f=0.2)
    low_cost = ev.compute(emergence={"betti_0": 0.5}, benchmark={"concept": 0.5}, cost=0.0)
    high_cost = ev.compute(emergence={"betti_0": 0.5}, benchmark={"concept": 0.5}, cost=1.0)
    assert low_cost > high_cost


def test_normalize_metric_no_history_returns_half():
    ev = FitnessEvaluator()
    result = ev.normalize_metric(0.5, "missing_key")
    assert result == 0.5


def test_normalize_metric_constant_history_returns_half():
    ev = FitnessEvaluator()
    ev.update_history({"y": 0.5})
    ev.update_history({"y": 0.5})
    result = ev.normalize_metric(0.5, "y")
    assert result == 0.5


def test_update_history_accumulates():
    ev = FitnessEvaluator()
    for i in range(5):
        ev.update_history({"z": float(i)})
    assert len(ev._history) == 5


def test_compute_verified_eliminates():
    ev = FitnessEvaluator()
    verification = {"eliminated": True, "scores": {}, "verification_score": 0, "failure_count": 4}
    fitness = ev.compute_verified({}, {}, 0.0, verification)
    assert fitness == 0.0


def test_compute_verified_rewards_prediction():
    ev = FitnessEvaluator()
    verification = {
        "eliminated": False,
        "scores": {"formal": 1.0, "counterexample": 1.0, "reproducibility": 1.0, "predictive": 0.8},
        "verification_score": 0.95,
        "failure_count": 0,
    }
    fitness = ev.compute_verified(
        {"betti_0": 0.5}, {"concept": 0.7, "query_accuracy": 0.6}, 0.3, verification
    )
    assert fitness > 0.5  # should be decent


def test_compute_verified_clips_to_unit_range():
    ev = FitnessEvaluator()
    verification = {
        "eliminated": False,
        "scores": {"formal": 1.0, "counterexample": 1.0, "reproducibility": 1.0, "predictive": 1.0},
        "verification_score": 1.0,
        "failure_count": 0,
    }
    fitness = ev.compute_verified(
        {"betti_0": 1.0}, {"concept": 1.0, "query_accuracy": 1.0}, 0.0, verification
    )
    assert 0.0 <= fitness <= 1.0


def test_compute_verified_penalises_failures():
    ev = FitnessEvaluator()
    no_failures = {
        "eliminated": False,
        "scores": {"formal": 0.8, "counterexample": 0.8, "reproducibility": 0.8, "predictive": 0.8},
        "verification_score": 0.8,
        "failure_count": 0,
    }
    with_failures = dict(no_failures, failure_count=3)
    f_clean = ev.compute_verified({"betti_0": 0.5}, {"concept": 0.5}, 0.3, no_failures)
    f_penalised = ev.compute_verified({"betti_0": 0.5}, {"concept": 0.5}, 0.3, with_failures)
    assert f_clean > f_penalised
