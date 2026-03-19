# tests/test_components/test_shadow_manifold_audit.py
from __future__ import annotations
import numpy as np
import networkx as nx
import pytest
from tecs.types import TopologyState
from tecs.components.verification.shadow_manifold_audit import ShadowManifoldAuditComponent


def _make_graph_state(seed: int = 0, n_nodes: int = 10) -> TopologyState:
    rng = np.random.default_rng(seed=seed)
    G = nx.karate_club_graph()
    for u, v in G.edges():
        G[u][v]["weight"] = float(rng.uniform(0.5, 2.0))
    curvature = np.zeros(len(G.nodes()))
    return TopologyState(
        complex=G, complex_type="graph", curvature=curvature,
        metrics={}, history=[], metadata={}
    )


def _make_small_graph_state(seed: int = 0, n_nodes: int = 8,
                              p: float = 0.5) -> TopologyState:
    rng = np.random.default_rng(seed=seed)
    G = nx.erdos_renyi_graph(n_nodes, p, seed=int(seed))
    for u, v in G.edges():
        G[u][v]["weight"] = float(rng.uniform(0.3, 3.0))
    curvature = np.zeros(n_nodes)
    return TopologyState(
        complex=G, complex_type="graph", curvature=curvature,
        metrics={}, history=[], metadata={}
    )


def test_create():
    comp = ShadowManifoldAuditComponent()
    assert comp.name == "shadow_manifold_audit"
    assert comp.layer == "verification"
    assert "graph" in comp.compatible_types


def test_execute_returns_topology_state():
    comp = ShadowManifoldAuditComponent()
    state = _make_graph_state()
    result = comp.execute(state)
    assert isinstance(result, TopologyState)
    assert result.complex_type == "graph"


def test_execute_sets_hallucination_score_in_metrics():
    comp = ShadowManifoldAuditComponent()
    state = _make_graph_state()
    result = comp.execute(state)
    assert "hallucination_score" in result.metrics
    assert result.metrics["hallucination_score"] >= 0.0


def test_execute_sets_confidence_in_metrics():
    comp = ShadowManifoldAuditComponent()
    comp.configure({"confidence": 0.9})
    state = _make_graph_state()
    result = comp.execute(state)
    assert "confidence" in result.metrics
    assert abs(result.metrics["confidence"] - 0.9) < 1e-9


def test_execute_records_history():
    comp = ShadowManifoldAuditComponent()
    state = _make_graph_state()
    result = comp.execute(state)
    actions = [h["action"] for h in result.history]
    assert "shadow_manifold_audit" in actions


def test_verify_returns_hallucination_score():
    comp = ShadowManifoldAuditComponent()
    state_a = _make_small_graph_state(seed=0)
    state_b = _make_small_graph_state(seed=1)
    result = comp.verify(state_a, state_b)
    assert isinstance(result, dict)
    assert "hallucination_score" in result
    assert result["hallucination_score"] >= 0.0


def test_verify_returns_confidence():
    comp = ShadowManifoldAuditComponent()
    state_a = _make_small_graph_state(seed=0)
    state_b = _make_small_graph_state(seed=1)
    result = comp.verify(state_a, state_b)
    assert "confidence" in result
    assert 0.0 <= result["confidence"] <= 1.0


def test_verify_two_different_states():
    """Verify two slightly different graph states produces a finite score."""
    comp = ShadowManifoldAuditComponent()
    state_a = _make_graph_state(seed=0)
    # Build a second state with different weights
    G2 = state_a.complex.copy()
    for u, v in G2.edges():
        G2[u][v]["weight"] = G2[u][v].get("weight", 1.0) * 1.5
    state_b = TopologyState(
        complex=G2, complex_type="graph",
        curvature=state_a.curvature.copy(), metrics={}, history=[], metadata={}
    )
    result = comp.verify(state_a, state_b)
    assert np.isfinite(result["hallucination_score"])


def test_measure_returns_expected_keys():
    comp = ShadowManifoldAuditComponent()
    state = _make_graph_state()
    executed = comp.execute(state)
    metrics = comp.measure(executed)
    assert "hallucination_score" in metrics
    assert "confidence" in metrics


def test_measure_hallucination_non_negative():
    comp = ShadowManifoldAuditComponent()
    state = _make_graph_state()
    executed = comp.execute(state)
    metrics = comp.measure(executed)
    assert metrics["hallucination_score"] >= 0.0


def test_cost_in_range():
    comp = ShadowManifoldAuditComponent()
    assert 0.0 <= comp.cost() <= 1.0
