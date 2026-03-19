# tests/test_components/test_fisher_distillation.py
from __future__ import annotations
import numpy as np
import networkx as nx
import pytest
from tecs.types import TopologyState
from tecs.components.optimization.fisher_distillation import FisherDistillationComponent


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


def test_create():
    comp = FisherDistillationComponent()
    assert comp.name == "fisher_distillation"
    assert comp.layer == "optimization"
    assert "graph" in comp.compatible_types


def test_execute_returns_topology_state():
    comp = FisherDistillationComponent()
    state = _make_graph_state()
    result = comp.execute(state)
    assert isinstance(result, TopologyState)
    assert result.complex_type == "graph"


def test_execute_records_history():
    comp = FisherDistillationComponent()
    state = _make_graph_state()
    result = comp.execute(state)
    actions = [h["action"] for h in result.history]
    assert "fisher_distillation" in actions


def test_execute_compresses():
    """compression_ratio < 1.0 when k < n_nodes."""
    comp = FisherDistillationComponent()
    comp.configure({"alpha": 0.5, "k_eigenvalues": 5})
    state = _make_graph_state()
    result = comp.execute(state)
    # n_nodes = 34 for karate club; k=5 < 34 => ratio < 1
    assert result.metrics["compression_ratio"] < 1.0


def test_execute_adjusts_weights():
    """Edge weights in result should be positive."""
    comp = FisherDistillationComponent()
    state = _make_graph_state()
    result = comp.execute(state)
    G = result.complex
    for u, v, data in G.edges(data=True):
        assert data.get("weight", 1.0) > 0.0


def test_measure_keys():
    comp = FisherDistillationComponent()
    state = _make_graph_state()
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert "compression_ratio" in metrics
    assert "mean_weight" in metrics
    assert "info_retained" in metrics


def test_measure_compression_ratio_in_range():
    comp = FisherDistillationComponent()
    comp.configure({"alpha": 0.5, "k_eigenvalues": 5})
    state = _make_graph_state()
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert 0.0 < metrics["compression_ratio"] <= 1.0


def test_measure_info_retained_in_range():
    comp = FisherDistillationComponent()
    state = _make_graph_state()
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert 0.0 <= metrics["info_retained"] <= 1.0 + 1e-9


def test_measure_mean_weight_positive():
    comp = FisherDistillationComponent()
    state = _make_graph_state()
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert metrics["mean_weight"] > 0.0


def test_cost_in_range():
    comp = FisherDistillationComponent()
    assert 0.0 <= comp.cost() <= 1.0


def test_configure_updates_alpha():
    comp = FisherDistillationComponent()
    comp.configure({"alpha": 0.1, "k_eigenvalues": 3})
    state = _make_graph_state()
    result = comp.execute(state)
    assert isinstance(result, TopologyState)
