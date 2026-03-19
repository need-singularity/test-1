# tecs/components/optimization/min_description_topology.py
from __future__ import annotations
import numpy as np
from tecs.types import TopologyState

try:
    import gudhi
    _GUDHI_AVAILABLE = True
except ImportError:
    _GUDHI_AVAILABLE = False


def _get_simplices(stree) -> list:
    """Return list of simplices from either gudhi SimplexTree or _FallbackSimplexTree."""
    if _GUDHI_AVAILABLE and isinstance(stree, gudhi.SimplexTree):
        return [list(s) for s, _ in stree.get_filtration()]
    else:
        return [list(s) for s in stree._simplices]


def _get_persistence_pairs(stree) -> list[tuple[float, float]]:
    """
    Return (birth, death) pairs sorted by persistence (death - birth) ascending.
    For gudhi SimplexTree, use actual persistence. For fallback, assign uniform
    filtration values so all have equal persistence.
    """
    if _GUDHI_AVAILABLE and isinstance(stree, gudhi.SimplexTree):
        stree.compute_persistence()
        pairs = []
        for dim, (birth, death) in stree.persistence():
            if death == float("inf"):
                death = birth + 1e6  # treat infinite death as very large
            pairs.append((birth, death))
        return pairs
    else:
        # Fallback: assign persistence = 1 to all (simplify by count)
        n = len(stree._simplices)
        return [(float(i), float(i) + 1.0) for i in range(n)]


def _count_simplices(stree) -> int:
    if _GUDHI_AVAILABLE and isinstance(stree, gudhi.SimplexTree):
        return stree.num_simplices()
    else:
        return len(stree._simplices)


def _compute_betti(stree) -> list[int]:
    stree.compute_persistence()
    return stree.betti_numbers()


class _PrunedFallbackSimplexTree:
    """A trimmed-down FallbackSimplexTree with a subset of simplices."""

    def __init__(self, simplices: list):
        self._simplices = [tuple(s) for s in simplices]

    def num_simplices(self) -> int:
        return len(self._simplices)

    def compute_persistence(self) -> None:
        pass

    def betti_numbers(self) -> list[int]:
        verts = [s for s in self._simplices if len(s) == 1]
        edges = [s for s in self._simplices if len(s) == 2]
        tris = [s for s in self._simplices if len(s) == 3]
        n = len(verts)
        e = len(edges)

        if n == 0:
            return [0, 0]

        parent = list(range(n))
        vertex_ids = [s[0] for s in verts]
        id_to_idx = {v: i for i, v in enumerate(vertex_ids)}

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: int, y: int) -> None:
            parent[find(x)] = find(y)

        for s in edges:
            if s[0] in id_to_idx and s[1] in id_to_idx:
                union(id_to_idx[s[0]], id_to_idx[s[1]])

        b0 = len({find(i) for i in range(n)})
        b1 = max(0, e - n + b0)
        return [b0, b1]


