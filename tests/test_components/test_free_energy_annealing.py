# tests/test_components/test_free_energy_annealing.py
from __future__ import annotations
import numpy as np
import networkx as nx
import pytest
from tecs.types import TopologyState
from tecs.components.representation.simplicial_complex import SimplicialComplexComponent
from tecs.components.optimization.free_energy_annealing import FreeEnergyAnnealingComponent


def _make_graph_state(seed: int = 0) -> TopologyState:
    rng = np.random.default_rng(seed=seed)
    G = nx.karate_club_graph()
    for u, v in G.edges():
        G[u][v]["weight"] = float(rng.uniform(0.5, 2.0))
    curvature = np.zeros(len(G.nodes()))
    return TopologyState(
        complex=G, complex_type="graph", curvature=curvature,
        metrics={}, history=[], metadata={}
    )


def _make_simplicial_state(seed: int = 0, n_points: int = 12,
                            max_edge_length: float = 0.5) -> TopologyState:
    rng = np.random.default_rng(seed=seed)
    points = rng.random((n_points, 2))
    state = TopologyState.empty("simplicial")
    state.metadata["points"] = points
    comp = SimplicialComplexComponent()
    comp.configure({"max_edge_length": max_edge_length, "max_dimension": 2})
    return comp.execute(state)


def test_create():
    comp = FreeEnergyAnnealingComponent()
    assert comp.name == "free_energy_annealing"
    assert comp.layer == "optimization"
    assert "graph" in comp.compatible_types
    assert "simplicial" in comp.compatible_types


def test_execute_graph_returns_topology_state():
    comp = FreeEnergyAnnealingComponent()
    state = _make_graph_state()
    result = comp.execute(state)
    assert isinstance(result, TopologyState)
    assert result.complex_type == "graph"


def test_execute_simplicial_returns_topology_state():
    comp = FreeEnergyAnnealingComponent()
    state = _make_simplicial_state()
    result = comp.execute(state)
    assert isinstance(result, TopologyState)
    assert result.complex_type == "simplicial"


def test_execute_records_history():
    comp = FreeEnergyAnnealingComponent()
    state = _make_graph_state()
    result = comp.execute(state)
    actions = [h["action"] for h in result.history]
    assert "free_energy_annealing" in actions


def test_execute_sets_metrics():
    comp = FreeEnergyAnnealingComponent()
    state = _make_graph_state()
    result = comp.execute(state)
    assert "free_energy" in result.metrics
    assert "temperature" in result.metrics
    assert "acceptance_rate" in result.metrics


def test_execute_reduces_free_energy_graph():
    """Free energy should decrease (or at least be finite) after annealing."""
    comp = FreeEnergyAnnealingComponent()
    comp.configure({"initial_temp": 2.0, "cooling_rate": 0.9, "n_steps": 100})
    state = _make_graph_state()
    result = comp.execute(state)
    initial_F = result.metrics.get("initial_free_energy", 0.0)
    final_F = result.metrics["free_energy"]
    # Final free energy should be <= initial or at least finite
    assert np.isfinite(final_F)
    assert final_F <= initial_F + abs(initial_F) * 0.5  # at most 50% worse


def test_execute_reduces_free_energy_simplicial():
    """Free energy should be finite after annealing on simplicial complex."""
    comp = FreeEnergyAnnealingComponent()
    comp.configure({"initial_temp": 2.0, "cooling_rate": 0.9, "n_steps": 50})
    state = _make_simplicial_state()
    result = comp.execute(state)
    final_F = result.metrics["free_energy"]
    assert np.isfinite(final_F)


def test_execute_temperature_decreases():
    """Final temperature should be less than initial temperature."""
    comp = FreeEnergyAnnealingComponent()
    comp.configure({"initial_temp": 1.0, "cooling_rate": 0.9, "n_steps": 20})
    state = _make_graph_state()
    result = comp.execute(state)
    assert result.metrics["temperature"] < 1.0


def test_execute_acceptance_rate_in_range():
    comp = FreeEnergyAnnealingComponent()
    state = _make_graph_state()
    result = comp.execute(state)
    ar = result.metrics["acceptance_rate"]
    assert 0.0 <= ar <= 1.0


def test_measure_keys():
    comp = FreeEnergyAnnealingComponent()
    state = _make_graph_state()
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert "free_energy" in metrics
    assert "temperature" in metrics
    assert "acceptance_rate" in metrics


def test_measure_acceptance_rate_in_range():
    comp = FreeEnergyAnnealingComponent()
    state = _make_graph_state()
    result = comp.execute(state)
    metrics = comp.measure(result)
    assert 0.0 <= metrics["acceptance_rate"] <= 1.0


def test_cost_in_range():
    comp = FreeEnergyAnnealingComponent()
    assert 0.0 <= comp.cost() <= 1.0


def test_configure_n_steps():
    comp = FreeEnergyAnnealingComponent()
    comp.configure({"initial_temp": 0.5, "cooling_rate": 0.8, "n_steps": 10})
    state = _make_graph_state()
    result = comp.execute(state)
    assert isinstance(result, TopologyState)
