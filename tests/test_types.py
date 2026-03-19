# tests/test_types.py
import numpy as np
from tecs.types import TopologyState, Candidate, LAYERS, COMPONENT_POOL

def test_topology_state_creation():
    state = TopologyState.empty("simplicial")
    assert state.complex_type == "simplicial"
    assert state.complex is None
    assert state.metrics == {}
    assert state.history == []

def test_topology_state_rejects_invalid_type():
    import pytest
    with pytest.raises(ValueError):
        TopologyState.empty("invalid_type")

def test_candidate_creation():
    c = Candidate.random(generation=0, phase=1)
    assert len(c.components) == 5
    assert all(layer in c.components for layer in LAYERS)
    assert c.generation == 0
    assert c.parent_ids == []
    assert c.id  # uuid assigned

def test_candidate_hamming_distance():
    c1 = Candidate.random(generation=0, phase=1)
    c2 = Candidate.random(generation=0, phase=1)
    d = c1.hamming_distance(c2)
    assert 0 <= d <= 5

def test_component_pool_completeness():
    assert len(LAYERS) == 5
    for layer in LAYERS:
        assert len(COMPONENT_POOL[layer]) == 3
