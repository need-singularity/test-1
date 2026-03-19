"""Encode real-world knowledge into topological structures."""
from __future__ import annotations
import numpy as np
from tecs.types import TopologyState


class KnowledgeEncoder:
    def __init__(self):
        self._word_vectors: dict[str, np.ndarray] = {}
        self._triples: list[tuple[str, str, str]] = []
        self._entity_index: dict[str, int] = {}

    def load_glove(self, path: str, max_words: int = 50000):
        """Load GloVe vectors from text file."""
        # If file not found, generate synthetic embeddings for testing
        # Real: parse glove.6B.300d.txt line by line
        # Each line: word 0.123 -0.456 ...
        try:
            with open(path) as f:
                for i, line in enumerate(f):
                    if i >= max_words:
                        break
                    parts = line.strip().split()
                    word = parts[0]
                    vec = np.array([float(x) for x in parts[1:]], dtype=np.float32)
                    self._word_vectors[word] = vec
        except FileNotFoundError:
            # Synthetic fallback for testing
            import random
            rng = random.Random(42)
            dim = 50  # smaller for synthetic
            # Create semantic clusters
            clusters = {
                "animals": ["cat", "dog", "animal", "mammal", "fish", "bird"],
                "vehicles": ["car", "truck", "vehicle", "bus", "bicycle"],
                "colors": ["red", "blue", "green", "color", "bright"],
                "actions": ["run", "walk", "move", "jump", "swim"],
                "sizes": ["big", "small", "tall", "short", "heavy"],
                "elements": ["water", "fire", "earth", "air", "wind"],
                "royalty": ["king", "queen", "man", "woman", "child"],
                "professions": ["doctor", "teacher", "student", "engineer", "scientist"],
                "physics": ["gravity", "force", "mass", "energy", "speed"],
                "economics": ["price", "supply", "demand", "market", "trade"],
                "particles": ["atom", "electron", "proton", "neutron", "molecule"],
                "biology": ["cell", "dna", "protein", "gene", "virus"],
            }
            for cluster_name, words in clusters.items():
                center = np.array([rng.gauss(0, 1) for _ in range(dim)], dtype=np.float32)
                for word in words:
                    noise = np.array([rng.gauss(0, 0.3) for _ in range(dim)], dtype=np.float32)
                    self._word_vectors[word] = center + noise

    def load_conceptnet_triples(self, path: str = None, max_triples: int = 10000):
        """Load ConceptNet triples or generate synthetic ones."""
        if path:
            try:
                with open(path) as f:
                    for i, line in enumerate(f):
                        if i >= max_triples:
                            break
                        parts = line.strip().split('\t')
                        if len(parts) >= 3:
                            self._triples.append((parts[0], parts[1], parts[2]))
                return
            except FileNotFoundError:
                pass

        # Synthetic triples for testing
        synthetic = [
            ("cat", "IsA", "mammal"), ("cat", "IsA", "animal"), ("cat", "HasA", "fur"),
            ("dog", "IsA", "mammal"), ("dog", "IsA", "animal"), ("dog", "HasA", "tail"),
            ("mammal", "IsA", "animal"), ("fish", "IsA", "animal"), ("bird", "IsA", "animal"),
            ("car", "IsA", "vehicle"), ("truck", "IsA", "vehicle"), ("bus", "IsA", "vehicle"),
            ("vehicle", "HasA", "wheels"), ("car", "HasA", "engine"),
            ("red", "IsA", "color"), ("blue", "IsA", "color"), ("green", "IsA", "color"),
            ("gravity", "IsA", "force"), ("mass", "RelatedTo", "gravity"),
            ("energy", "RelatedTo", "mass"), ("force", "RelatedTo", "mass"),
            ("price", "RelatedTo", "supply"), ("price", "RelatedTo", "demand"),
            ("supply", "RelatedTo", "market"), ("demand", "RelatedTo", "market"),
            ("atom", "HasA", "electron"), ("atom", "HasA", "proton"), ("atom", "HasA", "neutron"),
            ("molecule", "MadeOf", "atom"), ("cell", "HasA", "dna"),
            ("dna", "HasA", "gene"), ("protein", "MadeOf", "gene"),
            ("king", "IsA", "man"), ("queen", "IsA", "woman"),
            ("doctor", "IsA", "profession"), ("teacher", "IsA", "profession"),
        ]
        self._triples = synthetic

    def load_wordnet(self):
        """Load WordNet hierarchy."""
        try:
            from nltk.corpus import wordnet as wn
            for synset in list(wn.all_synsets())[:5000]:
                word = synset.lemmas()[0].name()
                for hyper in synset.hypernyms():
                    parent = hyper.lemmas()[0].name()
                    self._triples.append((word, "IsA", parent))
        except Exception:
            pass  # WordNet not available, use synthetic only

    def build_complex(self) -> TopologyState:
        """Build topological knowledge complex from loaded data."""
        import networkx as nx

        # Build entity index
        all_entities: set[str] = set()
        for w in self._word_vectors:
            all_entities.add(w)
        for h, r, t in self._triples:
            all_entities.add(h)
            all_entities.add(t)

        entities = sorted(all_entities)
        self._entity_index = {e: i for i, e in enumerate(entities)}
        n = len(entities)

        # Build graph
        G = nx.Graph()
        for i, e in enumerate(entities):
            G.add_node(i, label=e)

        # Add edges from word vector similarity
        if self._word_vectors:
            vec_entities = [e for e in entities if e in self._word_vectors]
            if vec_entities:
                vecs = np.array([self._word_vectors[e] for e in vec_entities])
                # Cosine similarity
                norms = np.linalg.norm(vecs, axis=1, keepdims=True)
                norms = np.where(norms == 0, 1, norms)
                normalized = vecs / norms
                sim_matrix = normalized @ normalized.T

                for i, ei in enumerate(vec_entities):
                    for j, ej in enumerate(vec_entities):
                        if i < j and sim_matrix[i, j] > 0.5:  # threshold
                            idx_i = self._entity_index[ei]
                            idx_j = self._entity_index[ej]
                            G.add_edge(idx_i, idx_j, weight=float(sim_matrix[i, j]),
                                       relation="similar")

        # Add edges from triples
        relation_weights = {"IsA": 0.9, "HasA": 0.7, "PartOf": 0.8,
                            "RelatedTo": 0.5, "MadeOf": 0.7, "MemberOf": 0.8}
        for h, r, t in self._triples:
            if h in self._entity_index and t in self._entity_index:
                idx_h = self._entity_index[h]
                idx_t = self._entity_index[t]
                w = relation_weights.get(r, 0.5)
                if G.has_edge(idx_h, idx_t):
                    # Strengthen existing edge
                    G[idx_h][idx_t]["weight"] = max(G[idx_h][idx_t]["weight"], w)
                else:
                    G.add_edge(idx_h, idx_t, weight=w, relation=r)

        # Compute curvature
        curvature = np.zeros(n)
        for i in range(n):
            if G.degree(i) > 0:
                neighbor_weights = [G[i][nb].get("weight", 0.5) for nb in G.neighbors(i)]
                curvature[i] = np.mean(neighbor_weights)

        return TopologyState(
            complex=G,
            complex_type="graph",
            curvature=curvature,
            metrics={},
            history=[{"action": "knowledge_encoding", "n_entities": n,
                      "n_edges": len(G.edges), "n_triples": len(self._triples),
                      "n_vectors": len(self._word_vectors)}],
            metadata={"entity_index": self._entity_index,
                      "index_to_entity": {i: e for e, i in self._entity_index.items()},
                      "triples": self._triples},
        )

    def load_wikipedia(self, topics: list[str], depth: int = 1, max_related: int = 10):
        """Load knowledge from Wikipedia for given topics."""
        from tecs.inference.wikipedia_loader import WikipediaLoader
        loader = WikipediaLoader()
        for topic in topics:
            print(f"  Loading Wikipedia: {topic}...")
            loader.load_topic(topic, depth=depth, max_related=max_related)

        new_triples = loader.extract_triples()
        self._triples.extend(new_triples)
        print(f"  Wikipedia: {len(loader.articles)} articles, {len(new_triples)} triples extracted")

    @property
    def entity_index(self) -> dict[str, int]:
        return self._entity_index
