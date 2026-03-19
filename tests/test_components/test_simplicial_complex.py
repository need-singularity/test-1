# tests/test_components/test_simplicial_complex.py
import numpy as np
import pytest
from tecs.types import TopologyState
from tecs.components.representation.simplicial_complex import SimplicialComplexComponent


def test_create():
    comp = SimplicialComplexComponent()
    assert comp.name == "simplicial_complex"
    assert comp.layer == "representation"
    assert "simplicial" in comp.compatible_types


def test_execute_builds_complex():
    comp = SimplicialComplexComponent()
    comp.configure({"max_edge_length": 2.0})
    state = TopologyState.empty("simplicial")
    state.metadata["points"] = np.random.rand(20, 3)
    result = comp.execute(state)
    assert result.complex is not None
    assert result.complex_type == "simplicial"


def test_execute_records_history():
    comp = SimplicialComplexComponent()
    comp.configure({"max_edge_length": 2.0})
    state = TopologyState.empty("simplicial")
    state.metadata["points"] = np.random.rand(20, 3)
    result = comp.execute(state)
    assert len(result.history) == 1
    assert result.history[0]["action"] == "build_rips_complex"
    assert "n_simplices" in result.history[0]


def test_execute_raises_without_points():
    comp = SimplicialComplexComponent()
    state = TopologyState.empty("simplicial")
    with pytest.raises(ValueError, match="No 'points'"):
        comp.execute(state)


def test_measure_returns_betti():
    comp = SimplicialComplexComponent()
    comp.configure({"max_edge_length": 2.0})
    state = TopologyState.empty("simplicial")
    state.metadata["points"] = np.random.rand(20, 3)
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert "betti_0" in metrics
    assert "betti_1" in metrics


def test_measure_returns_euler_characteristic():
    comp = SimplicialComplexComponent()
    comp.configure({"max_edge_length": 2.0})
    state = TopologyState.empty("simplicial")
    state.metadata["points"] = np.random.rand(20, 3)
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert "euler_characteristic" in metrics


def test_cost_in_range():
    comp = SimplicialComplexComponent()
    assert 0.0 <= comp.cost() <= 1.0
