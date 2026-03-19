# tecs/engine/architecture_generator.py
from __future__ import annotations

import random
import uuid

from tecs.types import Candidate, LAYERS, COMPONENT_POOL


class ArchitectureGenerator:
    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)

    def random_population(self, n: int, generation: int, phase: int) -> list[Candidate]:
        """Generate n random candidates."""
        return [Candidate.random(generation=generation, phase=phase, rng=self._rng) for _ in range(n)]

    def mutate(self, parent: Candidate, target_layer: str | None = None) -> Candidate:
        """Create child by mutating one layer.

        If target_layer is given, mutate that layer; otherwise pick a random layer.
        Child has parent_ids = [parent.id] and mutation_layer set to the mutated layer.
        The new component is guaranteed to differ from the parent's component for that layer.
        """
        layer = target_layer if target_layer is not None else self._rng.choice(LAYERS)

        current = parent.components[layer]
        options = [c for c in COMPONENT_POOL[layer] if c != current]
        # If all options are exhausted (shouldn't happen with 3-option pools), fall back to any
        if not options:
            options = COMPONENT_POOL[layer]
        new_component = self._rng.choice(options)

        new_components = dict(parent.components)
        new_components[layer] = new_component

        return Candidate(
            id=str(uuid.uuid4()),
            components=new_components,
            parent_ids=[parent.id],
            generation=parent.generation,
            phase=parent.phase,
            fitness=0.0,
            mutation_layer=layer,
        )

    def crossover(self, p1: Candidate, p2: Candidate) -> Candidate:
        """Uniform crossover between two parents.

        For each layer, independently pick the component from p1 or p2 with equal probability.
        Child has parent_ids = [p1.id, p2.id].
        """
        new_components = {
            layer: self._rng.choice([p1.components[layer], p2.components[layer]])
            for layer in LAYERS
        }

        return Candidate(
            id=str(uuid.uuid4()),
            components=new_components,
            parent_ids=[p1.id, p2.id],
            generation=p1.generation,
            phase=p1.phase,
            fitness=0.0,
            mutation_layer=None,
        )

    def enforce_diversity(self, population: list[Candidate], threshold: float) -> list[Candidate]:
        """Remove exact duplicates (hamming_distance == 0).

        If the resulting population is too homogeneous (average pairwise hamming distance
        below threshold * len(LAYERS)), inject random immigrants to replace removed duplicates.
        """
        # Remove exact duplicates, keeping first occurrence
        seen_components: list[dict[str, str]] = []
        unique: list[Candidate] = []
        for candidate in population:
            if candidate.components not in seen_components:
                seen_components.append(candidate.components)
                unique.append(candidate)

        # Determine how many immigrants are needed
        n_immigrants = len(population) - len(unique)

        if unique:
            # Check average pairwise hamming distance for homogeneity
            pairs = 0
            total_dist = 0
            for i, a in enumerate(unique):
                for b in unique[i + 1:]:
                    total_dist += a.hamming_distance(b)
                    pairs += 1
            avg_dist = total_dist / pairs if pairs > 0 else 0
            # If too homogeneous, inject additional immigrants
            if avg_dist < threshold * len(LAYERS):
                n_immigrants = max(n_immigrants, max(1, len(population) // 4))

        # Generate immigrants using the reference generation/phase from the first candidate
        immigrants: list[Candidate] = []
        if n_immigrants > 0 and population:
            ref = population[0]
            for _ in range(n_immigrants):
                immigrants.append(Candidate.random(generation=ref.generation, phase=ref.phase, rng=self._rng))

        return unique + immigrants
