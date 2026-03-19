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

    def _convert_state(self, state: TopologyState, target_type: str) -> TopologyState:
        """Convert state to a compatible type."""
        if state.complex_type == target_type:
            return state

        import networkx as nx

        if state.complex_type == "graph" and target_type == "simplicial":
            # Graph -> Simplicial: clique complex
            G = state.complex
            try:
                import gudhi
                stree = gudhi.SimplexTree()
            except ImportError:
                from tecs.components.representation.simplicial_complex import _FallbackSimplexTree
                # Build a minimal fallback from the graph
                points = state.metadata.get("points", np.zeros((len(G.nodes), 2)))
                stree = _FallbackSimplexTree(
                    points=np.asarray(points),
                    max_edge_length=float("inf"),
                    max_dimension=2,
                )
                # The fallback constructor builds from points, but we need
                # the graph structure. Build manually instead.
                class _ManualSimplexTree:
                    def __init__(self):
                        self._simplices: dict[int, dict] = {}

                    def insert(self, simplex, filtration=0.0):
                        dim = len(simplex) - 1
                        key = tuple(sorted(simplex))
                        self._simplices.setdefault(dim, {})[key] = filtration

                    def num_simplices(self):
                        return sum(len(v) for v in self._simplices.values())

                    def compute_persistence(self):
                        pass

                    def betti_numbers(self):
                        verts = len(self._simplices.get(0, {}))
                        edges = len(self._simplices.get(1, {}))
                        tris = len(self._simplices.get(2, {}))
                        parent = list(range(verts))
                        vert_list = sorted(self._simplices.get(0, {}).keys())
                        vert_map = {v[0]: i for i, v in enumerate(vert_list)}

                        def find(x):
                            while parent[x] != x:
                                parent[x] = parent[parent[x]]
                                x = parent[x]
                            return x

                        def union(x, y):
                            parent[find(x)] = find(y)

                        for e in self._simplices.get(1, {}):
                            a, b = e
                            if a in vert_map and b in vert_map:
                                union(vert_map[a], vert_map[b])
                        b0 = len({find(i) for i in range(verts)}) if verts > 0 else 0
                        b1 = max(0, edges - verts + b0)
                        return [b0, b1]

                    def get_skeleton(self, dim):
                        results = []
                        for d in range(dim + 1):
                            for simplex, filt in self._simplices.get(d, {}).items():
                                results.append((list(simplex), filt))
                        return results

                stree = _ManualSimplexTree()

            if hasattr(stree, 'insert'):
                for node in G.nodes:
                    stree.insert([node])
                for u, v in G.edges:
                    stree.insert([u, v])
                # Add triangles: for each edge (u,v), find common neighbors
                adj = {n: set(G.neighbors(n)) for n in G.nodes}
                seen_triangles = set()
                for u, v in G.edges:
                    common = adj[u] & adj[v]
                    for w in common:
                        tri = tuple(sorted([u, v, w]))
                        if tri not in seen_triangles:
                            seen_triangles.add(tri)
                            stree.insert(list(tri))

            return TopologyState(
                complex=stree, complex_type="simplicial",
                curvature=state.curvature, metrics=state.metrics.copy(),
                history=state.history + [{"action": "convert_graph_to_simplicial"}],
                metadata=state.metadata.copy(),
            )

        elif state.complex_type == "simplicial" and target_type == "graph":
            # Simplicial -> Graph: 1-skeleton
            G = nx.Graph()
            stree = state.complex
            if hasattr(stree, 'get_skeleton'):
                for simplex, filt in stree.get_skeleton(0):
                    G.add_node(simplex[0])
                for simplex, filt in stree.get_skeleton(1):
                    if len(simplex) == 2:
                        G.add_edge(simplex[0], simplex[1], weight=1.0)
            elif hasattr(stree, '_simplices'):
                for v in stree._simplices.get(0, {}):
                    G.add_node(v[0] if isinstance(v, tuple) else v)
                for e in stree._simplices.get(1, {}):
                    if isinstance(e, tuple) and len(e) == 2:
                        G.add_edge(e[0], e[1], weight=1.0)
            curvature = np.zeros(len(G.nodes))
            return TopologyState(
                complex=G, complex_type="graph", curvature=curvature,
                metrics=state.metrics.copy(),
                history=state.history + [{"action": "convert_simplicial_to_graph"}],
                metadata=state.metadata.copy(),
            )

        elif state.complex_type == "hypergraph" and target_type == "graph":
            # Hypergraph -> Graph: project to pairwise
            H = state.complex
            G = nx.Graph()
            for edge_id in H.edges:
                nodes = list(H.edges[edge_id])
                for i, u in enumerate(nodes):
                    G.add_node(u)
                    for v in nodes[i + 1:]:
                        G.add_edge(u, v, weight=1.0)
            curvature = np.zeros(len(G.nodes))
            return TopologyState(
                complex=G, complex_type="graph", curvature=curvature,
                metrics=state.metrics.copy(),
                history=state.history + [{"action": "convert_hypergraph_to_graph"}],
                metadata=state.metadata.copy(),
            )

        elif state.complex_type == "graph" and target_type == "hypergraph":
            try:
                import hypernetx as hnx
            except ImportError:
                return state
            G = state.complex
            hyperedges = {}
            for node in G.nodes:
                neighbors = tuple(sorted([node] + list(G.neighbors(node))))
                if len(neighbors) >= 2:
                    hyperedges[f"he_{node}"] = neighbors
            H = hnx.Hypergraph(hyperedges)
            return TopologyState(
                complex=H, complex_type="hypergraph", curvature=np.array([]),
                metrics=state.metrics.copy(),
                history=state.history + [{"action": "convert_graph_to_hypergraph"}],
                metadata=state.metadata.copy(),
            )

        # Fallback: try going through graph as intermediate
        if target_type == "simplicial" and state.complex_type == "hypergraph":
            graph_state = self._convert_state(state, "graph")
            return self._convert_state(graph_state, "simplicial")
        elif target_type == "hypergraph" and state.complex_type == "simplicial":
            graph_state = self._convert_state(state, "graph")
            return self._convert_state(graph_state, "hypergraph")

        return state  # give up, let it fail naturally

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
                # Try to convert state to a compatible type
                target_type = comp.compatible_types[0]
                state = self._convert_state(state, target_type)
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
