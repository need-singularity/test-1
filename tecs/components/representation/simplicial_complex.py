# tecs/components/representation/simplicial_complex.py
from __future__ import annotations
import numpy as np
from tecs.types import TopologyState

try:
    import gudhi
    _GUDHI_AVAILABLE = True
except ImportError:
    _GUDHI_AVAILABLE = False


class _FallbackSimplexTree:
    """Minimal simplex tree built from scratch when gudhi is unavailable."""

    def __init__(self, points: np.ndarray, max_edge_length: float, max_dimension: int):
        self._simplices: list[tuple] = []
        n = len(points)
        # 0-simplices (vertices)
        for i in range(n):
            self._simplices.append((i,))
        # 1-simplices (edges)
        edges = []
        for i in range(n):
            for j in range(i + 1, n):
                d = float(np.linalg.norm(points[i] - points[j]))
                if d <= max_edge_length:
                    self._simplices.append((i, j))
                    edges.append((i, j))
        # 2-simplices (triangles) if max_dimension >= 2
        if max_dimension >= 2:
            adj: dict[int, set] = {i: set() for i in range(n)}
            for i, j in edges:
                adj[i].add(j)
                adj[j].add(i)
            for i in range(n):
                nbrs = sorted(adj[i])
                for idx_a in range(len(nbrs)):
                    for idx_b in range(idx_a + 1, len(nbrs)):
                        a, b = nbrs[idx_a], nbrs[idx_b]
                        if b in adj[a]:
                            self._simplices.append((i, a, b))

    def num_simplices(self) -> int:
        return len(self._simplices)

    def compute_persistence(self) -> None:
        # No-op for the fallback; betti numbers computed differently
        pass

    def betti_numbers(self) -> list[int]:
        # Count vertices (b0), edges (b1), triangles, etc.
        verts = [s for s in self._simplices if len(s) == 1]
        edges = [s for s in self._simplices if len(s) == 2]
        tris = [s for s in self._simplices if len(s) == 3]
        # Euler characteristic via simplicial homology (chain complex)
        # Use basic Euler formula: b0 - b1 + b2 = V - E + F
        # Approximate: b0 via connected components, b1 = E - V + components, b2 = 0
        n = len(verts)
        e = len(edges)
        f = len(tris)
        # Connected components (b0) via union-find
        parent = list(range(n))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: int, y: int) -> None:
            parent[find(x)] = find(y)

        for s in edges:
            union(s[0], s[1])
        b0 = len({find(i) for i in range(n)})
        # b1 from Euler: chi = b0 - b1 + b2, chi = V - E + F => b1 = E - V + F + b0 - b2
        # Approximation: b2 = 0 for Rips 2-skeleton in typical cases
        b1 = max(0, e - n + b0)
        return [b0, b1]


class SimplicialComplexComponent:
    name = "simplicial_complex"
    layer = "representation"
    compatible_types = ["simplicial"]

    def __init__(self):
        self._params = {"max_edge_length": 2.0, "max_dimension": 2}

    def configure(self, params: dict) -> None:
        self._params.update(params)

    def execute(self, state: TopologyState) -> TopologyState:
        points = state.metadata.get("points")
        if points is None:
            raise ValueError("No 'points' in state.metadata")
        max_edge_length = self._params["max_edge_length"]
        max_dimension = self._params["max_dimension"]
        if _GUDHI_AVAILABLE:
            rips = gudhi.RipsComplex(points=points, max_edge_length=max_edge_length)
            stree = rips.create_simplex_tree(max_dimension=max_dimension)
            n_simplices = stree.num_simplices()
        else:
            stree = _FallbackSimplexTree(
                points=np.asarray(points),
                max_edge_length=max_edge_length,
                max_dimension=max_dimension,
            )
            n_simplices = stree.num_simplices()
        return TopologyState(
            complex=stree,
            complex_type="simplicial",
            curvature=np.array([]),
            metrics=state.metrics.copy(),
            history=state.history + [{"action": "build_rips_complex", "n_simplices": n_simplices}],
            metadata=state.metadata.copy(),
        )

    def measure(self, state: TopologyState) -> dict[str, float]:
        stree = state.complex
        stree.compute_persistence()
        betti = stree.betti_numbers()
        result: dict[str, float] = {}
        for i, b in enumerate(betti):
            result[f"betti_{i}"] = float(b)
        result["euler_characteristic"] = float(
            sum((-1) ** i * b for i, b in enumerate(betti))
        )
        return result

    def cost(self) -> float:
        return 0.3
