# tests/test_engine/test_fitness_evaluator.py
import numpy as np
import pytest
from tecs.engine.fitness_evaluator import FitnessEvaluator


def test_weighted_fitness():
    ev = FitnessEvaluator(w_e=0.4, w_b=0.4, w_f=0.2)
    fitness = ev.compute(
        emergence={"betti_change": 0.5, "order_r": 0.6},
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
        emergence={"a": 1.0, "b": 1.0},
        benchmark={"c": 1.0},
        cost=0.0,
    )
    assert fitness <= 1.0
    assert fitness >= 0.0


def test_high_cost_lowers_fitness():
    ev = FitnessEvaluator(w_e=0.4, w_b=0.4, w_f=0.2)
    low_cost = ev.compute(emergence={"a": 0.5}, benchmark={"b": 0.5}, cost=0.0)
    high_cost = ev.compute(emergence={"a": 0.5}, benchmark={"b": 0.5}, cost=1.0)
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
