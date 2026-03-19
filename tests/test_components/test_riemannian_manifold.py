# tests/test_components/test_riemannian_manifold.py
import numpy as np
import pytest
import networkx as nx
from tecs.types import TopologyState
from tecs.components.representation.riemannian_manifold import RiemannianManifoldComponent


def test_create():
    comp = RiemannianManifoldComponent()
    assert comp.name == "riemannian_manifold"
    assert comp.layer == "representation"
    assert "graph" in comp.compatible_types


def test_execute_builds_graph_with_metric():
    comp = RiemannianManifoldComponent()
    state = TopologyState.empty("graph")
    state.metadata["points"] = np.random.rand(20, 3)
    state.metadata["k_neighbors"] = 5
    result = comp.execute(state)
    assert isinstance(result.complex, nx.Graph)
    assert len(result.complex.nodes) == 20
    assert result.curvature.shape[0] > 0


def test_execute_raises_without_points():
    comp = RiemannianManifoldComponent()
    state = TopologyState.empty("graph")
    with pytest.raises(ValueError, match="No 'points'"):
        comp.execute(state)


def test_execute_records_history():
    comp = RiemannianManifoldComponent()
    state = TopologyState.empty("graph")
    state.metadata["points"] = np.random.rand(20, 3)
    result = comp.execute(state)
    assert len(result.history) == 1
    assert result.history[0]["action"] == "build_knn_graph"
    assert result.history[0]["n_nodes"] == 20


def test_configure_k_neighbors():
    comp = RiemannianManifoldComponent()
    comp.configure({"k_neighbors": 3})
    state = TopologyState.empty("graph")
    state.metadata["points"] = np.random.rand(20, 3)
    result = comp.execute(state)
    assert isinstance(result.complex, nx.Graph)


def test_measure_returns_curvature_stats():
    comp = RiemannianManifoldComponent()
    state = TopologyState.empty("graph")
    state.metadata["points"] = np.random.rand(20, 3)
    state.metadata["k_neighbors"] = 5
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert "mean_curvature" in metrics
    assert "max_curvature" in metrics
    assert "std_curvature" in metrics


def test_cost_in_range():
    comp = RiemannianManifoldComponent()
    assert 0.0 <= comp.cost() <= 1.0
