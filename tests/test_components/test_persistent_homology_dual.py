# tests/test_components/test_persistent_homology_dual.py
from __future__ import annotations
import numpy as np
import pytest
from tecs.types import TopologyState
from tecs.components.representation.simplicial_complex import SimplicialComplexComponent
from tecs.components.verification.persistent_homology_dual import PersistentHomologyDualComponent


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
    comp = PersistentHomologyDualComponent()
    assert comp.name == "persistent_homology_dual"
    assert comp.layer == "verification"
    assert "simplicial" in comp.compatible_types


def test_execute_returns_topology_state():
    comp = PersistentHomologyDualComponent()
    state = _make_simplicial_state()
    result = comp.execute(state)
    assert isinstance(result, TopologyState)
    assert result.complex_type == "simplicial"


def test_execute_sets_defect_score_in_metrics():
    comp = PersistentHomologyDualComponent()
    state = _make_simplicial_state()
    result = comp.execute(state)
    assert "defect_score" in result.metrics
    assert isinstance(result.metrics["defect_score"], float)
    assert result.metrics["defect_score"] >= 0.0


def test_execute_records_history():
    comp = PersistentHomologyDualComponent()
    state = _make_simplicial_state()
    result = comp.execute(state)
    actions = [h["action"] for h in result.history]
    assert "persistent_homology_dual" in actions


def test_execute_history_contains_betti():
    comp = PersistentHomologyDualComponent()
    state = _make_simplicial_state()
    result = comp.execute(state)
    entry = next(h for h in result.history if h["action"] == "persistent_homology_dual")
    assert "primal_betti" in entry
    assert "dual_betti" in entry


def test_verify_returns_dict_with_defect_score():
    comp = PersistentHomologyDualComponent()
    state_a = _make_simplicial_state(seed=0, max_edge_length=0.5)
    state_b = _make_simplicial_state(seed=1, max_edge_length=0.4)
    result = comp.verify(state_a, state_b)
    assert isinstance(result, dict)
    assert "defect_score" in result


def test_verify_returns_betti_keys():
    comp = PersistentHomologyDualComponent()
    state_a = _make_simplicial_state(seed=0)
    state_b = _make_simplicial_state(seed=2)
    result = comp.verify(state_a, state_b)
    assert "betti_0" in result


def test_verify_defect_score_non_negative():
    comp = PersistentHomologyDualComponent()
    state_a = _make_simplicial_state(seed=0)
    state_b = _make_simplicial_state(seed=3)
    result = comp.verify(state_a, state_b)
    assert result["defect_score"] >= 0.0


def test_verify_identical_states_zero_defect():
    comp = PersistentHomologyDualComponent()
    # Same state compared against itself should have defect 0
    state = _make_simplicial_state(seed=0)
    result = comp.verify(state, state)
    assert result["defect_score"] == 0.0


def test_measure_returns_expected_keys():
    comp = PersistentHomologyDualComponent()
    state = _make_simplicial_state()
    executed = comp.execute(state)
    metrics = comp.measure(executed)
    assert "defect_score" in metrics
    assert "betti_0" in metrics
    assert "betti_1" in metrics


def test_measure_betti_non_negative():
    comp = PersistentHomologyDualComponent()
    state = _make_simplicial_state()
    executed = comp.execute(state)
    metrics = comp.measure(executed)
    assert metrics["betti_0"] >= 0.0
    assert metrics["betti_1"] >= 0.0


def test_cost_in_range():
    comp = PersistentHomologyDualComponent()
    assert 0.0 <= comp.cost() <= 1.0
