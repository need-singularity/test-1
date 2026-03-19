# tests/test_engine/test_evolution_engine.py
from __future__ import annotations

import random
import uuid

import pytest

from tecs.config import SearchConfig
from tecs.engine.evolution_engine import EvolutionEngine
from tecs.types import Candidate, LAYERS, COMPONENT_POOL

# Shared config for tests
cfg = SearchConfig(
    population_size=10,
    elite_ratio=0.2,
    tournament_size=3,
    mutation_rate=0.3,
    crossover_rate=0.7,
    diversity_threshold=0.3,
    seed=42,
)


def make_candidate(fitness: float, generation: int = 0, phase: int = 1) -> Candidate:
    """Create a Candidate with given fitness and random components."""
    rng = random.Random()
    components = {layer: rng.choice(options) for layer, options in COMPONENT_POOL.items()}
    return Candidate(
        id=str(uuid.uuid4()),
        components=components,
        parent_ids=[],
        generation=generation,
        phase=phase,
        fitness=fitness,
    )


# ---------------------------------------------------------------------------
# tournament_select
# ---------------------------------------------------------------------------

def test_tournament_selection():
    engine = EvolutionEngine(cfg)
    pop = [make_candidate(fitness=f) for f in [0.1, 0.5, 0.9, 0.3]]
    selected = engine.tournament_select(pop, tournament_size=3)
    assert selected.fitness >= 0.1  # should tend to pick good ones


def test_tournament_selection_returns_best_of_contestants():
    """With full population as tournament, always returns highest-fitness candidate."""
    engine = EvolutionEngine(cfg, seed=0)
    pop = [make_candidate(fitness=f) for f in [0.1, 0.2, 0.99, 0.5, 0.3]]
    # Run many times; the best (0.99) should appear frequently
    winners = [engine.tournament_select(pop, tournament_size=len(pop)) for _ in range(20)]
    assert any(w.fitness == 0.99 for w in winners)


def test_tournament_selection_single_candidate():
    engine = EvolutionEngine(cfg)
    pop = [make_candidate(fitness=0.5)]
    selected = engine.tournament_select(pop, tournament_size=3)
    assert selected.fitness == 0.5


# ---------------------------------------------------------------------------
# get_elites
# ---------------------------------------------------------------------------

def test_elite_preservation():
    engine = EvolutionEngine(cfg)
    pop = [make_candidate(fitness=f) for f in [0.1, 0.5, 0.9, 0.3, 0.7]]
    elites = engine.get_elites(pop, ratio=0.2)
    assert len(elites) == 1
    assert elites[0].fitness == 0.9


def test_elite_preservation_multiple():
    engine = EvolutionEngine(cfg)
    pop = [make_candidate(fitness=f) for f in [0.1, 0.5, 0.9, 0.3, 0.7, 0.8, 0.2, 0.4, 0.6, 0.95]]
    elites = engine.get_elites(pop, ratio=0.2)
    assert len(elites) == 2
    fitnesses = sorted([e.fitness for e in elites], reverse=True)
    assert fitnesses[0] == 0.95
    assert fitnesses[1] == 0.9


def test_elite_at_least_one():
    """Even with tiny ratio, at least 1 elite is returned."""
    engine = EvolutionEngine(cfg)
    pop = [make_candidate(fitness=f) for f in [0.1, 0.2, 0.3]]
    elites = engine.get_elites(pop, ratio=0.01)
    assert len(elites) >= 1


# ---------------------------------------------------------------------------
# targeted_mutate
# ---------------------------------------------------------------------------

def test_targeted_mutation_uses_causal_info():
    engine = EvolutionEngine(cfg)
    causal_info = {"weakest_layer": "verification"}
    parent = Candidate.random(generation=0, phase=1)
    child = engine.targeted_mutate(parent, causal_info)
    assert child.mutation_layer == "verification"


def test_targeted_mutation_without_causal_info():
    engine = EvolutionEngine(cfg)
    parent = Candidate.random(generation=0, phase=1)
    child = engine.targeted_mutate(parent, causal_info=None)
    assert child.mutation_layer in LAYERS
    assert child.parent_ids == [parent.id]


def test_targeted_mutation_empty_causal_info():
    engine = EvolutionEngine(cfg)
    parent = Candidate.random(generation=0, phase=1)
    child = engine.targeted_mutate(parent, causal_info={})
    # No weakest_layer key → random mutation
    assert child.mutation_layer in LAYERS


def test_targeted_mutation_all_layers():
    engine = EvolutionEngine(cfg)
    for layer in LAYERS:
        parent = Candidate.random(generation=0, phase=1)
        child = engine.targeted_mutate(parent, causal_info={"weakest_layer": layer})
        assert child.mutation_layer == layer


# ---------------------------------------------------------------------------
# next_generation
# ---------------------------------------------------------------------------

def test_next_generation():
    engine = EvolutionEngine(cfg)
    rng = random.Random(0)
    pop = [make_candidate(fitness=rng.random()) for _ in range(10)]
    next_pop = engine.next_generation(pop, causal_info=None)
    assert len(next_pop) == len(pop)
    assert all(c.generation == pop[0].generation + 1 for c in next_pop)


def test_next_generation_preserves_size():
    engine = EvolutionEngine(cfg)
    for size in [5, 10, 20]:
        pop = [make_candidate(fitness=random.random()) for _ in range(size)]
        next_pop = engine.next_generation(pop)
        assert len(next_pop) == size


def test_next_generation_increments_generation():
    engine = EvolutionEngine(cfg)
    generation = 5
    pop = [make_candidate(fitness=random.random(), generation=generation) for _ in range(10)]
    next_pop = engine.next_generation(pop)
    assert all(c.generation == generation + 1 for c in next_pop)


def test_next_generation_empty_population():
    engine = EvolutionEngine(cfg)
    result = engine.next_generation([])
    assert result == []


def test_next_generation_with_causal_info():
    engine = EvolutionEngine(cfg)
    pop = [make_candidate(fitness=random.random()) for _ in range(10)]
    causal_info = {"weakest_layer": "reasoning"}
    next_pop = engine.next_generation(pop, causal_info=causal_info)
    assert len(next_pop) == len(pop)
    assert all(c.generation == pop[0].generation + 1 for c in next_pop)
