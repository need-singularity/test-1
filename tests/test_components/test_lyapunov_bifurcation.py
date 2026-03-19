# tests/test_components/test_lyapunov_bifurcation.py
import numpy as np
import networkx as nx
import pytest
from tecs.types import TopologyState
from tecs.components.emergence.lyapunov_bifurcation import LyapunovBifurcationComponent


def _make_graph_state(curvature: np.ndarray | None = None):
    G = nx.karate_club_graph()
    if curvature is None:
        curvature = np.random.default_rng(seed=5).normal(0.0, 1.0, size=len(G.nodes))
    return TopologyState(
        complex=G, complex_type="graph", curvature=curvature,
        metrics={}, history=[], metadata={}
    )


def test_create():
    comp = LyapunovBifurcationComponent()
    assert comp.name == "lyapunov_bifurcation"
    assert comp.layer == "emergence"
    assert "graph" in comp.compatible_types
    # Not compatible with simplicial
    assert "simplicial" not in comp.compatible_types


def test_execute_returns_topology_state():
    comp = LyapunovBifurcationComponent()
    comp.configure({"perturbation_scale": 1e-5, "n_steps": 20})
    state = _make_graph_state()
    result = comp.execute(state)
    assert isinstance(result, TopologyState)
    assert result.complex_type == "graph"


def test_execute_records_history():
    comp = LyapunovBifurcationComponent()
    comp.configure({"n_steps": 10})
    state = _make_graph_state()
    result = comp.execute(state)
    last = result.history[-1]
    assert last["action"] == "lyapunov_bifurcation"
    assert "lyapunov_exponent" in last
    assert "is_chaotic" in last


def test_execute_empty_curvature():
    comp = LyapunovBifurcationComponent()
    G = nx.karate_club_graph()
    state = TopologyState(
        complex=G, complex_type="graph", curvature=np.array([]),
        metrics={}, history=[], metadata={}
    )
    result = comp.execute(state)
    assert isinstance(result, TopologyState)
    metrics = comp.measure(result)
    assert metrics["lyapunov_exponent"] == 0.0


def test_execute_preserves_curvature():
    comp = LyapunovBifurcationComponent()
    comp.configure({"n_steps": 5})
    curv = np.ones(34) * 0.5
    state = _make_graph_state(curvature=curv)
    result = comp.execute(state)
    np.testing.assert_array_equal(result.curvature, curv)


def test_measure_returns_expected_keys():
    comp = LyapunovBifurcationComponent()
    comp.configure({"n_steps": 20})
    state = _make_graph_state()
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert "lyapunov_exponent" in metrics
    assert "is_chaotic" in metrics


def test_measure_is_chaotic_consistent_with_exponent():
    comp = LyapunovBifurcationComponent()
    comp.configure({"n_steps": 50})
    state = _make_graph_state()
    result = comp.execute(state)
    metrics = comp.measure(result)
    lam = metrics["lyapunov_exponent"]
    chaotic = metrics["is_chaotic"]
    # is_chaotic should be 1.0 if lambda > 0, else 0.0
    if lam > 0:
        assert chaotic == 1.0
    else:
        assert chaotic == 0.0


def test_measure_without_execute_returns_defaults():
    comp = LyapunovBifurcationComponent()
    state = _make_graph_state()
    metrics = comp.measure(state)
    assert metrics["lyapunov_exponent"] == 0.0
    assert metrics["is_chaotic"] == 0.0


def test_configure_accepted():
    comp = LyapunovBifurcationComponent()
    comp.configure({"perturbation_scale": 1e-6, "n_steps": 200})
    state = _make_graph_state()
    result = comp.execute(state)
    assert isinstance(result, TopologyState)


def test_cost_in_range():
    comp = LyapunovBifurcationComponent()
    assert 0.0 <= comp.cost() <= 1.0
