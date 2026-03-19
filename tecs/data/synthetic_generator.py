# tecs/data/synthetic_generator.py
"""Generates test data without external dependencies."""
from __future__ import annotations

import random
import numpy as np

RELATIONS = ["IsA", "HasA", "PartOf", "UsedFor", "CapableOf"]
INVERSE_RELATIONS = {
    "IsA": "NotIsA",
    "HasA": "LacksA",
    "PartOf": "NotPartOf",
    "UsedFor": "NotUsedFor",
    "CapableOf": "IncapableOf",
}

CATEGORIES = {
    "animals": ["dog", "cat", "bird", "fish", "horse", "lion", "tiger", "elephant"],
    "vehicles": ["car", "truck", "bus", "bike", "train", "plane", "boat", "ship"],
    "food": ["apple", "bread", "rice", "soup", "salad", "steak", "cake", "milk"],
    "tools": ["hammer", "saw", "drill", "wrench", "screwdriver", "knife", "chisel", "axe"],
    "places": ["city", "town", "village", "country", "forest", "desert", "ocean", "mountain"],
}


class SyntheticGenerator:
    """Generates synthetic concept data for testing without external dependencies."""

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)
        self._np_rng = np.random.default_rng(seed)

    def get_points(self, n: int, dim: int = 3) -> np.ndarray:
        """Generate n random points in dim-dimensional space."""
        return self._np_rng.standard_normal((n, dim))

    def get_concept_relations(self, n: int = 100) -> list[dict]:
        """
        Generate random (head, relation, tail) triples.
        Returns list of {"head": str, "relation": str, "tail": str}.
        """
        all_entities: list[str] = []
        for items in CATEGORIES.values():
            all_entities.extend(items)

        results = []
        for _ in range(n):
            head = self._rng.choice(all_entities)
            tail = self._rng.choice(all_entities)
            relation = self._rng.choice(RELATIONS)
            results.append({"head": head, "relation": relation, "tail": tail})
        return results

    def get_contradictions(self, n: int = 50) -> list[dict]:
        """
        Generate contradiction pairs.
        Each pair: {"positive": triple_dict, "negative": triple_dict}
        The negative inverts the relation of the positive triple.
        """
        positives = self.get_concept_relations(n)
        results = []
        for pos in positives:
            neg_relation = INVERSE_RELATIONS.get(pos["relation"], "Not" + pos["relation"])
            neg = {"head": pos["head"], "relation": neg_relation, "tail": pos["tail"]}
            results.append({"positive": pos, "negative": neg})
        return results

    def get_analogies(self, n: int = 50) -> list[dict]:
        """
        Generate structural analogy quads: A:B::C:D.
        Returns list of {"a": str, "b": str, "c": str, "d": str, "relation": str}.
        Items within a category share the same relation, yielding valid structural pairs.
        """
        category_names = list(CATEGORIES.keys())
        results = []
        for _ in range(n):
            # Pick two different categories for cross-category analogy
            cat_a, cat_c = self._rng.sample(category_names, 2)
            items_a = CATEGORIES[cat_a]
            items_c = CATEGORIES[cat_c]
            # Pick pairs within each category sharing the same structural relation
            a, b = self._rng.sample(items_a, 2) if len(items_a) >= 2 else (items_a[0], items_a[0])
            c, d = self._rng.sample(items_c, 2) if len(items_c) >= 2 else (items_c[0], items_c[0])
            relation = self._rng.choice(RELATIONS)
            results.append({"a": a, "b": b, "c": c, "d": d, "relation": relation})
        return results
