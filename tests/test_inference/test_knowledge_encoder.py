from tecs.inference.knowledge_encoder import KnowledgeEncoder


def test_load_synthetic_glove():
    enc = KnowledgeEncoder()
    enc.load_glove("nonexistent.txt")  # falls back to synthetic
    assert len(enc._word_vectors) > 0
    assert "cat" in enc._word_vectors


def test_load_synthetic_triples():
    enc = KnowledgeEncoder()
    enc.load_conceptnet_triples()  # synthetic
    assert len(enc._triples) > 0


def test_build_complex():
    enc = KnowledgeEncoder()
    enc.load_glove("nonexistent.txt")
    enc.load_conceptnet_triples()
    state = enc.build_complex()
    assert state.complex is not None
    assert state.complex_type == "graph"
    assert len(state.complex.nodes) > 0
    assert "entity_index" in state.metadata


def test_entity_index():
    enc = KnowledgeEncoder()
    enc.load_glove("nonexistent.txt")
    enc.load_conceptnet_triples()
    enc.build_complex()
    assert "cat" in enc.entity_index
    assert "dog" in enc.entity_index
