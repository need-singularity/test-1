# tecs/engine/benchmark_runner.py
"""Runs benchmark tasks on a candidate's simulated topology state."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import networkx as nx
import numpy as np

from tecs.types import TopologyState

if TYPE_CHECKING:
    from tecs.data.data_manager import DataManager

logger = logging.getLogger(__name__)

_DISTANCE_THRESHOLD = 3  # graph hop threshold for "topologically close"
_ANALOGY_THRESHOLD = 2   # max difference in distances for analogy


def _get_graph_nodes(state: TopologyState) -> list:
    """Return a sorted list of node identifiers from the state's complex."""
    ctype = state.complex_type
    if ctype == "graph":
        return list(state.complex.nodes())
    if ctype == "simplicial":
        # gudhi SimplicialComplex or similar — collect 0-simplices
        try:
            sc = state.complex
            # Try gudhi-style skeleton_simplex_tree
            nodes = [s[0][0] for s in sc.get_skeleton(0)]
            return nodes
        except (AttributeError, TypeError):
            pass
        # Fallback: treat as iterable of simplices
        try:
            nodes = set()
            for simplex in state.complex:
                for v in simplex:
                    nodes.add(v)
            return list(nodes)
        except TypeError:
            return []
    if ctype == "hypergraph":
        try:
            return list(state.complex.nodes())
        except AttributeError:
            pass
        try:
            nodes = set()
            for edge in state.complex:
                for v in edge:
                    nodes.add(v)
            return list(nodes)
        except TypeError:
            return []
    return []


def _topological_distance(state: TopologyState, a, b) -> float:
    """Return a topological distance between node indices a and b.

    For graph types uses NetworkX shortest path length (capped at a large
    value when not connected).  For simplicial / hypergraph types counts the
    number of simplices / hyperedges that contain *both* a and b (higher
    co-occurrence → lower distance).  Returns a non-negative float.
    """
    ctype = state.complex_type

    if ctype == "graph":
        G = state.complex
        if not G.has_node(a) or not G.has_node(b):
            return float("inf")
        try:
            return float(nx.shortest_path_length(G, a, b))
        except nx.NetworkXNoPath:
            return float("inf")

    # Simplicial / hypergraph: co-occurrence based
    try:
        if ctype == "simplicial":
            # gudhi-style: iterate over simplices
            try:
                simplices = [s[0] for s in state.complex.get_filtration()]
            except AttributeError:
                simplices = list(state.complex)

            co = sum(1 for s in simplices if a in s and b in s)
            # Invert: more co-occurrence = smaller distance
            return 1.0 / (co + 1)

        if ctype == "hypergraph":
            try:
                edges = state.complex.edges()
            except AttributeError:
                edges = list(state.complex)

            co = sum(1 for e in edges if a in e and b in e)
            return 1.0 / (co + 1)
    except Exception:  # noqa: BLE001
        pass

    return float("inf")


def _entity_to_node(nodes: list, name: str) -> object:
    """Map an arbitrary entity name to an existing graph node.

    Since benchmark data uses real names (dog, cat, …) and graphs use integer
    node IDs, we use a deterministic hash-based mapping so the same entity
    always maps to the same node.
    """
    if not nodes:
        return None
    idx = hash(name) % len(nodes)
    return nodes[idx]


class BenchmarkRunner:
    """Runs the three standard benchmark tasks against a :class:`TopologyState`."""

    def __init__(self, data_manager: "DataManager") -> None:
        self._dm = data_manager

    # ------------------------------------------------------------------
    # Individual benchmarks
    # ------------------------------------------------------------------

    def run_concept_relation(self, state: TopologyState) -> float:
        """Test: does the topology correctly encode concept relations?

        Score = fraction of triples where topological distance < threshold.
        """
        triples = self._dm.get_concept_relations(n=100)
        if not triples:
            return 0.0

        nodes = _get_graph_nodes(state)
        if not nodes:
            return 0.0

        hits = 0
        for triple in triples:
            a = _entity_to_node(nodes, triple["head"])
            b = _entity_to_node(nodes, triple["tail"])
            if a is None or b is None:
                continue
            dist = _topological_distance(state, a, b)
            if dist < _DISTANCE_THRESHOLD:
                hits += 1

        return hits / len(triples)

    def run_contradiction(self, state: TopologyState) -> float:
        """Test: can the topology detect contradictions?

        Score = fraction where positive triple is topologically closer than the
        negative triple.
        """
        pairs = self._dm.get_contradictions(n=50)
        if not pairs:
            return 0.0

        nodes = _get_graph_nodes(state)
        if not nodes:
            return 0.0

        hits = 0
        for pair in pairs:
            pos = pair["positive"]
            neg = pair["negative"]
            a_pos = _entity_to_node(nodes, pos["head"])
            b_pos = _entity_to_node(nodes, pos["tail"])
            a_neg = _entity_to_node(nodes, neg["head"])
            b_neg = _entity_to_node(nodes, neg["tail"])
            if None in (a_pos, b_pos, a_neg, b_neg):
                continue
            d_pos = _topological_distance(state, a_pos, b_pos)
            d_neg = _topological_distance(state, a_neg, b_neg)
            if d_pos < d_neg:
                hits += 1

        return hits / len(pairs)

    def run_analogy(self, state: TopologyState) -> float:
        """Test: does the topology support structural transfer?

        Score = fraction of quads (A:B::C:D) where
        |dist(A,B) - dist(C,D)| < threshold.
        """
        quads = self._dm.get_analogies(n=50)
        if not quads:
            return 0.0

        nodes = _get_graph_nodes(state)
        if not nodes:
            return 0.0

        hits = 0
        for quad in quads:
            na = _entity_to_node(nodes, quad["a"])
            nb = _entity_to_node(nodes, quad["b"])
            nc = _entity_to_node(nodes, quad["c"])
            nd = _entity_to_node(nodes, quad["d"])
            if None in (na, nb, nc, nd):
                continue
            d_ab = _topological_distance(state, na, nb)
            d_cd = _topological_distance(state, nc, nd)
            # Treat inf distances as "very large" for comparison
            if not (np.isinf(d_ab) or np.isinf(d_cd)):
                if abs(d_ab - d_cd) < _ANALOGY_THRESHOLD:
                    hits += 1

        return hits / len(quads)

    # ------------------------------------------------------------------
    # Combined runner
    # ------------------------------------------------------------------

    def run_all(self, state: TopologyState) -> dict[str, float]:
        """Run all 3 benchmarks; return individual + combined scores."""
        concept = self.run_concept_relation(state)
        contradiction = self.run_contradiction(state)
        analogy = self.run_analogy(state)
        return {
            "concept": concept,
            "contradiction": contradiction,
            "analogy": analogy,
            "combined": (concept + contradiction + analogy) / 3,
        }
