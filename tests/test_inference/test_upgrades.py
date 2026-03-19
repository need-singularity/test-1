from tecs.inference.dimension_checker import DimensionChecker


def test_dimension_match():
    dc = DimensionChecker()
    result = dc.check("M*L^2/T^2", "M*L^2/T^2")
    assert result["match"] is True


def test_dimension_mismatch():
    dc = DimensionChecker()
    result = dc.check("L^2/T", "L/T")
    assert result["match"] is False


def test_dimensionless():
    dc = DimensionChecker()
    result = dc.check("1", "1")
    assert result["match"] is True


def test_validate_equation():
    dc = DimensionChecker()
    s = dc.validate_equation("test", "M*L/T^2", "M*L/T^2")
    assert "PASS" in s


def test_validate_fail():
    dc = DimensionChecker()
    s = dc.validate_equation("test", "L^2", "L^3")
    assert "MISMATCH" in s


from tecs.inference.debate import DebateProtocol


def test_debate_disabled():
    d = DebateProtocol(enabled=False)
    result = d.debate({"claim": "test"})
    assert result["verdict"] == "SKIP"
