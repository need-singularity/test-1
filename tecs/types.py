# tecs/types.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Union
import uuid
import random
import numpy as np

LAYERS = ["representation", "reasoning", "emergence", "verification", "optimization"]

COMPONENT_POOL: dict[str, list[str]] = {
    "representation": ["simplicial_complex", "riemannian_manifold", "dynamic_hypergraph"],
    "reasoning": ["ricci_flow", "homotopy_deformation", "geodesic_bifurcation"],
    "emergence": ["kuramoto_oscillator", "ising_phase_transition", "lyapunov_bifurcation"],
    "verification": ["persistent_homology_dual", "shadow_manifold_audit", "stress_tensor_zero"],
    "optimization": ["min_description_topology", "fisher_distillation", "free_energy_annealing"],
}

VALID_COMPLEX_TYPES = {"simplicial", "graph", "hypergraph"}


@dataclass
class TopologyState:
    complex: Any
    complex_type: str
    curvature: np.ndarray
    metrics: dict[str, float] = field(default_factory=dict)
    history: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @classmethod
    def empty(cls, complex_type: str) -> TopologyState:
        if complex_type not in VALID_COMPLEX_TYPES:
            raise ValueError(f"Invalid complex_type: {complex_type}. Must be one of {VALID_COMPLEX_TYPES}")
        return cls(
            complex=None,
            complex_type=complex_type,
            curvature=np.array([]),
            metrics={},
            history=[],
            metadata={},
        )


@dataclass
class Candidate:
    id: str
    components: dict[str, str]
    parent_ids: list[str]
    generation: int
    phase: int
    fitness: float = 0.0
    mutation_layer: str | None = None
    metrics: dict[str, float] = field(default_factory=dict)

    @classmethod
    def random(cls, generation: int, phase: int, rng: random.Random | None = None) -> Candidate:
        r = rng or random.Random()
        components = {layer: r.choice(options) for layer, options in COMPONENT_POOL.items()}
        return cls(
            id=str(uuid.uuid4()),
            components=components,
            parent_ids=[],
            generation=generation,
            phase=phase,
        )

    def hamming_distance(self, other: Candidate) -> int:
        return sum(1 for layer in LAYERS if self.components[layer] != other.components[layer])
