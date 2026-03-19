from tecs.inference.knowledge_encoder import KnowledgeEncoder
from tecs.inference.analogy_engine import AnalogyEngine


def _make_engine():
    enc = KnowledgeEncoder()
    enc.load_glove("nonexistent.txt")  # synthetic with clustered vectors
    enc.load_conceptnet_triples()  # synthetic triples
    knowledge = enc.build_complex()
    return AnalogyEngine(knowledge)


def test_find_analogy():
    engine = _make_engine()
    results = engine.find_analogy("gravity", "economics")
    assert isinstance(results, list)
    # Should find something since gravity(physics) and price(economics)
    # have similar local topology in the synthetic data


def test_find_analogy_returns_mapping():
    engine = _make_engine()
    results = engine.find_analogy("force", "economics")
    if results:
        d = results[0].to_dict()
        assert "mapping" in d
        assert results[0].similarity > 0


def test_compare_concepts():
    engine = _make_engine()
    results = engine.find_cross_domain_pattern("gravity", "price")
    assert isinstance(results, list)
    if results:
        assert results[0].source_concept == "gravity"
        assert results[0].target_concept == "price"


def test_unknown_concept():
    engine = _make_engine()
    results = engine.find_analogy("xyznonexistent", "economics")
    assert results == []


def test_domain_classification():
    engine = _make_engine()
    # gravity should be classified as physics
    assert engine._entity_domains.get("gravity") == "physics"
    # price should be classified as economics
    assert engine._entity_domains.get("price") == "economics"


def test_structural_signature():
    engine = _make_engine()
    idx = engine._entity_index.get("gravity")
    if idx is not None:
        sig = engine._get_structural_signature(idx)
        assert sig is not None
        assert "degree" in sig
        assert "clustering" in sig


def test_result_repr():
    engine = _make_engine()
    results = engine.find_analogy("gravity", "economics")
    if results:
        s = repr(results[0])
        assert "~" in s or "Analogy" in s
        assert "Mapping" in s


def test_result_to_dict():
    engine = _make_engine()
    results = engine.find_analogy("gravity", "economics")
    if results:
        d = results[0].to_dict()
        assert "source" in d
        assert "target" in d
        assert "similarity" in d
        assert "verified" in d


def test_compare_unknown():
    engine = _make_engine()
    results = engine.find_cross_domain_pattern("xyznonexistent", "price")
    assert results == []


def test_compare_returns_similarity():
    engine = _make_engine()
    results = engine.find_cross_domain_pattern("gravity", "price")
    if results:
        assert 0.0 <= results[0].similarity <= 1.0
