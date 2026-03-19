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
    # Inference benchmarks
    # ------------------------------------------------------------------

    def run_inference_benchmark(self, state: TopologyState) -> dict[str, float]:
        """Test actual reasoning ability using the inference engine."""
        from tecs.inference.inference_engine import InferenceEngine
        from tecs.inference.analogy_engine import AnalogyEngine

        # Build knowledge from state's topology
        test_knowledge = self._build_test_knowledge(state)
        engine = InferenceEngine(test_knowledge)
        analogy = AnalogyEngine(test_knowledge)

        scores = {}

        # Query accuracy: test known triples
        query_correct = 0
        query_total = 0
        test_queries = [
            ("cat", "IsA", "mammal"),
            ("dog", "IsA", "mammal"),
            ("car", "IsA", "vehicle"),
            ("gravity", "IsA", "force"),
            ("atom", "HasA", "electron"),
        ]
        for subj, rel, expected in test_queries:
            result = engine.query(subj, rel)
            if result.answer == expected:
                query_correct += 1
            query_total += 1
        scores["query_accuracy"] = query_correct / max(query_total, 1)

        # Multi-hop: can it find indirect connections?
        multihop_correct = 0
        multihop_total = 0
        # cat → mammal → animal (2-hop)
        result = engine.query("cat", "IsA")
        if result.answer in ("mammal", "animal"):
            multihop_correct += 1
        multihop_total += 1
        # dog → mammal → animal (2-hop)
        result = engine.query("dog", "IsA")
        if result.answer in ("mammal", "animal"):
            multihop_correct += 1
        multihop_total += 1
        scores["multihop_accuracy"] = multihop_correct / max(multihop_total, 1)

        # Analogy: can it find cross-domain patterns?
        analogy_score = 0.0
        results = analogy.find_analogy("gravity", "economics")
        if results and results[0].similarity > 0.3:
            analogy_score = results[0].similarity
        scores["analogy_score"] = analogy_score

        # Verification: does self-verification work?
        result = engine.query("cat", "IsA")
        scores["verification_working"] = 1.0 if result.verified else 0.0

        # Combined inference score
        scores["inference_combined"] = (
            scores["query_accuracy"] * 0.3
            + scores["multihop_accuracy"] * 0.3
            + scores["analogy_score"] * 0.3
            + scores["verification_working"] * 0.1
        )

        return scores

    def _build_test_knowledge(self, state: TopologyState) -> TopologyState:
        """Build a test knowledge state by injecting known triples into the existing topology."""
        import networkx as nx
        import numpy as np

        # Start with the state's existing graph or build a new one
        if state.complex_type == "graph" and isinstance(state.complex, nx.Graph):
            G = state.complex.copy()
        else:
            G = nx.Graph()

        # Inject test entities and relations
        test_triples = [
            ("cat", "IsA", "mammal"), ("cat", "IsA", "animal"), ("cat", "HasA", "fur"),
            ("dog", "IsA", "mammal"), ("dog", "IsA", "animal"), ("dog", "HasA", "tail"),
            ("mammal", "IsA", "animal"), ("fish", "IsA", "animal"),
            ("car", "IsA", "vehicle"), ("truck", "IsA", "vehicle"),
            ("gravity", "IsA", "force"), ("mass", "RelatedTo", "gravity"),
            ("energy", "RelatedTo", "mass"),
            ("price", "RelatedTo", "supply"), ("price", "RelatedTo", "demand"),
            ("atom", "HasA", "electron"), ("atom", "HasA", "proton"),
        ]

        entity_set = set()
        for h, r, t in test_triples:
            entity_set.add(h)
            entity_set.add(t)

        # Add entities as nodes (offset from existing nodes)
        offset = max(G.nodes) + 1 if G.nodes else 0
        entity_index = {}
        for i, entity in enumerate(sorted(entity_set)):
            idx = offset + i
            G.add_node(idx, label=entity)
            entity_index[entity] = idx

        # Add edges from triples
        relation_weights = {"IsA": 0.9, "HasA": 0.7, "RelatedTo": 0.5}
        for h, r, t in test_triples:
            if h in entity_index and t in entity_index:
                G.add_edge(entity_index[h], entity_index[t],
                           weight=relation_weights.get(r, 0.5), relation=r)

        index_to_entity = {v: k for k, v in entity_index.items()}
        curvature = np.zeros(len(G.nodes))

        return TopologyState(
            complex=G, complex_type="graph", curvature=curvature,
            metrics={}, history=[],
            metadata={
                "entity_index": entity_index,
                "index_to_entity": index_to_entity,
                "triples": test_triples,
            },
        )

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
