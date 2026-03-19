# tecs/engine/benchmark_runner.py
"""Runs benchmark tasks on a candidate's simulated topology state."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import networkx as nx
import numpy as np

from tecs.types import TopologyState
from tecs.inference.poincare_utils import generate_poincare_embeddings

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

    Topology benchmarks (concept, contradiction, analogy) test graph
    structure, so we use hop-count here.  Hyperbolic / Ouroboros
    distance is used only in the inference engine (Level 2).
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

    _inference_cache: "TopologyState | None" = None  # class-level cache

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
        """Test actual reasoning ability using fixed eval set."""
        from tecs.inference.eval_set import EVAL_QUERIES, EVAL_ANALOGIES, EVAL_KNOWLEDGE
        from tecs.inference.inference_engine import InferenceEngine
        from tecs.inference.analogy_engine import AnalogyEngine

        # Build knowledge ONCE and cache
        if BenchmarkRunner._inference_cache is None:
            BenchmarkRunner._inference_cache = self._build_eval_knowledge(state, EVAL_KNOWLEDGE)

        test_knowledge = BenchmarkRunner._inference_cache
        engine = InferenceEngine(test_knowledge)
        analogy_engine = AnalogyEngine(test_knowledge)

        scores = {}

        # Query accuracy (Level 1 + 2)
        correct = 0
        total = 0
        for subj, rel, expected, level, category in EVAL_QUERIES:
            result = engine.query(subj, rel)
            if result.answer == expected:
                correct += 1
            total += 1
        scores["query_accuracy"] = correct / max(total, 1)

        # Analogy accuracy
        analogy_correct = 0
        analogy_total = 0
        for source, target_domain, expected_target in EVAL_ANALOGIES:
            results = analogy_engine.find_analogy(source, target_domain, max_results=3)
            if results:
                # Check if expected_target appears in any mapping
                for r in results:
                    if expected_target in r.mapping.values() or r.target_concept == expected_target:
                        analogy_correct += 1
                        break
            analogy_total += 1
        scores["analogy_score"] = analogy_correct / max(analogy_total, 1)

        # Verification rate
        verified_count = 0
        for subj, rel, expected, level, category in EVAL_QUERIES[:5]:
            result = engine.query(subj, rel)
            if result.verified:
                verified_count += 1
        scores["verification_rate"] = verified_count / 5.0

        # Multi-hop accuracy (only Level 2 questions)
        multihop_correct = 0
        multihop_total = 0
        for subj, rel, expected, level, category in EVAL_QUERIES:
            if level >= 2:
                result = engine.query(subj, rel)
                if result.answer == expected:
                    multihop_correct += 1
                multihop_total += 1
        scores["multihop_accuracy"] = multihop_correct / max(multihop_total, 1)

        # Combined
        scores["inference_combined"] = (
            scores["query_accuracy"] * 0.3 +
            scores["multihop_accuracy"] * 0.2 +
            scores["analogy_score"] * 0.3 +
            scores["verification_rate"] * 0.2
        )

        return scores

    def _build_eval_knowledge(self, state: TopologyState, triples: list) -> TopologyState:
        """Build evaluation knowledge state — called once and cached."""
        import networkx as nx
        import numpy as np

        G = nx.Graph()
        entity_set = set()
        for h, r, t in triples:
            entity_set.add(h)
            entity_set.add(t)

        entity_index = {}
        for i, entity in enumerate(sorted(entity_set)):
            G.add_node(i, label=entity)
            entity_index[entity] = i

        relation_weights = {"IsA": 0.9, "HasA": 0.7, "PartOf": 0.8,
                           "RelatedTo": 0.5, "MadeOf": 0.7}
        for h, r, t in triples:
            if h in entity_index and t in entity_index:
                G.add_edge(entity_index[h], entity_index[t],
                          weight=relation_weights.get(r, 0.5), relation=r)

        index_to_entity = {v: k for k, v in entity_index.items()}
        curvature = np.zeros(len(G.nodes))

        # Generate Poincare embeddings for hyperbolic inference
        poincare_emb = generate_poincare_embeddings(G)

        return TopologyState(
            complex=G, complex_type="graph", curvature=curvature,
            metrics={}, history=[],
            metadata={
                "entity_index": entity_index,
                "index_to_entity": index_to_entity,
                "triples": triples,
                "poincare_embeddings": poincare_emb,
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
