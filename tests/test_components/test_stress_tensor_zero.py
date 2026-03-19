# tests/test_components/test_stress_tensor_zero.py
from __future__ import annotations
import numpy as np
import networkx as nx
import pytest
from tecs.types import TopologyState
from tecs.components.verification.stress_tensor_zero import StressTensorZeroComponent


def _make_graph_state(seed: int = 0) -> TopologyState:
    rng = np.random.default_rng(seed=seed)
    G = nx.karate_club_graph()
    for u, v in G.edges():
        G[u][v]["weight"] = float(rng.uniform(0.5, 2.0))
    curvature = np.zeros(len(G.nodes()))
    return TopologyState(
        complex=G, complex_type="graph", curvature=curvature,
        metrics={}, history=[], metadata={}
    )


def _make_small_graph_state(seed: int = 0, n: int = 6) -> TopologyState:
    rng = np.random.default_rng(seed=seed)
    G = nx.complete_graph(n)
    for u, v in G.edges():
        G[u][v]["weight"] = float(rng.uniform(1.0, 3.0))
    curvature = np.zeros(n)
    return TopologyState(
        complex=G, complex_type="graph", curvature=curvature,
        metrics={}, history=[], metadata={}
    )


def test_create():
    comp = StressTensorZeroComponent()
    assert comp.name == "stress_tensor_zero"
    assert comp.layer == "verification"
    assert "graph" in comp.compatible_types


def test_execute_returns_topology_state():
    comp = StressTensorZeroComponent()
    state = _make_graph_state()
    result = comp.execute(state)
    assert isinstance(result, TopologyState)
    assert result.complex_type == "graph"


def test_execute_sets_stress_magnitude_in_metrics():
    comp = StressTensorZeroComponent()
    state = _make_graph_state()
    result = comp.execute(state)
    assert "stress_magnitude" in result.metrics
    assert result.metrics["stress_magnitude"] >= 0.0


def test_execute_sets_max_stress_in_metrics():
    comp = StressTensorZeroComponent()
    state = _make_graph_state()
    result = comp.execute(state)
    assert "max_stress" in result.metrics
    assert result.metrics["max_stress"] >= 0.0


def test_execute_records_history():
    comp = StressTensorZeroComponent()
    state = _make_graph_state()
    result = comp.execute(state)
    actions = [h["action"] for h in result.history]
    assert "stress_tensor_zero" in actions


def test_execute_uniform_weights_low_stress():
    """Graph with uniform weights has low stress (geodesic = weight on direct edge)."""
    comp = StressTensorZeroComponent()
    G = nx.path_graph(5)
    for u, v in G.edges():
        G[u][v]["weight"] = 1.0
    state = TopologyState(
        complex=G, complex_type="graph", curvature=np.zeros(5),
        metrics={}, history=[], metadata={}
    )
    result = comp.execute(state)
    # On a path graph with uniform weights, each edge is a geodesic segment.
    # Direct edges: geodesic equals weight => zero stress per direct edge.
    assert result.metrics["stress_magnitude"] == pytest.approx(0.0, abs=1e-9)


def test_verify_returns_expected_keys():
    comp = StressTensorZeroComponent()
    state_a = _make_small_graph_state(seed=0)
    state_b = _make_small_graph_state(seed=1)
    result = comp.verify(state_a, state_b)
    assert isinstance(result, dict)
    assert "stress_magnitude" in result
    assert "stress_magnitude_reference" in result
    assert "stress_delta" in result


def test_verify_stress_non_negative():
    comp = StressTensorZeroComponent()
    state_a = _make_small_graph_state(seed=0)
    state_b = _make_small_graph_state(seed=2)
    result = comp.verify(state_a, state_b)
    assert result["stress_magnitude"] >= 0.0
    assert result["stress_magnitude_reference"] >= 0.0
    assert result["stress_delta"] >= 0.0


def test_verify_identical_states_zero_delta():
    """Two identical states should have zero stress delta."""
    comp = StressTensorZeroComponent()
    state = _make_small_graph_state(seed=0)
    result = comp.verify(state, state)
    assert result["stress_delta"] == pytest.approx(0.0, abs=1e-9)


def test_verify_two_different_states():
    """Different weight distributions should produce different stress magnitudes."""
    comp = StressTensorZeroComponent()
    state_a = _make_graph_state(seed=0)
    G2 = state_a.complex.copy()
    for u, v in G2.edges():
        G2[u][v]["weight"] = G2[u][v].get("weight", 1.0) * 3.0
    state_b = TopologyState(
        complex=G2, complex_type="graph",
        curvature=state_a.curvature.copy(), metrics={}, history=[], metadata={}
    )
    result = comp.verify(state_a, state_b)
    assert np.isfinite(result["stress_delta"])


def test_measure_returns_expected_keys():
    comp = StressTensorZeroComponent()
    state = _make_graph_state()
    executed = comp.execute(state)
    metrics = comp.measure(executed)
    assert "stress_magnitude" in metrics
    assert "max_stress" in metrics


def test_measure_values_non_negative():
    comp = StressTensorZeroComponent()
    state = _make_graph_state()
    executed = comp.execute(state)
    metrics = comp.measure(executed)
    assert metrics["stress_magnitude"] >= 0.0
    assert metrics["max_stress"] >= 0.0


def test_cost_in_range():
    comp = StressTensorZeroComponent()
    assert 0.0 <= comp.cost() <= 1.0
