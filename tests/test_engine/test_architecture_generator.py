# tests/test_engine/test_architecture_generator.py
from __future__ import annotations

import pytest

from tecs.engine.architecture_generator import ArchitectureGenerator
from tecs.types import Candidate, LAYERS


def test_random_population():
    gen = ArchitectureGenerator(seed=42)
    pop = gen.random_population(n=10, generation=0, phase=1)
    assert len(pop) == 10
    assert all(len(c.components) == 5 for c in pop)


def test_random_population_correct_layers():
    gen = ArchitectureGenerator(seed=42)
    pop = gen.random_population(n=5, generation=2, phase=3)
    for c in pop:
        assert set(c.components.keys()) == set(LAYERS)
        assert c.generation == 2
        assert c.phase == 3


def test_mutate_records_layer():
    gen = ArchitectureGenerator(seed=42)
    parent = Candidate.random(generation=0, phase=1)
    child = gen.mutate(parent, target_layer="reasoning")
    assert child.mutation_layer == "reasoning"
    assert child.parent_ids == [parent.id]
    assert child.components["reasoning"] != parent.components["reasoning"]


def test_mutate_random_layer():
    gen = ArchitectureGenerator(seed=42)
    parent = Candidate.random(generation=0, phase=1)
    child = gen.mutate(parent)
    assert child.mutation_layer in LAYERS
    assert child.parent_ids == [parent.id]
    # Exactly one layer should differ
    diffs = [l for l in LAYERS if child.components[l] != parent.components[l]]
    assert len(diffs) == 1
    assert diffs[0] == child.mutation_layer


def test_mutate_all_layers():
    """Verify mutate works for each individual layer."""
    gen = ArchitectureGenerator(seed=99)
    for layer in LAYERS:
        parent = Candidate.random(generation=0, phase=1)
        child = gen.mutate(parent, target_layer=layer)
        assert child.mutation_layer == layer
        assert child.components[layer] != parent.components[layer]


def test_crossover_records_parents():
    gen = ArchitectureGenerator(seed=42)
    p1 = Candidate.random(generation=0, phase=1)
    p2 = Candidate.random(generation=0, phase=1)
    child = gen.crossover(p1, p2)
    assert set(child.parent_ids) == {p1.id, p2.id}


def test_crossover_inherits_components():
    gen = ArchitectureGenerator(seed=42)
    p1 = Candidate.random(generation=0, phase=1)
    p2 = Candidate.random(generation=0, phase=1)
    child = gen.crossover(p1, p2)
    for layer in LAYERS:
        assert child.components[layer] in {p1.components[layer], p2.components[layer]}


def test_diversity_filter_removes_duplicates():
    gen = ArchitectureGenerator(seed=42)
    pop = [Candidate.random(generation=0, phase=1) for _ in range(10)]
    filtered = gen.enforce_diversity(pop, threshold=0.3)
    # No two candidates should be identical (hamming_distance == 0)
    for i, a in enumerate(filtered):
        for b in filtered[i + 1:]:
            assert a.hamming_distance(b) > 0


def test_diversity_filter_exact_duplicates():
    """If we inject exact copies, they should be removed."""
    gen = ArchitectureGenerator(seed=42)
    original = Candidate.random(generation=0, phase=1)
    # Create population where the same candidate appears multiple times
    import copy, uuid
    pop = []
    for _ in range(5):
        dup = copy.deepcopy(original)
        dup.id = str(uuid.uuid4())
        pop.append(dup)
    # Add a different one
    other = Candidate.random(generation=0, phase=1)
    pop.append(other)

    filtered = gen.enforce_diversity(pop, threshold=0.0)
    # There should be at most 2 unique component configurations
    unique_comps = [tuple(sorted(c.components.items())) for c in filtered]
    # The duplicates of original should have been collapsed to 1
    assert unique_comps.count(tuple(sorted(original.components.items()))) <= 1


def test_diversity_filter_preserves_size_approximately():
    """enforce_diversity returns a non-empty list."""
    gen = ArchitectureGenerator(seed=42)
    pop = [Candidate.random(generation=0, phase=1) for _ in range(10)]
    filtered = gen.enforce_diversity(pop, threshold=0.3)
    assert len(filtered) >= 1
