# tests/test_components/test_homotopy_deformation.py
import numpy as np
import pytest
from tecs.types import TopologyState
from tecs.components.representation.simplicial_complex import SimplicialComplexComponent
from tecs.components.reasoning.homotopy_deformation import HomotopyDeformationComponent


def _make_simplicial_state():
    """Build a simplicial TopologyState using the representation component."""
    rep = SimplicialComplexComponent()
    rep.configure({"max_edge_length": 2.0, "max_dimension": 2})
    state = TopologyState.empty("simplicial")
    state.metadata["points"] = np.random.default_rng(0).random((20, 3))
    return rep.execute(state)


def test_create():
    comp = HomotopyDeformationComponent()
    assert comp.name == "homotopy_deformation"
    assert comp.layer == "reasoning"
    assert "simplicial" in comp.compatible_types


def test_execute_returns_simplicial_state():
    comp = HomotopyDeformationComponent()
    state = _make_simplicial_state()
    result = comp.execute(state)
    assert result.complex_type == "simplicial"
    assert result.complex is not None


def test_execute_records_history():
    comp = HomotopyDeformationComponent()
    comp.configure({"n_steps": 5})
    state = _make_simplicial_state()
    result = comp.execute(state)
    actions = [h["action"] for h in result.history]
    assert "homotopy_deformation" in actions
    deform_entry = next(h for h in result.history if h["action"] == "homotopy_deformation")
    assert deform_entry["n_steps"] == 5


def test_execute_sets_filtration_in_curvature():
    comp = HomotopyDeformationComponent()
    state = _make_simplicial_state()
    result = comp.execute(state)
    # curvature field holds deformed filtration values
    assert len(result.curvature) > 0


def test_execute_deformation_reduces_filtration():
    comp = HomotopyDeformationComponent()
    comp.configure({"n_steps": 20, "deformation_rate": 0.5})
    state = _make_simplicial_state()
    result = comp.execute(state)
    # After deformation toward zero, mean filtration should be small
    mean_filt = float(np.mean(result.curvature))
    assert mean_filt < 1.0  # should be less than original max (1.0)


def test_execute_preserves_metadata():
    comp = HomotopyDeformationComponent()
    state = _make_simplicial_state()
    state.metadata["tag"] = "test"
    result = comp.execute(state)
    assert result.metadata["tag"] == "test"


def test_configure_deformation_rate():
    comp = HomotopyDeformationComponent()
    comp.configure({"n_steps": 3, "deformation_rate": 0.2})
    state = _make_simplicial_state()
    result = comp.execute(state)
    assert result.complex is not None


def test_measure_returns_filtration_stats():
    comp = HomotopyDeformationComponent()
    state = _make_simplicial_state()
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert "mean_filtration" in metrics
    assert "max_filtration" in metrics


def test_measure_with_empty_curvature():
    comp = HomotopyDeformationComponent()
    state = TopologyState(
        complex=None, complex_type="simplicial", curvature=np.array([]),
        metrics={}, history=[], metadata={}
    )
    metrics = comp.measure(state)
    assert metrics["mean_filtration"] == 0.0
    assert metrics["max_filtration"] == 0.0


def test_measure_max_ge_mean():
    comp = HomotopyDeformationComponent()
    state = _make_simplicial_state()
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert metrics["max_filtration"] >= metrics["mean_filtration"]


def test_cost_in_range():
    comp = HomotopyDeformationComponent()
    assert 0.0 <= comp.cost() <= 1.0


def test_deformed_complex_has_num_simplices():
    comp = HomotopyDeformationComponent()
    state = _make_simplicial_state()
    result = comp.execute(state)
    assert hasattr(result.complex, "num_simplices")
    assert result.complex.num_simplices() > 0