class MinDescriptionTopologyComponent:
    name = "min_description_topology"
    layer = "optimization"
    compatible_types = ["simplicial"]

    def __init__(self):
        self._params = {"lambda_tradeoff": 0.5, "max_removals": 10}
        self._n_before: int = 0
        self._n_after: int = 0

    def configure(self, params: dict) -> None:
        self._params.update(params)

    def execute(self, state: TopologyState) -> TopologyState:
        stree = state.complex
        if stree is None:
            raise ValueError("state.complex must be a simplex tree (not None)")

        max_removals = int(self._params.get("max_removals", 10))
        lambda_tradeoff = float(self._params.get("lambda_tradeoff", 0.5))

        n_before = _count_simplices(stree)
        self._n_before = n_before

        if _GUDHI_AVAILABLE and isinstance(stree, gudhi.SimplexTree):
            new_stree = self._prune_gudhi(stree, max_removals, lambda_tradeoff)
        else:
            new_stree = self._prune_fallback(stree, max_removals)

        n_after = _count_simplices(new_stree)
        self._n_after = n_after

        new_metrics = state.metrics.copy()
        new_metrics["n_simplices_before"] = float(n_before)
        new_metrics["n_simplices_after"] = float(n_after)
        new_metrics["compression_ratio"] = float(n_after) / float(n_before) if n_before > 0 else 1.0

        return TopologyState(
            complex=new_stree,
            complex_type=state.complex_type,
            curvature=state.curvature.copy() if len(state.curvature) > 0 else np.array([]),
            metrics=new_metrics,
            history=state.history + [
                {
                    "action": "min_description_topology",
                    "n_before": n_before,
                    "n_after": n_after,
                    "lambda_tradeoff": lambda_tradeoff,
                }
            ],
            metadata=state.metadata.copy(),
        )

    def _prune_gudhi(self, stree, max_removals: int, lambda_tradeoff: float):
        """Prune low-persistence simplices from a gudhi SimplexTree."""
        stree.compute_persistence()
        pairs = stree.persistence()

        # Build a list of (persistence, birth, simplex) for non-infinite pairs
        finite_pairs = [(death - birth, birth) for dim, (birth, death) in pairs if death != float("inf")]
        # Sort by persistence ascending (lowest first = candidates for removal)
        finite_pairs.sort(key=lambda x: x[0])

        # Determine filtration threshold: remove simplices with persistence below threshold
        n_remove = min(max_removals, max(0, int(len(finite_pairs) * lambda_tradeoff)))
        if n_remove == 0 or not finite_pairs:
            # Return a copy with no changes
            new_st = gudhi.SimplexTree()
            for simplex, filt in stree.get_filtration():
                new_st.insert(simplex, filtration=filt)
            new_st.make_filtration_non_decreasing()
            return new_st

        threshold = finite_pairs[min(n_remove - 1, len(finite_pairs) - 1)][0]

        # Build new simplex tree keeping only simplices with higher-than-threshold persistence
        # We remove simplices (of dim >= 1) with low filtration values
        all_simplices = list(stree.get_filtration())
        all_simplices.sort(key=lambda x: len(x[0]))

        # Keep all 0-simplices (vertices), filter higher-dim by persistence proxy
        # Use filtration value as a proxy for persistence
        filt_values = [filt for _, filt in all_simplices if len(_) >= 1]
        if not filt_values:
            threshold_filt = 0.0
        else:
            filt_values_nonzero = [f for f in filt_values if f > 0]
            if filt_nonzero_sorted := sorted(filt_values_nonzero):
                threshold_filt = filt_nonzero_sorted[min(n_remove - 1, len(filt_nonzero_sorted) - 1)]
            else:
                threshold_filt = 0.0

        new_st = gudhi.SimplexTree()
        removed = 0
        for simplex, filt in all_simplices:
            if len(simplex) == 1:
                # Always keep vertices
                new_st.insert(simplex, filtration=filt)
            elif removed < n_remove and filt <= threshold_filt and len(simplex) > 1:
                removed += 1
                # Skip this simplex
            else:
                new_st.insert(simplex, filtration=filt)
        new_st.make_filtration_non_decreasing()
        return new_st

    def _prune_fallback(self, stree, max_removals: int):
        """Prune simplices from a _FallbackSimplexTree."""
        simplices = list(stree._simplices)
        # Separate by dimension
        verts = [s for s in simplices if len(s) == 1]
        edges = [s for s in simplices if len(s) == 2]
        higher = [s for s in simplices if len(s) >= 3]

        # Remove from highest dimension first, then edges
        to_remove = max_removals
        pruned_higher = []
        for s in higher:
            if to_remove > 0:
                to_remove -= 1
            else:
                pruned_higher.append(s)

        pruned_edges = []
        for s in edges:
            if to_remove > 0:
                to_remove -= 1
            else:
                pruned_edges.append(s)

        kept = verts + pruned_edges + pruned_higher
        return _PrunedFallbackSimplexTree(kept)

    def measure(self, state: TopologyState) -> dict[str, float]:
        stree = state.complex
        if stree is None:
            return {"total_betti": 0.0, "n_simplices": 0.0, "compression_ratio": 1.0}

        betti = _compute_betti(stree)
        total_betti = float(sum(betti))
        n_simplices = float(_count_simplices(stree))
        n_before = state.metrics.get("n_simplices_before", n_simplices)
        compression_ratio = n_simplices / n_before if n_before > 0 else 1.0

        return {
            "total_betti": total_betti,
            "n_simplices": n_simplices,
            "compression_ratio": compression_ratio,
        }

    def cost(self) -> float:
        return 0.4
