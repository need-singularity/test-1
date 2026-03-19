"""Tests for CausalTracer."""
import numpy as np
import pytest
from tecs.analysis.causal_tracer import CausalTracer


def test_insufficient_data():
    tracer = CausalTracer(min_generations=20)
    history = [
        {"generation": i, "components": {}, "metrics": {}, "mutation_layer": None}
        for i in range(5)
    ]
    result = tracer.analyze(history)
    assert result["confidence"] == "insufficient_data"
    assert result["weakest_layer"] is None


def test_identifies_weakest_layer():
    tracer = CausalTracer(min_generations=5)
    # Create history where "verification" mutations always decrease fitness
    history = []
    for i in range(10):
        history.append({
            "generation": i,
            "components": {
                "representation": "a", "reasoning": "b", "emergence": "c",
                "verification": "d", "optimization": "e"
            },
            "metrics": {"fitness": 0.5 + (i * 0.01 if i % 2 == 0 else -0.05)},
            "mutation_layer": "verification" if i % 2 == 1 else "reasoning",
        })
    result = tracer.analyze(history)
    assert result["confidence"] == "sufficient"
    assert result["weakest_layer"] is not None


def test_causal_matrix_shape():
    tracer = CausalTracer(min_generations=5)
    history = [
        {
            "generation": i,
            "components": {},
            "metrics": {"a": i * 0.1, "b": i * 0.2},
            "mutation_layer": "reasoning" if i % 2 else None,
        }
        for i in range(10)
    ]
    result = tracer.analyze(history)
    assert result["causal_matrix"].shape[0] == 5  # 5 layers


def test_layer_scores_all_layers_present():
    tracer = CausalTracer(min_generations=5)
    history = [
        {
            "generation": i,
            "components": {},
            "metrics": {"fitness": float(i)},
            "mutation_layer": "reasoning",
        }
        for i in range(10)
    ]
    result = tracer.analyze(history)
    assert "layer_scores" in result
    # reasoning was mutated — should have a non-zero score
    assert "reasoning" in result["layer_scores"]


def test_weakest_layer_is_worst_mean_delta():
    tracer = CausalTracer(min_generations=5)
    history = []
    # optimization mutations: always -1 fitness
    # representation mutations: always +1 fitness
    for i in range(20):
        prev_fitness = float(i)
        if i % 2 == 0:
            mut = "optimization"
            fitness = prev_fitness - 1.0
        else:
            mut = "representation"
            fitness = prev_fitness + 1.0
        history.append({
            "generation": i,
            "components": {},
            "metrics": {"fitness": fitness},
            "mutation_layer": mut,
        })
    result = tracer.analyze(history)
    assert result["confidence"] == "sufficient"
    assert result["weakest_layer"] == "optimization"


def test_no_mutation_entries_returns_none_weakest():
    tracer = CausalTracer(min_generations=5)
    history = [
        {
            "generation": i,
            "components": {},
            "metrics": {"fitness": 1.0},
            "mutation_layer": None,
        }
        for i in range(20)
    ]
    result = tracer.analyze(history)
    assert result["confidence"] == "sufficient"
    assert result["weakest_layer"] is None


def test_causal_matrix_dtype_is_float():
    tracer = CausalTracer(min_generations=5)
    history = [
        {
            "generation": i,
            "components": {},
            "metrics": {"x": float(i)},
            "mutation_layer": "emergence" if i > 5 else None,
        }
        for i in range(10)
    ]
    result = tracer.analyze(history)
    assert result["causal_matrix"].dtype == np.float64


def test_insufficient_data_returns_zero_matrix():
    tracer = CausalTracer(min_generations=20)
    history = [
        {"generation": i, "components": {}, "metrics": {}, "mutation_layer": None}
        for i in range(3)
    ]
    result = tracer.analyze(history)
    assert np.all(result["causal_matrix"] == 0)


def test_matrix_second_dim_matches_metric_count():
    tracer = CausalTracer(min_generations=5)
    history = [
        {
            "generation": i,
            "components": {},
            "metrics": {"a": 1.0, "b": 2.0, "c": 3.0},
            "mutation_layer": "reasoning",
        }
        for i in range(10)
    ]
    result = tracer.analyze(history)
    assert result["causal_matrix"].shape == (5, 3)
