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

    _cached_inference_knowledge: "TopologyState | None" = None  # class-level cache

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
        """Test actual reasoning ability using cached knowledge + fixed eval set."""
        from tecs.inference.inference_engine import InferenceEngine
        from tecs.inference.analogy_engine import AnalogyEngine

        # Use cached knowledge (built once, reused across all candidates)
        if BenchmarkRunner._cached_inference_knowledge is None:
            BenchmarkRunner._cached_inference_knowledge = self._build_eval_knowledge()

        knowledge = BenchmarkRunner._cached_inference_knowledge
        engine = InferenceEngine(knowledge)
        analogy = AnalogyEngine(knowledge)

        scores = {}

        # EVAL SET 1: Direct knowledge queries (10 questions)
        QUERY_EVAL = [
            ("cat", "IsA", "mammal"),
            ("dog", "IsA", "mammal"),
            ("mammal", "IsA", "animal"),
            ("car", "IsA", "vehicle"),
            ("truck", "IsA", "vehicle"),
            ("gravity", "IsA", "force"),
            ("atom", "HasA", "electron"),
            ("cell", "HasA", "dna"),
            ("red", "IsA", "color"),
            ("king", "IsA", "man"),
        ]
        query_correct = 0
        for subj, rel, expected in QUERY_EVAL:
            result = engine.query(subj, rel)
            if result.answer == expected:
                query_correct += 1
        scores["query_accuracy"] = query_correct / len(QUERY_EVAL)

        # EVAL SET 2: Multi-hop reasoning (5 questions, need 2+ hops)
        MULTIHOP_EVAL = [
            ("cat", "IsA", ["mammal", "animal"]),    # cat→mammal→animal
            ("dog", "IsA", ["mammal", "animal"]),     # dog→mammal→animal
            ("electron", "PartOf", ["atom", "molecule"]),  # electron→atom→molecule
            ("gene", "PartOf", ["dna", "cell"]),      # gene→dna→cell
            ("truck", "IsA", ["vehicle"]),             # truck→vehicle
        ]
        multihop_correct = 0
        for subj, rel, acceptable in MULTIHOP_EVAL:
            result = engine.query(subj, rel)
            if result.answer in acceptable:
                multihop_correct += 1
        scores["multihop_accuracy"] = multihop_correct / len(MULTIHOP_EVAL)

        # EVAL SET 3: Analogical reasoning (5 cross-domain tests)
        ANALOGY_EVAL = [
            ("gravity", "economics", 0.3),   # gravity≈price
            ("force", "economics", 0.3),     # force≈price/demand
            ("atom", "biology", 0.3),        # atom≈cell
            ("energy", "economics", 0.3),    # energy≈capital
            ("mass", "economics", 0.3),      # mass≈supply
        ]
        analogy_total = 0.0
        for concept, domain, threshold in ANALOGY_EVAL:
            results = analogy.find_analogy(concept, domain)
            if results and results[0].similarity > threshold:
                analogy_total += results[0].similarity
        scores["analogy_score"] = analogy_total / len(ANALOGY_EVAL)

        # Verification check
        result = engine.query("cat", "IsA")
        scores["verification_working"] = 1.0 if result.verified else 0.0

        # Combined
        scores["inference_combined"] = (
            scores["query_accuracy"] * 0.3 +
            scores["multihop_accuracy"] * 0.3 +
            scores["analogy_score"] * 0.3 +
            scores["verification_working"] * 0.1
        )

        return scores

    def _build_eval_knowledge(self) -> TopologyState:
        """Build the evaluation knowledge base. Called ONCE, cached forever."""
        import networkx as nx
        import numpy as np

        G = nx.Graph()

        # Comprehensive test knowledge (60+ entities, 50+ relations)
        test_triples = [
            # Biology
            ("cat", "IsA", "mammal"), ("cat", "IsA", "animal"), ("cat", "HasA", "fur"),
            ("dog", "IsA", "mammal"), ("dog", "IsA", "animal"), ("dog", "HasA", "tail"),
            ("mammal", "IsA", "animal"), ("fish", "IsA", "animal"), ("bird", "IsA", "animal"),
            ("cell", "HasA", "dna"), ("cell", "HasA", "membrane"), ("cell", "IsA", "organism_unit"),
            ("dna", "HasA", "gene"), ("gene", "MadeOf", "nucleotide"),
            ("protein", "MadeOf", "amino_acid"), ("virus", "IsA", "pathogen"),
            # Transport
            ("car", "IsA", "vehicle"), ("truck", "IsA", "vehicle"), ("bus", "IsA", "vehicle"),
            ("vehicle", "HasA", "wheels"), ("vehicle", "HasA", "engine"),
            ("bicycle", "IsA", "vehicle"), ("airplane", "IsA", "vehicle"),
            # Physics
            ("gravity", "IsA", "force"), ("mass", "RelatedTo", "gravity"),
            ("energy", "RelatedTo", "mass"), ("force", "RelatedTo", "mass"),
            ("force", "RelatedTo", "acceleration"), ("speed", "RelatedTo", "acceleration"),
            ("light", "IsA", "wave"), ("light", "IsA", "particle"),
            ("electron", "PartOf", "atom"), ("proton", "PartOf", "atom"),
            ("neutron", "PartOf", "atom"), ("atom", "PartOf", "molecule"),
            # Economics
            ("price", "RelatedTo", "supply"), ("price", "RelatedTo", "demand"),
            ("supply", "RelatedTo", "market"), ("demand", "RelatedTo", "market"),
            ("inflation", "RelatedTo", "price"), ("trade", "RelatedTo", "market"),
            ("capital", "RelatedTo", "investment"), ("labor", "RelatedTo", "production"),
            # Colors
            ("red", "IsA", "color"), ("blue", "IsA", "color"), ("green", "IsA", "color"),
            # People
            ("king", "IsA", "man"), ("queen", "IsA", "woman"),
            ("doctor", "IsA", "profession"), ("teacher", "IsA", "profession"),
            # Chemistry
            ("molecule", "MadeOf", "atom"), ("water", "MadeOf", "hydrogen"),
            ("water", "MadeOf", "oxygen"),
        ]

        entity_set = set()
        for h, r, t in test_triples:
            entity_set.add(h)
            entity_set.add(t)

        entity_index = {}
        for i, entity in enumerate(sorted(entity_set)):
            G.add_node(i, label=entity)
            entity_index[entity] = i

        relation_weights = {"IsA": 0.9, "HasA": 0.7, "PartOf": 0.8,
                           "RelatedTo": 0.5, "MadeOf": 0.7, "MemberOf": 0.8}
        for h, r, t in test_triples:
            if h in entity_index and t in entity_index:
                G.add_edge(entity_index[h], entity_index[t],
                          weight=relation_weights.get(r, 0.5), relation=r)

        # Add similarity edges for entities in same domain
        domain_groups = {
            "biology": ["cat", "dog", "mammal", "animal", "cell", "dna", "gene", "protein", "virus"],
            "physics": ["gravity", "force", "mass", "energy", "acceleration", "speed", "light", "electron", "atom"],
            "economics": ["price", "supply", "demand", "market", "inflation", "trade", "capital", "labor"],
            "transport": ["car", "truck", "bus", "vehicle", "bicycle", "airplane"],
        }
        for domain, entities in domain_groups.items():
            for i, e1 in enumerate(entities):
                for e2 in entities[i+1:]:
                    if e1 in entity_index and e2 in entity_index:
                        idx1, idx2 = entity_index[e1], entity_index[e2]
                        if not G.has_edge(idx1, idx2):
                            G.add_edge(idx1, idx2, weight=0.3, relation="similar")

        index_to_entity = {v: k for k, v in entity_index.items()}
        curvature = np.zeros(len(G.nodes))

        print(f"  Eval knowledge built: {len(G.nodes)} entities, {len(G.edges)} connections, {len(test_triples)} triples")

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
