# tests/test_components/test_kuramoto_oscillator.py
import numpy as np
import networkx as nx
import pytest
from tecs.types import TopologyState
from tecs.components.emergence.kuramoto_oscillator import KuramotoOscillatorComponent
from tecs.components.representation.simplicial_complex import SimplicialComplexComponent


def _make_graph_state():
    G = nx.karate_club_graph()
    curvature = np.zeros(len(G.nodes))
    return TopologyState(
        complex=G, complex_type="graph", curvature=curvature,
        metrics={}, history=[], metadata={}
    )


def _make_simplicial_state():
    rng = np.random.default_rng(seed=1)
    points = rng.random((15, 2))
    state = TopologyState.empty("simplicial")
    state.metadata["points"] = points
    comp = SimplicialComplexComponent()
    comp.configure({"max_edge_length": 0.6, "max_dimension": 2})
    return comp.execute(state)


def test_create():
    comp = KuramotoOscillatorComponent()
    assert comp.name == "kuramoto_oscillator"
    assert comp.layer == "emergence"
    assert "graph" in comp.compatible_types
    assert "simplicial" in comp.compatible_types


def test_execute_graph_returns_topology_state():
    comp = KuramotoOscillatorComponent()
    comp.configure({"n_steps": 10, "K": 1.0, "dt": 0.1})
    state = _make_graph_state()
    result = comp.execute(state)
    assert isinstance(result, TopologyState)
    assert result.complex_type == "graph"


def test_execute_stores_phases_in_metadata():
    comp = KuramotoOscillatorComponent()
    comp.configure({"n_steps": 10, "K": 1.0, "dt": 0.1})
    state = _make_graph_state()
    result = comp.execute(state)
    assert "phases" in result.metadata
    phases = result.metadata["phases"]
    assert len(phases) == len(list(state.complex.nodes()))


def test_execute_simplicial_state():
    comp = KuramotoOscillatorComponent()
    comp.configure({"n_steps": 5, "K": 1.0, "dt": 0.1})
    state = _make_simplicial_state()
    result = comp.execute(state)
    assert isinstance(result, TopologyState)
    assert result.complex_type == "simplicial"
    assert "phases" in result.metadata


def test_execute_records_history():
    comp = KuramotoOscillatorComponent()
    comp.configure({"n_steps": 5})
    state = _make_graph_state()
    result = comp.execute(state)
    assert len(result.history) >= 1
    last = result.history[-1]
    assert last["action"] == "kuramoto_oscillator"


def test_measure_returns_expected_keys():
    comp = KuramotoOscillatorComponent()
    comp.configure({"n_steps": 20, "K": 2.0, "dt": 0.1})
    state = _make_graph_state()
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert "order_parameter_r" in metrics
    assert "mean_frequency" in metrics


def test_measure_order_parameter_in_range():
    comp = KuramotoOscillatorComponent()
    comp.configure({"n_steps": 30, "K": 5.0, "dt": 0.1})
    state = _make_graph_state()
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert 0.0 <= metrics["order_parameter_r"] <= 1.0


def test_measure_empty_phases():
    comp = KuramotoOscillatorComponent()
    state = _make_graph_state()
    # Don't execute — no phases set
    metrics = comp.measure(state)
    assert metrics["order_parameter_r"] == 0.0
    assert metrics["mean_frequency"] == 0.0


def test_cost_in_range():
    comp = KuramotoOscillatorComponent()
    assert 0.0 <= comp.cost() <= 1.0
