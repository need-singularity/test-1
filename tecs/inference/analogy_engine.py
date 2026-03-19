"""Analogical reasoning — find structural isomorphisms across domains."""
from __future__ import annotations
import numpy as np
import networkx as nx
from dataclasses import dataclass
from tecs.types import TopologyState


@dataclass
class AnalogyResult:
    source_concept: str
    source_domain: str
    target_concept: str
    target_domain: str
    mapping: dict[str, str]  # source entity -> target entity
    similarity: float  # 0.0 - 1.0
    reasoning: str
    verified: bool = False

    def to_dict(self) -> dict:
        return {
            "source": f"{self.source_concept} ({self.source_domain})",
            "target": f"{self.target_concept} ({self.target_domain})",
            "mapping": self.mapping,
            "similarity": round(self.similarity, 4),
            "reasoning": self.reasoning,
            "verified": self.verified,
        }

    def __repr__(self):
        v = "+" if self.verified else "?"
        lines = [
            f"[Analogy|{v}] {self.source_concept}({self.source_domain})"
            f" ~ {self.target_concept}({self.target_domain})"
            f" -- similarity: {self.similarity:.2f}"
        ]
        lines.append("  Mapping:")
        for src, tgt in self.mapping.items():
            lines.append(f"    {src} <-> {tgt}")
        lines.append(f"  Reasoning: {self.reasoning}")
        return "\n".join(lines)


# Domain classification based on triples and known categories
DOMAIN_KEYWORDS: dict[str, set[str]] = {
    "physics": {
        "force", "mass", "energy", "gravity", "acceleration", "velocity",
        "momentum", "quantum", "wave", "particle", "field", "relativity",
        "thermodynamics", "entropy", "light", "photon", "electron", "newton",
        "einstein", "planck", "speed",
    },
    "economics": {
        "price", "supply", "demand", "market", "trade", "gdp", "inflation",
        "currency", "stock", "bond", "interest", "capital", "labor", "profit",
        "cost", "tax", "economy", "bank", "investment", "growth",
    },
    "biology": {
        "cell", "dna", "gene", "protein", "organism", "evolution", "species",
        "mutation", "enzyme", "membrane", "virus", "bacteria", "organ",
        "tissue", "genome", "replication", "mitosis", "natural selection",
        "darwin",
    },
    "chemistry": {
        "atom", "molecule", "element", "compound", "reaction", "bond", "ion",
        "acid", "base", "solution", "catalyst", "oxidation", "periodic table",
    },
    "mathematics": {
        "number", "prime", "theorem", "proof", "equation", "function", "set",
        "group", "ring", "field", "topology", "algebra", "calculus",
        "integral", "derivative", "limit", "infinity", "conjecture",
        "hypothesis", "riemann",
    },
    "computer_science": {
        "algorithm", "data", "program", "computer", "software", "hardware",
        "network", "database", "encryption", "binary", "code", "compiler",
        "memory", "processor", "internet", "protocol", "recursion",
    },
}


