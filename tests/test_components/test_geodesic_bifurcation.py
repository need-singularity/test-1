# tests/test_components/test_geodesic_bifurcation.py
import numpy as np
import networkx as nx
from tecs.types import TopologyState
from tecs.components.reasoning.geodesic_bifurcation import GeodesicBifurcationComponent


def _make_graph_state(seed: int = 0) -> TopologyState:
    rng = np.random.default_rng(seed)
    G = nx.karate_club_graph()
    for u, v in G.edges:
        G[u][v]["weight"] = float(rng.uniform(0.5, 1.5))
    nodes_list = list(G.nodes)
    curvature = rng.uniform(-0.5, 0.5, size=len(nodes_list))
    return TopologyState(
        complex=G, complex_type="graph", curvature=curvature,
        metrics={}, history=[], metadata={}
    )


def test_create():
    comp = GeodesicBifurcationComponent()
    assert comp.name == "geodesic_bifurcation"
    assert comp.layer == "reasoning"
    assert "graph" in comp.compatible_types


def test_execute_returns_graph_state():
    comp = GeodesicBifurcationComponent()
    state = _make_graph_state()
    result = comp.execute(state)
    assert isinstance(result.complex, nx.Graph)
    assert result.complex_type == "graph"


def test_execute_records_history():
    comp = GeodesicBifurcationComponent()
    comp.configure({"n_branches": 2})
    state = _make_graph_state()
    result = comp.execute(state)
    actions = [h["action"] for h in result.history]
    assert "geodesic_bifurcation" in actions


def test_execute_sets_curvature():
    comp = GeodesicBifurcationComponent()
    state = _make_graph_state()
    result = comp.execute(state)
    assert len(result.curvature) == len(list(result.complex.nodes))


def test_execute_modifies_weights():
    comp = GeodesicBifurcationComponent()
    comp.configure({"perturbation_scale": 0.3})
    state = _make_graph_state()
    original_weights = {(u, v): state.complex[u][v]["weight"] for u, v in state.complex.edges}
    result = comp.execute(state)
    new_weights = {(u, v): result.complex[u][v]["weight"] for u, v in result.complex.edges}
    # At least some weights should change
    diffs = [abs(new_weights[(u, v)] - original_weights[(u, v)]) for u, v in state.complex.edges]
    assert max(diffs) > 0.0


def test_all_weights_positive():
    comp = GeodesicBifurcationComponent()
    state = _make_graph_state()
    result = comp.execute(state)
    for u, v in result.complex.edges:
        assert result.complex[u][v]["weight"] > 0.0


def test_execute_preserves_node_count():
    comp = GeodesicBifurcationComponent()
    state = _make_graph_state()
    result = comp.execute(state)
    assert len(result.complex.nodes) == len(state.complex.nodes)
    assert len(result.complex.edges) == len(state.complex.edges)


def test_execute_preserves_metadata():
    comp = GeodesicBifurcationComponent()
    state = _make_graph_state()
    state.metadata["info"] = "test"
    result = comp.execute(state)
    assert result.metadata["info"] == "test"


def test_measure_returns_keys():
    comp = GeodesicBifurcationComponent()
    state = _make_graph_state()
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert "n_bifurcation_points" in metrics
    assert "branch_stability" in metrics


def test_measure_branch_stability_in_range():
    comp = GeodesicBifurcationComponent()
    state = _make_graph_state()
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert 0.0 <= metrics["branch_stability"] <= 1.0


def test_configure_n_branches():
    comp = GeodesicBifurcationComponent()
    comp.configure({"n_branches": 5, "perturbation_scale": 0.1})
    state = _make_graph_state()
    result = comp.execute(state)
    entry = next(h for h in result.history if h["action"] == "geodesic_bifurcation")
    assert entry["n_branches"] == 5


def test_empty_curvature_does_not_crash():
    comp = GeodesicBifurcationComponent()
    G = nx.karate_club_graph()
    for u, v in G.edges:
        G[u][v]["weight"] = 1.0
    state = TopologyState(
        complex=G, complex_type="graph", curvature=np.array([]),
        metrics={}, history=[], metadata={}
    )
    result = comp.execute(state)
    assert result.complex is not None


def test_cost_in_range():
    comp = GeodesicBifurcationComponent()
    assert 0.0 <= comp.cost() <= 1.0
