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
