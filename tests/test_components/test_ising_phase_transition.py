# tests/test_components/test_ising_phase_transition.py
import numpy as np
import networkx as nx
import pytest
from tecs.types import TopologyState
from tecs.components.emergence.ising_phase_transition import IsingPhaseTransitionComponent
from tecs.components.representation.simplicial_complex import SimplicialComplexComponent


def _make_graph_state():
    G = nx.karate_club_graph()
    curvature = np.zeros(len(G.nodes))
    return TopologyState(
        complex=G, complex_type="graph", curvature=curvature,
        metrics={}, history=[], metadata={}
    )


def _make_simplicial_state():
    rng = np.random.default_rng(seed=2)
    points = rng.random((15, 2))
    state = TopologyState.empty("simplicial")
    state.metadata["points"] = points
    comp = SimplicialComplexComponent()
    comp.configure({"max_edge_length": 0.6, "max_dimension": 2})
    return comp.execute(state)


def test_create():
    comp = IsingPhaseTransitionComponent()
    assert comp.name == "ising_phase_transition"
    assert comp.layer == "emergence"
    assert "graph" in comp.compatible_types
    assert "simplicial" in comp.compatible_types


def test_execute_graph_returns_topology_state():
    comp = IsingPhaseTransitionComponent()
    comp.configure({"n_sweeps": 10, "temperature": 2.5})
    state = _make_graph_state()
    result = comp.execute(state)
    assert isinstance(result, TopologyState)
    assert result.complex_type == "graph"


def test_execute_stores_spins_in_metadata():
    comp = IsingPhaseTransitionComponent()
    comp.configure({"n_sweeps": 10, "temperature": 2.5})
    state = _make_graph_state()
    result = comp.execute(state)
    assert "spins" in result.metadata
    spins = result.metadata["spins"]
    assert len(spins) == len(list(state.complex.nodes()))


def test_execute_spins_are_plus_minus_one():
    comp = IsingPhaseTransitionComponent()
    comp.configure({"n_sweeps": 20, "temperature": 2.5})
    state = _make_graph_state()
    result = comp.execute(state)
    spins = result.metadata["spins"]
    for s in spins:
        assert s in (-1.0, 1.0)


def test_execute_simplicial_state():
    comp = IsingPhaseTransitionComponent()
    comp.configure({"n_sweeps": 5, "temperature": 3.0})
    state = _make_simplicial_state()
    result = comp.execute(state)
    assert isinstance(result, TopologyState)
    assert result.complex_type == "simplicial"
    assert "spins" in result.metadata


def test_execute_records_history():
    comp = IsingPhaseTransitionComponent()
    comp.configure({"n_sweeps": 5})
    state = _make_graph_state()
    result = comp.execute(state)
    last = result.history[-1]
    assert last["action"] == "ising_phase_transition"


def test_measure_returns_expected_keys():
    comp = IsingPhaseTransitionComponent()
    comp.configure({"n_sweeps": 20, "temperature": 2.269})
    state = _make_graph_state()
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert "magnetization" in metrics
    assert "energy" in metrics


def test_measure_magnetization_in_range():
    comp = IsingPhaseTransitionComponent()
    comp.configure({"n_sweeps": 50, "temperature": 2.269})
    state = _make_graph_state()
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert 0.0 <= metrics["magnetization"] <= 1.0


def test_measure_low_temperature_high_magnetization():
    """At very low temperature on a complete graph all spins should align."""
    # Use a complete graph so there is no frustration and spins converge easily
    G = nx.complete_graph(10)
    curvature = np.zeros(len(G.nodes))
    state = TopologyState(
        complex=G, complex_type="graph", curvature=curvature,
        metrics={}, history=[], metadata={}
    )
    comp = IsingPhaseTransitionComponent()
    comp.configure({"n_sweeps": 300, "temperature": 0.1})
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert metrics["magnetization"] > 0.5


def test_measure_empty_spins():
    comp = IsingPhaseTransitionComponent()
    state = _make_graph_state()
    # Don't execute — no spins set
    metrics = comp.measure(state)
    assert metrics["magnetization"] == 0.0
    assert metrics["energy"] == 0.0


def test_cost_in_range():
    comp = IsingPhaseTransitionComponent()
    assert 0.0 <= comp.cost() <= 1.0
