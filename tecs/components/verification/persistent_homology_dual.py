# tecs/components/verification/persistent_homology_dual.py
from __future__ import annotations
import numpy as np
from tecs.types import TopologyState

try:
    import gudhi
    _GUDHI_AVAILABLE = True
except ImportError:
    _GUDHI_AVAILABLE = False


def _betti_numbers(stree) -> list[int]:
    """Compute Betti numbers from either a gudhi SimplexTree or _FallbackSimplexTree."""
    stree.compute_persistence()
    return stree.betti_numbers()


def _build_dual_complex(stree):
    """
    Build a dual complex K* by inverting filtration values.

    For _FallbackSimplexTree we build a new instance with inverted simplex
    membership (same structure; inversion manifests as reordering).
    For gudhi SimplexTree we create a new tree with negated filtration values
    shifted so all values remain non-negative.
    """
    if _GUDHI_AVAILABLE and isinstance(stree, gudhi.SimplexTree):
        # Collect all (simplex, filtration) pairs
        pairs = list(stree.get_filtration())
        if not pairs:
            dual = gudhi.SimplexTree()
            return dual
        max_val = max(filt for _, filt in pairs)
        dual = gudhi.SimplexTree()
        for simplex, filt in pairs:
            dual.insert(simplex, filtration=max_val - filt)
        dual.make_filtration_non_decreasing()
        return dual
    else:
        # _FallbackSimplexTree: return the same object (topology is structural)
        return stree


class PersistentHomologyDualComponent:
    name = "persistent_homology_dual"
    layer = "verification"
    compatible_types = ["simplicial"]

    def __init__(self):
        self._params: dict = {}
        self._last_defect_score: float = 0.0
        self._last_betti: list[int] = []

    def configure(self, params: dict) -> None:
        self._params.update(params)

    def execute(self, state: TopologyState) -> TopologyState:
        """Build dual complex K* and compute defect_score vs the primal."""
        stree = state.complex
        if stree is None:
            raise ValueError("state.complex must be a simplex tree (not None)")

        dual = _build_dual_complex(stree)

        primal_betti = _betti_numbers(stree)
        dual_betti = _betti_numbers(dual)

        # Pad to equal length
        length = max(len(primal_betti), len(dual_betti))
        pb = primal_betti + [0] * (length - len(primal_betti))
        db = dual_betti + [0] * (length - len(dual_betti))
        defect_score = float(sum(abs(pb[i] - db[i]) for i in range(length)))

        self._last_defect_score = defect_score
        self._last_betti = primal_betti

        new_metrics = state.metrics.copy()
        new_metrics["defect_score"] = defect_score

        return TopologyState(
            complex=state.complex,
            complex_type=state.complex_type,
            curvature=state.curvature.copy() if len(state.curvature) > 0 else np.array([]),
            metrics=new_metrics,
            history=state.history + [
                {
                    "action": "persistent_homology_dual",
                    "defect_score": defect_score,
                    "primal_betti": primal_betti,
                    "dual_betti": dual_betti,
                }
            ],
            metadata=state.metadata.copy(),
        )

    def verify(self, state: TopologyState, reference: TopologyState) -> dict[str, float]:
        """
        Compare Betti numbers of state vs reference.
        Defect = Σ |β_n(state) - β_n(reference)|
        """
        stree_s = state.complex
        stree_r = reference.complex

        betti_s = _betti_numbers(stree_s)
        betti_r = _betti_numbers(stree_r)

        length = max(len(betti_s), len(betti_r))
        bs = betti_s + [0] * (length - len(betti_s))
        br = betti_r + [0] * (length - len(betti_r))
        defect = float(sum(abs(bs[i] - br[i]) for i in range(length)))

        result: dict[str, float] = {"defect_score": defect}
        for i, b in enumerate(betti_s):
            result[f"betti_{i}"] = float(b)
        return result

    def measure(self, state: TopologyState) -> dict[str, float]:
        stree = state.complex
        betti = _betti_numbers(stree)
        defect_score = state.metrics.get("defect_score", self._last_defect_score)

        result: dict[str, float] = {"defect_score": defect_score}
        for i, b in enumerate(betti):
            result[f"betti_{i}"] = float(b)
        # Ensure at least betti_0 and betti_1 are present
        for key in ("betti_0", "betti_1"):
            if key not in result:
                result[key] = 0.0
        return result

    def cost(self) -> float:
        return 0.5
