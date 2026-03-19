# tests/test_components/test_ricci_flow.py
import numpy as np
import networkx as nx
from tecs.types import TopologyState
from tecs.components.reasoning.ricci_flow import RicciFlowComponent


def _make_graph_state():
    G = nx.karate_club_graph()
    for u, v in G.edges:
        G[u][v]["weight"] = 1.0
    curvatures = np.zeros(len(G.nodes))
    return TopologyState(
        complex=G, complex_type="graph", curvature=curvatures,
        metrics={}, history=[], metadata={}
    )


def test_create():
    comp = RicciFlowComponent()
    assert comp.name == "ricci_flow"
    assert comp.layer == "reasoning"
    assert "graph" in comp.compatible_types


def test_execute_modifies_weights():
    comp = RicciFlowComponent()
    comp.configure({"n_steps": 5})
    state = _make_graph_state()
    original_weights = [state.complex[u][v]["weight"] for u, v in state.complex.edges]
    result = comp.execute(state)
    new_weights = [result.complex[u][v]["weight"] for u, v in result.complex.edges]
    assert original_weights != new_weights


def test_execute_returns_graph_state():
    comp = RicciFlowComponent()
    state = _make_graph_state()
    result = comp.execute(state)
    assert isinstance(result.complex, nx.Graph)
    assert result.complex_type == "graph"


def test_execute_sets_curvature():
    comp = RicciFlowComponent()
    state = _make_graph_state()
    result = comp.execute(state)
    assert len(result.curvature) == len(list(result.complex.nodes))


def test_execute_records_history():
    comp = RicciFlowComponent()
    comp.configure({"n_steps": 3})
    state = _make_graph_state()
    result = comp.execute(state)
    assert len(result.history) == 1
    assert result.history[0]["action"] == "ricci_flow"
    assert result.history[0]["n_steps"] == 3


def test_execute_preserves_metadata():
    comp = RicciFlowComponent()
    state = _make_graph_state()
    state.metadata["key"] = "value"
    result = comp.execute(state)
    assert result.metadata["key"] == "value"


def test_weights_positive():
    comp = RicciFlowComponent()
    comp.configure({"n_steps": 10})
    state = _make_graph_state()
    result = comp.execute(state)
    for u, v in result.complex.edges:
        assert result.complex[u][v]["weight"] > 0.0


def test_measure_returns_curvature():
    comp = RicciFlowComponent()
    comp.configure({"n_steps": 3})
    state = _make_graph_state()
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert "mean_ricci_curvature" in metrics
    assert "std_ricci_curvature" in metrics


def test_measure_with_empty_curvature():
    comp = RicciFlowComponent()
    state = TopologyState(
        complex=nx.Graph(), complex_type="graph", curvature=np.array([]),
        metrics={}, history=[], metadata={}
    )
    metrics = comp.measure(state)
    assert metrics["mean_ricci_curvature"] == 0.0
    assert metrics["std_ricci_curvature"] == 0.0


def test_configure_step_size():
    comp = RicciFlowComponent()
    comp.configure({"n_steps": 2, "step_size": 0.5})
    state = _make_graph_state()
    result = comp.execute(state)
    assert result.complex is not None


def test_cost_in_range():
    comp = RicciFlowComponent()
    assert 0.0 <= comp.cost() <= 1.0
