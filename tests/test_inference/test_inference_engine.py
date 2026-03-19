from tecs.inference.knowledge_encoder import KnowledgeEncoder
from tecs.inference.inference_engine import InferenceEngine


def _make_engine():
    enc = KnowledgeEncoder()
    enc.load_glove("nonexistent.txt")
    enc.load_conceptnet_triples()
    knowledge = enc.build_complex()
    return InferenceEngine(knowledge)


def test_level1_direct():
    engine = _make_engine()
    result = engine.query("cat", "IsA")
    assert result.answer in ("mammal", "animal")
    assert result.confidence > 0
    assert result.level >= 1


def test_level1_direct_specific():
    engine = _make_engine()
    result = engine.query("cat", "HasA")
    assert result.answer == "fur"
    assert result.level >= 1


def test_unknown_entity():
    engine = _make_engine()
    result = engine.query("xyznonexistent", "IsA")
    assert result.answer == "unknown"
    assert result.confidence == 0.0


def test_level2_multipath():
    engine = _make_engine()
    result = engine.query("cat", "IsA")
    # Should find "animal" via cat -> mammal -> animal
    assert result.answer in ("mammal", "animal")
    assert result.confidence > 0


def test_verification():
    engine = _make_engine()
    result = engine.query("cat", "IsA")
    assert isinstance(result.verified, bool)


def test_result_to_dict():
    engine = _make_engine()
    result = engine.query("cat", "IsA")
    d = result.to_dict()
    assert "answer" in d
    assert "confidence" in d
    assert "level" in d
    assert "verified" in d


def test_cross_domain():
    engine = _make_engine()
    result = engine.query("gravity", "IsA")
    assert result.answer == "force"


def test_repr():
    engine = _make_engine()
    result = engine.query("cat", "IsA")
    s = repr(result)
    assert "L" in s  # level indicator


def test_eval_set_has_level2_only_queries():
    from tecs.inference.eval_set import EVAL_QUERIES, EVAL_KNOWLEDGE
    direct_triples = {(h, r, t) for h, r, t in EVAL_KNOWLEDGE}
    level2_no_direct = []
    for subj, rel, expected, lvl, _ in EVAL_QUERIES:
        if lvl == 2 and (subj, rel, expected) not in direct_triples:
            level2_no_direct.append((subj, rel, expected))
    assert len(level2_no_direct) >= 5


def test_eval_set_has_reverse_triples():
    from tecs.inference.eval_set import EVAL_KNOWLEDGE
    partof = [(h, r, t) for h, r, t in EVAL_KNOWLEDGE if r == "PartOf"]
    assert len(partof) >= 3


def test_eval_set_has_cross_domain_queries():
    from tecs.inference.eval_set import EVAL_QUERIES
    level4 = [q for q in EVAL_QUERIES if q[3] >= 4]
    assert len(level4) >= 3


def test_engine_uses_adaptive_sigma():
    engine = _make_engine()
    assert hasattr(engine, '_sigma')
    assert isinstance(engine._sigma, float)
    assert 0.05 <= engine._sigma <= 0.30 or engine._sigma == 0.15


def test_engine_has_fuchsian_group():
    engine = _make_engine()
    assert hasattr(engine, '_fuchsian_group')
