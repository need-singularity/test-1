# tecs/engine/evolution_engine.py
from __future__ import annotations

import math

from tecs.config import SearchConfig
from tecs.types import Candidate
from tecs.engine.architecture_generator import ArchitectureGenerator


class EvolutionEngine:
    def __init__(self, config: SearchConfig, seed: int = 42):
        self._cfg = config
        self._generator = ArchitectureGenerator(seed)

    def tournament_select(self, population: list[Candidate], tournament_size: int = 3) -> Candidate:
        """Pick tournament_size random candidates; return the one with highest fitness."""
        contestants = self._generator._rng.sample(population, min(tournament_size, len(population)))
        return max(contestants, key=lambda c: c.fitness)

    def get_elites(self, population: list[Candidate], ratio: float = 0.2) -> list[Candidate]:
        """Return the top ratio fraction of the population by fitness (at least 1)."""
        n = max(1, math.floor(len(population) * ratio))
        return sorted(population, key=lambda c: c.fitness, reverse=True)[:n]

    def targeted_mutate(self, parent: Candidate, causal_info: dict | None) -> Candidate:
        """Mutate using causal info if available.

        If causal_info contains 'weakest_layer', mutate that layer; otherwise random mutation.
        """
        target_layer: str | None = None
        if causal_info and "weakest_layer" in causal_info:
            target_layer = causal_info["weakest_layer"]
        return self._generator.mutate(parent, target_layer=target_layer)

    def next_generation(
        self,
        population: list[Candidate],
        causal_info: dict | None = None,
    ) -> list[Candidate]:
        """Produce next generation of the same size.

        Strategy:
        - Preserve elites (elite_ratio of population).
        - Fill remaining slots with crossover children and targeted mutations, chosen
          based on crossover_rate / mutation_rate probabilities.
        - Apply diversity enforcement.
        - Increment generation for all children by 1 relative to parent generation.
        """
        if not population:
            return []

        target_size = len(population)
        base_generation = population[0].generation
        next_gen = base_generation + 1

        # Elites carry over
        elites = self.get_elites(population, ratio=self._cfg.elite_ratio)
        # Bump their generation
        promoted_elites: list[Candidate] = []
        for e in elites:
            import copy, uuid as _uuid
            promoted = copy.copy(e)
            object.__setattr__(promoted, "generation", next_gen) if hasattr(type(promoted), "__dataclass_fields__") else None
            # Dataclass is not frozen, so direct assignment works
            promoted.generation = next_gen
            promoted.id = str(_uuid.uuid4())
            promoted.parent_ids = [e.id]
            promoted_elites.append(promoted)

        # Fill the rest
        children: list[Candidate] = list(promoted_elites)
        total_rate = self._cfg.crossover_rate + self._cfg.mutation_rate
        crossover_prob = self._cfg.crossover_rate / total_rate if total_rate > 0 else 0.7

        while len(children) < target_size:
            if self._generator._rng.random() < crossover_prob:
                p1 = self.tournament_select(population, self._cfg.tournament_size)
                p2 = self.tournament_select(population, self._cfg.tournament_size)
                child = self._generator.crossover(p1, p2)
            else:
                parent = self.tournament_select(population, self._cfg.tournament_size)
                child = self.targeted_mutate(parent, causal_info)
            child.generation = next_gen
            children.append(child)

        # Enforce diversity
        children = self._generator.enforce_diversity(children, self._cfg.diversity_threshold)

        # Trim or pad to target_size
        while len(children) < target_size:
            from tecs.types import Candidate as _Candidate
            ref = population[0]
            immigrant = _Candidate.random(generation=next_gen, phase=ref.phase, rng=self._generator._rng)
            children.append(immigrant)

        return children[:target_size]
