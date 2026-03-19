# tecs/engine/topology_simulator.py
from __future__ import annotations

import numpy as np

from tecs.components.registry import ComponentRegistry
from tecs.types import Candidate, TopologyState


class IncompatibleComponentError(Exception):
    pass


class TopologySimulator:
    def __init__(self, registry: ComponentRegistry):
        self._registry = registry

    def simulate(self, candidate: Candidate, points: np.ndarray) -> TopologyState:
        """Run the full 5-layer pipeline for a candidate."""
        # 1. Get representation component, determine complex_type
        repr_comp = self._registry.get("representation", candidate.components["representation"])

        # Determine complex_type from representation component
        complex_type = repr_comp.compatible_types[0]
        state = TopologyState.empty(complex_type)
        state.metadata["points"] = points

        # 2. Execute representation
        state = repr_comp.execute(state)

        # Collect metrics from representation component
        metrics = repr_comp.measure(state)
        state.metrics.update(metrics)

        # 3. Check compatibility and execute remaining layers
        for layer in ["reasoning", "emergence", "verification", "optimization"]:
            comp_name = candidate.components[layer]
            comp = self._registry.get(layer, comp_name)

            if not self._registry.check_compatible(comp, state):
                raise IncompatibleComponentError(
                    f"Component '{comp_name}' (compatible: {comp.compatible_types}) "
                    f"incompatible with state type '{state.complex_type}'"
                )

            if layer == "verification" and hasattr(comp, "verify"):
                # Create reference state for verification
                reference = TopologyState(
                    complex=state.complex,
                    complex_type=state.complex_type,
                    curvature=state.curvature.copy() if len(state.curvature) > 0 else state.curvature,
                    metrics=state.metrics.copy(),
                    history=list(state.history),
                    metadata=dict(state.metadata),
                )
                verify_result = comp.verify(state, reference)
                state.metrics.update(verify_result)
                state = comp.execute(state)
            else:
                state = comp.execute(state)

            # Collect metrics from this component
            metrics = comp.measure(state)
            state.metrics.update(metrics)

        return state
