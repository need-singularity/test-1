# tests/test_components/test_dynamic_hypergraph.py
import numpy as np
import pytest
from tecs.types import TopologyState
from tecs.components.representation.dynamic_hypergraph import DynamicHypergraphComponent


def test_create():
    comp = DynamicHypergraphComponent()
    assert comp.name == "dynamic_hypergraph"
    assert comp.layer == "representation"
    assert "hypergraph" in comp.compatible_types


def test_execute_builds_hypergraph():
    comp = DynamicHypergraphComponent()
    state = TopologyState.empty("hypergraph")
    state.metadata["points"] = np.random.rand(20, 3)
    state.metadata["cluster_threshold"] = 1.0
    result = comp.execute(state)
    assert result.complex is not None
    assert result.complex_type == "hypergraph"


def test_execute_raises_without_points():
    comp = DynamicHypergraphComponent()
    state = TopologyState.empty("hypergraph")
    with pytest.raises(ValueError, match="No 'points'"):
        comp.execute(state)


def test_execute_records_history():
    comp = DynamicHypergraphComponent()
    state = TopologyState.empty("hypergraph")
    state.metadata["points"] = np.random.rand(20, 3)
    result = comp.execute(state)
    assert len(result.history) == 1
    assert result.history[0]["action"] == "build_hypergraph"
    assert "n_hyperedges" in result.history[0]


def test_measure_returns_hyperedge_stats():
    comp = DynamicHypergraphComponent()
    state = TopologyState.empty("hypergraph")
    state.metadata["points"] = np.random.rand(20, 3)
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert "n_hyperedges" in metrics
    assert "mean_hyperedge_size" in metrics
    assert "max_hyperedge_size" in metrics


def test_configure_threshold():
    comp = DynamicHypergraphComponent()
    comp.configure({"cluster_threshold": 0.5})
    state = TopologyState.empty("hypergraph")
    state.metadata["points"] = np.random.rand(20, 3)
    result = comp.execute(state)
    assert result.complex is not None


def test_cost_in_range():
    comp = DynamicHypergraphComponent()
    assert 0.0 <= comp.cost() <= 1.0
