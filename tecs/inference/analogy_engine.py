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
        # Quantum / wave mechanics
        "schrodinger", "wave function", "brownian", "diffusion",
        "partial differential", "probability amplitude", "hamiltonian",
        "eigenvalue", "wavefunction", "heat equation",
    },
    "finance": {
        "black-scholes", "option", "derivative", "portfolio", "hedging",
        "volatility", "risk", "stochastic calculus", "ito", "martingale",
        "arbitrage", "pricing", "financial engineering",
        "quantitative finance", "black scholes", "option pricing",
        "risk-neutral", "put", "call option",
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
        # Stochastic / PDE territory
        "partial differential equation", "stochastic process", "brownian motion",
        "wiener process", "markov", "probability distribution", "eigenvalue",
        "differential equation", "boundary condition", "heat equation",
        "stochastic differential", "ito calculus",
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
    # Structural signature (persistent homology)
    # ------------------------------------------------------------------

    def _get_structural_signature(self, node_idx: int) -> dict | None:
        """Get REAL topological signature using persistent homology."""
        if node_idx not in self._G:
            return None

        neighbors = list(self._G.neighbors(node_idx))
        if not neighbors:
            return None

        # Build local subgraph (ego graph, radius 2)
        local_nodes: set[int] = {node_idx}
        for n in neighbors:
            local_nodes.add(n)
            for nn in self._G.neighbors(n):
                local_nodes.add(nn)

        local_nodes_list = list(local_nodes)
        if len(local_nodes_list) < 3:
            return None

        # Build distance matrix from graph distances
        subG = self._G.subgraph(local_nodes_list)
        node_list = list(subG.nodes)
        n = len(node_list)

        dist_matrix = np.zeros((n, n))
        for i, u in enumerate(node_list):
            for j, v in enumerate(node_list):
                if i < j:
                    try:
                        path_len = nx.shortest_path_length(subG, u, v, weight=None)
                        dist_matrix[i][j] = path_len
                        dist_matrix[j][i] = path_len
                    except nx.NetworkXNoPath:
                        dist_matrix[i][j] = float('inf')
                        dist_matrix[j][i] = float('inf')

        # Replace inf with max finite distance + 1
        finite_vals = dist_matrix[dist_matrix < float('inf')]
        finite_max = float(finite_vals.max()) if finite_vals.size > 0 else 1.0
        dist_matrix[dist_matrix == float('inf')] = finite_max + 1

        # Compute persistent homology using Rips complex
        betti_numbers = [0, 0, 0]
        persistence_pairs: list[tuple[int, float, float]] = []

        try:
            import gudhi
            rips = gudhi.RipsComplex(
                distance_matrix=dist_matrix.tolist(),
                max_edge_length=finite_max + 2,
            )
            stree = rips.create_simplex_tree(max_dimension=2)
            stree.compute_persistence()

            betti_numbers = list(stree.betti_numbers())
            while len(betti_numbers) < 3:
                betti_numbers.append(0)

            for dim in range(min(3, 3)):
                for interval in stree.persistence_intervals_in_dimension(dim):
                    birth, death = interval
                    if death == float('inf'):
                        death = finite_max + 2
                    persistence_pairs.append((dim, float(birth), float(death)))
        except (ImportError, Exception):
            # Fallback: graph-based approximation of homology
            components = nx.number_connected_components(subG)
            betti_numbers[0] = components
            betti_numbers[1] = max(0, len(subG.edges) - len(subG.nodes) + components)
            # Approximate persistence pairs from degree sequence
            degrees = sorted([subG.degree(nd) for nd in subG.nodes], reverse=True)
            for i, d in enumerate(degrees[:5]):
                persistence_pairs.append((0, 0.0, float(d)))

        degree = self._G.degree(node_idx)
        clustering = nx.clustering(self._G, node_idx, weight="weight")

        return {
            "betti": betti_numbers[:3],
            "persistence_pairs": persistence_pairs,
            "degree": degree,
            "clustering": clustering,
            "n_local_nodes": len(local_nodes_list),
            "n_local_edges": len(subG.edges),
        }

    # ------------------------------------------------------------------
    # Signature comparison
    # ------------------------------------------------------------------

    def _compare_signatures(self, sig1: dict, sig2: dict) -> float:
        """Compare using persistence diagram distance + Betti number similarity."""
        scores: list[float] = []

        # 1. Betti number comparison (most important — topological invariant)
        b1 = np.array(sig1["betti"], dtype=float)
        b2 = np.array(sig2["betti"], dtype=float)
        betti_max = max(float(np.sum(b1)), float(np.sum(b2)), 1.0)
        betti_sim = 1.0 - float(np.sum(np.abs(b1 - b2))) / betti_max
        scores.append(betti_sim * 2.0)  # double weight

        # 2. Persistence diagram comparison (bottleneck-like distance)
        pairs1 = sig1["persistence_pairs"]
        pairs2 = sig2["persistence_pairs"]
        if pairs1 and pairs2:
            lifetimes1 = sorted([d - b for _, b, d in pairs1], reverse=True)
            lifetimes2 = sorted([d - b for _, b, d in pairs2], reverse=True)
            max_len = max(len(lifetimes1), len(lifetimes2))
            l1 = lifetimes1 + [0.0] * (max_len - len(lifetimes1))
            l2 = lifetimes2 + [0.0] * (max_len - len(lifetimes2))
            a = np.array(l1, dtype=float)
            b_arr = np.array(l2, dtype=float)
            na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b_arr))
            if na > 0 and nb > 0:
                persistence_sim = float(np.dot(a, b_arr) / (na * nb))
            else:
                persistence_sim = 0.0
            scores.append(persistence_sim * 1.5)  # 1.5x weight

        # 3. Degree similarity (minor)
        d1, d2 = sig1["degree"], sig2["degree"]
        scores.append(1.0 - abs(d1 - d2) / max(d1, d2, 1))

        # 4. Clustering similarity (minor)
        scores.append(1.0 - abs(sig1["clustering"] - sig2["clustering"]))

        # Weighted average
        if len(scores) == 3:  # no persistence pairs
            total_weight = 2.0 + 1.0 + 1.0
        else:
            total_weight = 2.0 + 1.5 + 1.0 + 1.0
        return float(min(1.0, sum(scores) / total_weight))

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
        parts.append(f"{src}({src_domain}) ≅ {tgt}({tgt_domain})")

        # Betti numbers
        b1 = src_sig.get("betti", [0, 0, 0])
        b2 = tgt_sig.get("betti", [0, 0, 0])
        parts.append(
            f"β₀β₁β₂: ({b1[0]},{b1[1]},{b1[2]}) vs ({b2[0]},{b2[1]},{b2[2]})"
        )

        # Persistence pairs count
        n_pairs1 = len(src_sig.get("persistence_pairs", []))
        n_pairs2 = len(tgt_sig.get("persistence_pairs", []))
        parts.append(f"persistence pairs: {n_pairs1} vs {n_pairs2}")

        # Degree
        parts.append(f"degree: {src_sig['degree']} vs {tgt_sig['degree']}")

        # Mapping
        if len(mapping) > 1:
            map_strs = [f"{s}↔{t}" for s, t in list(mapping.items())[:4]]
            parts.append(f"mapping: {', '.join(map_strs)}")

        return "; ".join(parts)
