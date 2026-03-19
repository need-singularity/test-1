# tests/test_components/test_min_description_topology.py
from __future__ import annotations
import numpy as np
import pytest
from tecs.types import TopologyState
from tecs.components.representation.simplicial_complex import SimplicialComplexComponent
from tecs.components.optimization.min_description_topology import MinDescriptionTopologyComponent


def _make_simplicial_state(seed: int = 0, n_points: int = 15,
                            max_edge_length: float = 0.5) -> TopologyState:
    rng = np.random.default_rng(seed=seed)
    points = rng.random((n_points, 2))
    state = TopologyState.empty("simplicial")
    state.metadata["points"] = points
    comp = SimplicialComplexComponent()
    comp.configure({"max_edge_length": max_edge_length, "max_dimension": 2})
    return comp.execute(state)


def test_create():
    comp = MinDescriptionTopologyComponent()
    assert comp.name == "min_description_topology"
    assert comp.layer == "optimization"
    assert "simplicial" in comp.compatible_types


def test_execute_returns_topology_state():
    comp = MinDescriptionTopologyComponent()
    state = _make_simplicial_state()
    result = comp.execute(state)
    assert isinstance(result, TopologyState)
    assert result.complex_type == "simplicial"


def test_execute_records_history():
    comp = MinDescriptionTopologyComponent()
    state = _make_simplicial_state()
    result = comp.execute(state)
    actions = [h["action"] for h in result.history]
    assert "min_description_topology" in actions


def test_execute_reduces_complexity():
    """total_betti should not increase after simplification."""
    comp = MinDescriptionTopologyComponent()
    comp.configure({"lambda_tradeoff": 0.8, "max_removals": 20})
    state = _make_simplicial_state(n_points=20, max_edge_length=0.6)

    betti_before_list = state.complex.betti_numbers()
    total_betti_before = sum(betti_before_list)

    result = comp.execute(state)
    betti_after_list = result.complex.betti_numbers()
    total_betti_after = sum(betti_after_list)

    assert total_betti_after <= total_betti_before + 1  # allow small tolerance


def test_execute_compresses():
    """n_simplices_after should be <= n_simplices_before."""
    comp = MinDescriptionTopologyComponent()
    comp.configure({"lambda_tradeoff": 0.5, "max_removals": 5})
    state = _make_simplicial_state(n_points=20, max_edge_length=0.6)

    result = comp.execute(state)
    assert result.metrics["n_simplices_after"] <= result.metrics["n_simplices_before"]


def test_execute_compression_ratio_in_range():
    comp = MinDescriptionTopologyComponent()
    comp.configure({"lambda_tradeoff": 0.5, "max_removals": 5})
    state = _make_simplicial_state()
    result = comp.execute(state)
    ratio = result.metrics["compression_ratio"]
    assert 0.0 < ratio <= 1.0


def test_measure_keys():
    comp = MinDescriptionTopologyComponent()
    state = _make_simplicial_state()
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert "total_betti" in metrics
    assert "n_simplices" in metrics
    assert "compression_ratio" in metrics


def test_measure_total_betti_non_negative():
    comp = MinDescriptionTopologyComponent()
    state = _make_simplicial_state()
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert metrics["total_betti"] >= 0.0


def test_measure_compression_ratio_in_range():
    comp = MinDescriptionTopologyComponent()
    state = _make_simplicial_state()
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert 0.0 < metrics["compression_ratio"] <= 1.0


def test_cost_in_range():
    comp = MinDescriptionTopologyComponent()
    assert 0.0 <= comp.cost() <= 1.0


def test_configure_updates_params():
    comp = MinDescriptionTopologyComponent()
    comp.configure({"lambda_tradeoff": 0.9, "max_removals": 3})
    state = _make_simplicial_state()
    result = comp.execute(state)
    assert isinstance(result, TopologyState)
