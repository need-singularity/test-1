# tecs/components/reasoning/homotopy_deformation.py
from __future__ import annotations
import numpy as np
from tecs.types import TopologyState


class HomotopyDeformationComponent:
    name = "homotopy_deformation"
    layer = "reasoning"
    compatible_types = ["simplicial"]

    def __init__(self):
        self._params = {"n_steps": 10, "deformation_rate": 0.1}

    def configure(self, params: dict) -> None:
        self._params.update(params)

    def execute(self, state: TopologyState) -> TopologyState:
        stree = state.complex
        n_steps = self._params["n_steps"]
        rate = self._params["deformation_rate"]

        # Extract existing filtration values or generate them from simplex count
        filtration_values = self._extract_filtration_values(stree)

        # Deform filtration values toward a target (lower values = simpler topology)
        target = np.zeros_like(filtration_values)
        deformed = filtration_values.copy()
        for _ in range(n_steps):
            deformed = deformed + rate * (target - deformed)

        # Build a lightweight deformed complex representation
        deformed_complex = _DeformedSimplexTree(stree, deformed)

        mean_filt = float(np.mean(deformed)) if len(deformed) > 0 else 0.0
        max_filt = float(np.max(deformed)) if len(deformed) > 0 else 0.0

        return TopologyState(
            complex=deformed_complex,
            complex_type="simplicial",
            curvature=deformed,
            metrics=state.metrics.copy(),
            history=state.history + [
                {
                    "action": "homotopy_deformation",
                    "n_steps": n_steps,
                    "mean_filtration": mean_filt,
                    "max_filtration": max_filt,
                }
            ],
            metadata=state.metadata.copy(),
        )

    def _extract_filtration_values(self, stree) -> np.ndarray:
        """Extract filtration values from the simplex tree, or generate synthetic ones."""
        # Try gudhi-style interface first
        if hasattr(stree, "get_filtration"):
            try:
                vals = np.array([filt for _, filt in stree.get_filtration()], dtype=float)
                if len(vals) > 0:
                    return vals
            except Exception:
                pass
        # Try fallback simplex tree interface
        if hasattr(stree, "_simplices"):
            n = len(stree._simplices)
            if n > 0:
                return np.linspace(0.0, 1.0, n)
        # Final fallback: use num_simplices if available
        if hasattr(stree, "num_simplices"):
            n = stree.num_simplices()
            if n > 0:
                return np.linspace(0.0, 1.0, n)
        return np.array([0.5])

    def measure(self, state: TopologyState) -> dict[str, float]:
        filt = state.curvature  # deformed filtration values stored in curvature field
        if len(filt) == 0:
            return {"mean_filtration": 0.0, "max_filtration": 0.0}
        return {
            "mean_filtration": float(np.mean(filt)),
            "max_filtration": float(np.max(filt)),
        }

    def cost(self) -> float:
        return 0.4


class _DeformedSimplexTree:
    """Wraps an original simplex tree with updated filtration values for downstream use."""

    def __init__(self, original, filtration_values: np.ndarray):
        self._original = original
        self._filtration_values = filtration_values

    def num_simplices(self) -> int:
        if hasattr(self._original, "num_simplices"):
            return self._original.num_simplices()
        return len(self._filtration_values)

    def compute_persistence(self) -> None:
        if hasattr(self._original, "compute_persistence"):
            self._original.compute_persistence()

    def betti_numbers(self) -> list[int]:
        if hasattr(self._original, "betti_numbers"):
            return self._original.betti_numbers()
        return [1, 0]

    def get_filtration(self):
        """Yield (simplex, filtration_value) pairs with deformed values."""
        if hasattr(self._original, "get_filtration"):
            try:
                pairs = list(self._original.get_filtration())
                for i, (simplex, _) in enumerate(pairs):
                    filt = self._filtration_values[i] if i < len(self._filtration_values) else 0.0
                    yield simplex, filt
                return
            except Exception:
                pass
        for i, filt in enumerate(self._filtration_values):
            yield (i,), float(filt)
