# tests/test_engine/test_topology_simulator.py
import numpy as np
import pytest
from tecs.types import Candidate, TopologyState
from tecs.components.registry import ComponentRegistry
from tecs.engine.topology_simulator import TopologySimulator, IncompatibleComponentError

# Import actual components to register
from tecs.components.representation.riemannian_manifold import RiemannianManifoldComponent
from tecs.components.reasoning.ricci_flow import RicciFlowComponent
from tecs.components.emergence.kuramoto_oscillator import KuramotoOscillatorComponent
from tecs.components.verification.shadow_manifold_audit import ShadowManifoldAuditComponent
from tecs.components.optimization.fisher_distillation import FisherDistillationComponent


def _make_registry():
    reg = ComponentRegistry()
    reg.register(RiemannianManifoldComponent())
    reg.register(RicciFlowComponent())
    reg.register(KuramotoOscillatorComponent())
    reg.register(ShadowManifoldAuditComponent())
    reg.register(FisherDistillationComponent())
    return reg


def test_runs_compatible_combo():
    reg = _make_registry()
    sim = TopologySimulator(reg)
    candidate = Candidate(
        id="test",
        components={
            "representation": "riemannian_manifold",
            "reasoning": "ricci_flow",
            "emergence": "kuramoto_oscillator",
            "verification": "shadow_manifold_audit",
            "optimization": "fisher_distillation",
        },
        parent_ids=[],
        generation=0,
        phase=1,
    )
    result = sim.simulate(candidate, np.random.rand(20, 3))
    assert isinstance(result, TopologyState)
    assert len(result.metrics) > 0
    assert len(result.history) > 0


def test_converts_incompatible_combo():
    """Previously incompatible combos now succeed via automatic type conversion."""
    reg = _make_registry()
    # riemannian_manifold produces "graph", but persistent_homology_dual needs "simplicial"
    from tecs.components.verification.persistent_homology_dual import PersistentHomologyDualComponent
    reg.register(PersistentHomologyDualComponent())
    sim = TopologySimulator(reg)
    candidate = Candidate(
        id="test",
        components={
            "representation": "riemannian_manifold",
            "reasoning": "ricci_flow",
            "emergence": "kuramoto_oscillator",
            "verification": "persistent_homology_dual",
            "optimization": "fisher_distillation",
        },
        parent_ids=[],
        generation=0,
        phase=1,
    )
    # Should succeed now via graph->simplicial conversion
    result = sim.simulate(candidate, np.random.rand(20, 3))
    assert isinstance(result, TopologyState)
    assert len(result.metrics) > 0
    # Verify conversion happened
    convert_actions = [h for h in result.history if "convert" in h.get("action", "")]
    assert len(convert_actions) > 0


def test_state_has_metrics_after_simulation():
    reg = _make_registry()
    sim = TopologySimulator(reg)
    candidate = Candidate(
        id="metrics_test",
        components={
            "representation": "riemannian_manifold",
            "reasoning": "ricci_flow",
            "emergence": "kuramoto_oscillator",
            "verification": "shadow_manifold_audit",
            "optimization": "fisher_distillation",
        },
        parent_ids=[],
        generation=0,
        phase=1,
    )
    result = sim.simulate(candidate, np.random.rand(15, 3))
    # Should have accumulated metrics from multiple components
    assert "mean_curvature" in result.metrics or len(result.metrics) > 0


def test_verify_called_for_verification_layer():
    reg = _make_registry()
    sim = TopologySimulator(reg)
    candidate = Candidate(
        id="verify_test",
        components={
            "representation": "riemannian_manifold",
            "reasoning": "ricci_flow",
            "emergence": "kuramoto_oscillator",
            "verification": "shadow_manifold_audit",
            "optimization": "fisher_distillation",
        },
        parent_ids=[],
        generation=0,
        phase=1,
    )
    result = sim.simulate(candidate, np.random.rand(10, 3))
    # shadow_manifold_audit.verify returns hallucination_score
    assert "hallucination_score" in result.metrics
