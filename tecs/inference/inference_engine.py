"""Topological reasoning engine -- multi-level inference."""
from __future__ import annotations
import numpy as np
import networkx as nx
from tecs.types import TopologyState


class InferenceResult:
    def __init__(self, answer: str, confidence: float, level: int,
                 reasoning: str, path: list[str], verified: bool):
        self.answer = answer
        self.confidence = confidence
        self.level = level
        self.reasoning = reasoning
        self.path = path
        self.verified = verified

    def to_dict(self) -> dict:
        return {
            "answer": self.answer, "confidence": round(self.confidence, 4),
            "level": self.level, "reasoning": self.reasoning,
            "path": self.path, "verified": self.verified,
        }

    def __repr__(self):
        v = "verified" if self.verified else "unverified"
        return f"[L{self.level}|{v}] {self.answer} ({self.confidence:.2f}) -- {self.reasoning}"


class InferenceEngine:
    def __init__(self, knowledge: TopologyState):
        self._knowledge = knowledge
        self._G: nx.Graph = knowledge.complex
        self._entity_index: dict[str, int] = knowledge.metadata.get("entity_index", {})
        self._index_to_entity: dict[int, str] = knowledge.metadata.get("index_to_entity", {})
        self._triples = knowledge.metadata.get("triples", [])

    def query(self, subject: str, relation: str, obj: str = "?") -> InferenceResult:
        """Multi-level inference."""
        if subject not in self._entity_index:
            return InferenceResult(answer="unknown", confidence=0.0, level=0,
                                   reasoning=f"'{subject}' not in knowledge base",
                                   path=[], verified=False)

        # Try each level, return best result
        results = []

        # Level 1: Direct path
        r1 = self._level1_direct(subject, relation, obj)
        if r1:
            results.append(r1)

        # Level 2: Multi-path
        r2 = self._level2_multipath(subject, relation, obj)
        if r2:
            results.append(r2)

        # Level 3: Homology matching
        r3 = self._level3_homology(subject, relation, obj)
        if r3:
            results.append(r3)

        # Level 4: Emergent reasoning
        r4 = self._level4_emergent(subject, relation, obj)
        if r4:
            results.append(r4)

        if not results:
            return InferenceResult(answer="unknown", confidence=0.0, level=0,
                                   reasoning="no inference path found",
                                   path=[], verified=False)

        # Pick best by confidence
        best = max(results, key=lambda r: r.confidence)

        # Level 5: Self-verification
        best.verified = self._level5_verify(subject, relation, best.answer)
        if not best.verified:
            best.confidence *= 0.5  # penalize unverified

        return best

    def _level1_direct(self, subject: str, relation: str, obj: str) -> InferenceResult | None:
        """Level 1: Direct edge lookup."""
        subj_idx = self._entity_index.get(subject)
        if subj_idx is None:
            return None

        # Check direct triples
        for h, r, t in self._triples:
            if h == subject and r == relation:
                if obj == "?" or t == obj:
                    return InferenceResult(
                        answer=t, confidence=0.9, level=1,
                        reasoning=f"direct triple: ({subject}, {relation}, {t})",
                        path=[subject, t], verified=False,
                    )

        # Check graph neighbors with matching relation
        for nb in self._G.neighbors(subj_idx):
            edge_data = self._G[subj_idx][nb]
            if edge_data.get("relation") == relation:
                entity = self._index_to_entity.get(nb, str(nb))
                if obj == "?" or entity == obj:
                    return InferenceResult(
                        answer=entity, confidence=float(edge_data.get("weight", 0.5)),
                        level=1, reasoning=f"direct edge ({relation})",
                        path=[subject, entity], verified=False,
                    )
        return None

    def _level2_multipath(self, subject: str, relation: str, obj: str) -> InferenceResult | None:
        """Level 2: Multi-hop path search."""
        subj_idx = self._entity_index.get(subject)
        if subj_idx is None:
            return None

        # BFS up to 3 hops
        visited = {subj_idx: [subject]}
        queue = [(subj_idx, 0)]
        candidates = []

        while queue:
            node, depth = queue.pop(0)
            if depth >= 3:
                continue
            for nb in self._G.neighbors(node):
                if nb not in visited:
                    entity = self._index_to_entity.get(nb, str(nb))
                    path = visited[node] + [entity]
                    visited[nb] = path

                    # Check if this entity matches relation via triples
                    for h, r, t in self._triples:
                        if h == subject and r == relation and t == entity:
                            conf = 0.8 / (depth + 1)  # confidence decreases with hops
                            candidates.append(InferenceResult(
                                answer=entity, confidence=conf, level=2,
                                reasoning=f"{depth+1}-hop path via triples",
                                path=path, verified=False,
                            ))
                        elif t == entity and r == relation:
                            # Reverse direction check
                            conf = 0.6 / (depth + 1)
                            candidates.append(InferenceResult(
                                answer=entity, confidence=conf, level=2,
                                reasoning=f"{depth+1}-hop reverse path",
                                path=path, verified=False,
                            ))

                    queue.append((nb, depth + 1))

        if candidates:
            return max(candidates, key=lambda r: r.confidence)
        return None

    def _level3_homology(self, subject: str, relation: str, obj: str) -> InferenceResult | None:
        """Level 3: Structural similarity matching."""
        subj_idx = self._entity_index.get(subject)
        if subj_idx is None or subj_idx not in self._G:
            return None

        # Compute "topological signature" of subject
        # = sorted degrees of k-hop neighborhood
        subj_sig = self._compute_signature(subj_idx)
        if not subj_sig:
            return None

        # Find entities with similar signatures
        best_match = None
        best_similarity = 0.0

        for entity, idx in self._entity_index.items():
            if entity == subject or idx not in self._G:
                continue
            sig = self._compute_signature(idx)
            if not sig:
                continue
            sim = self._signature_similarity(subj_sig, sig)
            if sim > best_similarity and sim > 0.5:
                # Check if this entity has a known answer for the relation
                for h, r, t in self._triples:
                    if h == entity and r == relation:
                        best_similarity = sim
                        best_match = InferenceResult(
                            answer=t, confidence=sim * 0.7, level=3,
                            reasoning=f"structural match: {subject}~{entity} (sim={sim:.2f}), "
                                      f"so {subject} {relation} {t} (by analogy from {entity})",
                            path=[subject, f"~{entity}", t], verified=False,
                        )

        return best_match

    def _level4_emergent(self, subject: str, relation: str, obj: str) -> InferenceResult | None:
        """Level 4: Cross-domain structural transfer."""
        subj_idx = self._entity_index.get(subject)
        if subj_idx is None or subj_idx not in self._G:
            return None

        # Get subject's local neighborhood structure
        subj_neighbors = list(self._G.neighbors(subj_idx))
        if len(subj_neighbors) < 2:
            return None

        # Find structurally isomorphic neighborhoods in different domains
        subj_domain = self._get_domain(subject)
        subj_subgraph = self._G.subgraph([subj_idx] + subj_neighbors)

        for entity, idx in self._entity_index.items():
            if entity == subject or idx not in self._G:
                continue
            other_domain = self._get_domain(entity)
            if other_domain == subj_domain:
                continue  # skip same domain

            other_neighbors = list(self._G.neighbors(idx))
            if abs(len(other_neighbors) - len(subj_neighbors)) > 2:
                continue

            # Compare local topology
            other_subgraph = self._G.subgraph([idx] + other_neighbors)
            if abs(len(subj_subgraph.edges) - len(other_subgraph.edges)) <= 2:
                # Similar local structure in different domain!
                for h, r, t in self._triples:
                    if h == entity and r == relation:
                        return InferenceResult(
                            answer=t, confidence=0.5, level=4,
                            reasoning=f"cross-domain transfer: {subject}({subj_domain}) ~ "
                                      f"{entity}({other_domain}), emergent: {subject} {relation} {t}",
                            path=[subject, f"~{entity}({other_domain})", t],
                            verified=False,
                        )
        return None

    def _level5_verify(self, subject: str, relation: str, answer: str) -> bool:
        """Level 5: Self-verification via structural consistency."""
        subj_idx = self._entity_index.get(subject)
        ans_idx = self._entity_index.get(answer)
        if subj_idx is None or ans_idx is None:
            return False
        if subj_idx not in self._G or ans_idx not in self._G:
            return False

        # Check 1: Are they connected?
        try:
            path_length = nx.shortest_path_length(self._G, subj_idx, ans_idx)
            if path_length > 5:
                return False  # too far apart
        except nx.NetworkXNoPath:
            return False

        # Check 2: Structural consistency
        # The answer should be in a structurally compatible region
        subj_sig = self._compute_signature(subj_idx)
        ans_sig = self._compute_signature(ans_idx)
        if subj_sig and ans_sig:
            # For IsA: answer should have >= connectivity (more general)
            if relation == "IsA":
                return self._G.degree(ans_idx) >= self._G.degree(subj_idx) * 0.5
            # For HasA: answer should be connected to subject
            elif relation == "HasA":
                return path_length <= 2

        return True  # default: accept

    def _compute_signature(self, node_idx: int, k: int = 2) -> list[int]:
        """Compute topological signature: sorted degrees of k-hop neighborhood."""
        if node_idx not in self._G:
            return []
        neighbors: set[int] = set()
        current = {node_idx}
        for _ in range(k):
            next_level: set[int] = set()
            for n in current:
                for nb in self._G.neighbors(n):
                    if nb not in neighbors and nb != node_idx:
                        next_level.add(nb)
                        neighbors.add(nb)
            current = next_level
        degrees = sorted([self._G.degree(n) for n in neighbors], reverse=True)
        return degrees[:10]  # top 10

    def _signature_similarity(self, sig1: list[int], sig2: list[int]) -> float:
        """Compare two signatures."""
        if not sig1 or not sig2:
            return 0.0
        # Pad to same length
        max_len = max(len(sig1), len(sig2))
        s1 = sig1 + [0] * (max_len - len(sig1))
        s2 = sig2 + [0] * (max_len - len(sig2))
        # Cosine similarity
        a, b = np.array(s1, dtype=float), np.array(s2, dtype=float)
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    def _get_domain(self, entity: str) -> str:
        """Guess domain of an entity from its triples."""
        domains = {
            "animal": "biology", "mammal": "biology", "cat": "biology", "dog": "biology",
            "vehicle": "transport", "car": "transport", "truck": "transport",
            "force": "physics", "gravity": "physics", "mass": "physics", "energy": "physics",
            "price": "economics", "supply": "economics", "demand": "economics", "market": "economics",
            "atom": "chemistry", "electron": "chemistry", "molecule": "chemistry",
            "cell": "biology", "dna": "biology", "gene": "biology",
        }
        return domains.get(entity, "general")