class AnalogyEngine:
    """Find structural isomorphisms between knowledge domains.

    Two knowledge subgraphs are "analogous" if their local topology is
    similar, even when the entities are completely different.
    """

    def __init__(self, knowledge: TopologyState):
        self._G: nx.Graph = knowledge.complex
        self._entity_index: dict[str, int] = knowledge.metadata.get(
            "entity_index", {}
        )
        self._index_to_entity: dict[int, str] = knowledge.metadata.get(
            "index_to_entity", {}
        )
        self._triples: list[tuple[str, str, str]] = knowledge.metadata.get(
            "triples", []
        )
        self._entity_domains: dict[str, str] = self._classify_domains()

    # ------------------------------------------------------------------
    # Domain classification
    # ------------------------------------------------------------------

    def _classify_domains(self) -> dict[str, str]:
        """Classify each entity into a domain."""
        domains: dict[str, str] = {}
        for entity in self._entity_index:
            entity_lower = entity.lower()
            best_domain = "general"
            best_score = 0.0
            for domain, keywords in DOMAIN_KEYWORDS.items():
                score = 0.0
                # Check entity name directly
                score += sum(1 for kw in keywords if kw in entity_lower)
                # Check connected entities (half weight)
                idx = self._entity_index.get(entity)
                if idx is not None and idx in self._G:
                    for nb in self._G.neighbors(idx):
                        nb_entity = self._index_to_entity.get(nb, "").lower()
                        score += sum(
                            0.5 for kw in keywords if kw in nb_entity
                        )
                # Check triples (lower weight)
                for h, r, t in self._triples:
                    if h == entity or t == entity:
                        other = t if h == entity else h
                        score += sum(
                            0.3 for kw in keywords if kw in other.lower()
                        )
                if score > best_score:
                    best_score = score
                    best_domain = domain
            domains[entity] = best_domain if best_score > 0 else "general"
        return domains

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def find_analogy(
        self, concept: str, target_domain: str, max_results: int = 3
    ) -> list[AnalogyResult]:
        """Find analogous concepts in *target_domain* for *concept*.

        Example::

            find_analogy("force", "economics")
            -> force(physics) ~ price(economics)
        """
        concept_lower = concept.lower()
        if concept_lower not in self._entity_index:
            return []

        source_domain = self._entity_domains.get(concept_lower, "general")

        # Source structural signature
        source_idx = self._entity_index[concept_lower]
        source_sig = self._get_structural_signature(source_idx)
        if not source_sig:
            return []

        source_neighbors = self._get_labeled_neighbors(source_idx)

        # Scan candidates in target domain
        results: list[AnalogyResult] = []
        for entity, domain in self._entity_domains.items():
            if domain != target_domain:
                continue
            if entity == concept_lower:
                continue

            target_idx = self._entity_index.get(entity)
            if target_idx is None or target_idx not in self._G:
                continue

            target_sig = self._get_structural_signature(target_idx)
            if not target_sig:
                continue

            similarity = self._compare_signatures(source_sig, target_sig)
            if similarity < 0.3:
                continue

            target_neighbors = self._get_labeled_neighbors(target_idx)
            mapping = self._build_mapping(
                concept_lower, source_neighbors, entity, target_neighbors
            )
            verified = self._verify_analogy(source_idx, target_idx, mapping)
            reasoning = self._explain_analogy(
                concept_lower, source_domain, entity, target_domain,
                source_sig, target_sig, mapping,
            )

            results.append(AnalogyResult(
                source_concept=concept_lower,
                source_domain=source_domain,
                target_concept=entity,
                target_domain=target_domain,
                mapping=mapping,
                similarity=similarity,
                reasoning=reasoning,
                verified=verified,
            ))

        results.sort(key=lambda r: r.similarity, reverse=True)
        return results[:max_results]

    def find_cross_domain_pattern(
        self, concept_a: str, concept_b: str
    ) -> list[AnalogyResult]:
        """Given two concepts, find what they have in common structurally.

        Example::

            find_cross_domain_pattern("gravity", "price")
            -> Both have similar local topology
        """
        a_lower = concept_a.lower()
        b_lower = concept_b.lower()

        if a_lower not in self._entity_index:
            return []
        if b_lower not in self._entity_index:
            return []

        a_idx = self._entity_index[a_lower]
        b_idx = self._entity_index[b_lower]

        a_sig = self._get_structural_signature(a_idx)
        b_sig = self._get_structural_signature(b_idx)
        if not a_sig or not b_sig:
            return []

        similarity = self._compare_signatures(a_sig, b_sig)

        a_neighbors = self._get_labeled_neighbors(a_idx)
        b_neighbors = self._get_labeled_neighbors(b_idx)
        mapping = self._build_mapping(
            a_lower, a_neighbors, b_lower, b_neighbors
        )

        a_domain = self._entity_domains.get(a_lower, "general")
        b_domain = self._entity_domains.get(b_lower, "general")

        reasoning = self._explain_analogy(
            a_lower, a_domain, b_lower, b_domain, a_sig, b_sig, mapping
        )
        verified = self._verify_analogy(a_idx, b_idx, mapping)

        return [AnalogyResult(
            source_concept=a_lower,
            source_domain=a_domain,
            target_concept=b_lower,
            target_domain=b_domain,
            mapping=mapping,
            similarity=similarity,
            reasoning=reasoning,
            verified=verified,
        )]

    # ------------------------------------------------------------------
    # Structural signature
    # ------------------------------------------------------------------

    def _get_structural_signature(self, node_idx: int) -> dict | None:
        """Compute the structural signature of a node's local topology."""
        if node_idx not in self._G:
            return None

        neighbors = list(self._G.neighbors(node_idx))
        if not neighbors:
            return None

        degree = self._G.degree(node_idx)
        neighbor_degrees = sorted(
            [self._G.degree(n) for n in neighbors], reverse=True
        )

        weights = [
            self._G[node_idx][n].get("weight", 0.5) for n in neighbors
        ]

        clustering = nx.clustering(self._G, node_idx, weight="weight")

        relation_counts: dict[str, int] = {}
        for n in neighbors:
            rel = self._G[node_idx][n].get("relation", "unknown")
            relation_counts[rel] = relation_counts.get(rel, 0) + 1

        # 2-hop reachability
        two_hop: set[int] = set()
        for n in neighbors:
            for nn in self._G.neighbors(n):
                if nn != node_idx and nn not in neighbors:
                    two_hop.add(nn)

        return {
            "degree": degree,
            "neighbor_degrees": neighbor_degrees[:5],
            "weight_mean": float(np.mean(weights)) if weights else 0.0,
            "weight_std": float(np.std(weights)) if weights else 0.0,
            "clustering": clustering,
            "relation_types": relation_counts,
            "n_relation_types": len(relation_counts),
            "two_hop_reach": len(two_hop),
        }

    # ------------------------------------------------------------------
    # Signature comparison
    # ------------------------------------------------------------------

    def _compare_signatures(self, sig1: dict, sig2: dict) -> float:
        """Compare two structural signatures. Returns similarity in [0, 1]."""
        scores: list[float] = []

        # Degree similarity
        d1, d2 = sig1["degree"], sig2["degree"]
        scores.append(1.0 - abs(d1 - d2) / max(d1, d2, 1))

        # Neighbor degree distribution (cosine)
        nd1 = sig1["neighbor_degrees"]
        nd2 = sig2["neighbor_degrees"]
        max_len = max(len(nd1), len(nd2), 1)
        nd1_padded = nd1 + [0] * (max_len - len(nd1))
        nd2_padded = nd2 + [0] * (max_len - len(nd2))
        a = np.array(nd1_padded, dtype=float)
        b = np.array(nd2_padded, dtype=float)
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na > 0 and nb > 0:
            scores.append(float(np.dot(a, b) / (na * nb)))
        else:
            scores.append(0.0)

        # Weight distribution similarity
        scores.append(
            1.0 - min(1.0, abs(sig1["weight_mean"] - sig2["weight_mean"]))
        )

        # Clustering similarity
        scores.append(1.0 - abs(sig1["clustering"] - sig2["clustering"]))

        # Relation type diversity similarity
        scores.append(
            1.0
            - abs(sig1["n_relation_types"] - sig2["n_relation_types"])
            / max(sig1["n_relation_types"], sig2["n_relation_types"], 1)
        )

        # 2-hop reach similarity
        r1, r2 = sig1["two_hop_reach"], sig2["two_hop_reach"]
        scores.append(1.0 - abs(r1 - r2) / max(r1, r2, 1))

        return float(np.mean(scores))

    # ------------------------------------------------------------------
    # Neighbor helpers
    # ------------------------------------------------------------------

    def _get_labeled_neighbors(self, node_idx: int) -> list[dict]:
        """Get neighbors with labels and edge metadata, sorted by weight."""
        neighbors: list[dict] = []
        for nb in self._G.neighbors(node_idx):
            entity = self._index_to_entity.get(nb, str(nb))
            edge = self._G[node_idx][nb]
            neighbors.append({
                "idx": nb,
                "entity": entity,
                "weight": edge.get("weight", 0.5),
                "relation": edge.get("relation", "unknown"),
                "degree": self._G.degree(nb),
            })
        neighbors.sort(key=lambda n: n["weight"], reverse=True)
        return neighbors

    # ------------------------------------------------------------------
    # Mapping construction
    # ------------------------------------------------------------------

    def _build_mapping(
        self,
        src_name: str,
        src_neighbors: list[dict],
        tgt_name: str,
        tgt_neighbors: list[dict],
    ) -> dict[str, str]:
        """Build entity-to-entity mapping based on structural role similarity."""
        mapping: dict[str, str] = {src_name: tgt_name}

        used_targets: set[str] = set()
        for sn in src_neighbors:
            best_match = None
            best_score = -1.0
            for tn in tgt_neighbors:
                if tn["entity"] in used_targets:
                    continue
                score = 0.0
                if sn["relation"] == tn["relation"]:
                    score += 0.5
                degree_sim = 1.0 - abs(sn["degree"] - tn["degree"]) / max(
                    sn["degree"], tn["degree"], 1
                )
                score += 0.3 * degree_sim
                weight_sim = 1.0 - abs(sn["weight"] - tn["weight"])
                score += 0.2 * weight_sim
                if score > best_score:
                    best_score = score
                    best_match = tn
            if best_match is not None and best_score > 0.3:
                mapping[sn["entity"]] = best_match["entity"]
                used_targets.add(best_match["entity"])

        return mapping

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def _verify_analogy(
        self, src_idx: int, tgt_idx: int, mapping: dict[str, str]
    ) -> bool:
        """Verify structural consistency of the analogy.

        If A--B in source subgraph, then mapping(A)--mapping(B) should hold
        in the target subgraph.
        """
        consistent = 0
        total = 0
        for src_entity, tgt_entity in mapping.items():
            src_i = self._entity_index.get(src_entity)
            tgt_i = self._entity_index.get(tgt_entity)
            if src_i is None or tgt_i is None:
                continue
            for src_nb_entity, tgt_nb_entity in mapping.items():
                if src_nb_entity == src_entity:
                    continue
                src_nb_i = self._entity_index.get(src_nb_entity)
                tgt_nb_i = self._entity_index.get(tgt_nb_entity)
                if src_nb_i is None or tgt_nb_i is None:
                    continue
                total += 1
                src_connected = self._G.has_edge(src_i, src_nb_i)
                tgt_connected = self._G.has_edge(tgt_i, tgt_nb_i)
                if src_connected == tgt_connected:
                    consistent += 1

        if total == 0:
            return False
        return (consistent / total) >= 0.5

    # ------------------------------------------------------------------
    # Explanation
    # ------------------------------------------------------------------

    def _explain_analogy(
        self,
        src: str,
        src_domain: str,
        tgt: str,
        tgt_domain: str,
        src_sig: dict,
        tgt_sig: dict,
        mapping: dict[str, str],
    ) -> str:
        """Generate a human-readable explanation of the analogy."""
        parts: list[str] = []
        parts.append(
            f"{src}({src_domain}) and {tgt}({tgt_domain}) share similar topology"
        )
        parts.append(f"degree: {src_sig['degree']} vs {tgt_sig['degree']}")
        parts.append(
            f"clustering: {src_sig['clustering']:.2f} vs"
            f" {tgt_sig['clustering']:.2f}"
        )
        if len(mapping) > 1:
            map_strs = [
                f"{s}<->{t}" for s, t in list(mapping.items())[:4]
            ]
            parts.append(f"mapping: {', '.join(map_strs)}")
        return "; ".join(parts)
