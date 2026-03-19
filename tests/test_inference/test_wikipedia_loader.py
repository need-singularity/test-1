# tests/test_inference/test_wikipedia_loader.py
from unittest.mock import patch, MagicMock
from tecs.inference.wikipedia_loader import WikipediaLoader


def test_extract_triples_from_text():
    loader = WikipediaLoader()
    loader.articles["Riemann hypothesis"] = (
        "In mathematics, the Riemann hypothesis is a conjecture that the Riemann zeta function "
        "has its zeros only at the negative even integers and complex numbers with real part 1/2. "
        "It was proposed by Bernhard Riemann in 1859. "
        "It is related to the distribution of prime numbers."
    )
    loader.links = [("Riemann hypothesis", "Riemann zeta function")]
    loader.categories = {"Riemann hypothesis": ["Conjectures", "Analytic number theory"]}

    triples = loader.extract_triples()
    assert len(triples) > 0
    # Should find IsA conjecture, ProposedBy Bernhard Riemann, RelatedTo distribution/prime numbers
    relations = [r for _, r, _ in triples]
    assert "RelatedTo" in relations
    assert "IsA" in relations


def test_normalize():
    loader = WikipediaLoader()
    assert loader._normalize("Hello World!") == "hello world"
    assert loader._normalize("  spaces  ") == "spaces"


def test_extract_from_text_patterns():
    loader = WikipediaLoader()
    triples = loader._extract_from_text("gravity", "Gravity is a fundamental force of nature. It has a gravitational constant.")
    # Should extract (gravity, IsA, fundamental force of nature) and (gravity, HasA, gravitational constant)
    assert len(triples) > 0


def test_load_topic_with_mock():
    loader = WikipediaLoader()
    with patch("requests.get") as mock_get:
        # Mock summary response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "title": "Cat",
            "extract": "The cat is a small domesticated carnivorous mammal."
        }
        mock_get.return_value = mock_resp

        loader._fetch_article("Cat")
        assert "Cat" in loader.articles
        assert "mammal" in loader.articles["Cat"]


def test_noise_filter():
    loader = WikipediaLoader()
    assert loader._is_noise("short description is different from wikidata")
    assert loader._is_noise("CS1 maint: multiple names")
    assert loader._is_noise("Articles with hCards")
    assert not loader._is_noise("quantum mechanics")
    assert not loader._is_noise("partial differential equation")


def test_deep_extraction():
    loader = WikipediaLoader()
    triples = loader._extract_from_text(
        "Black-Scholes model",
        "The Black-Scholes model is a mathematical model used in financial engineering. "
        "It is derived from the heat equation. "
        "The model assumes a geometric Brownian motion process. "
        "It is used to determine the price of European options. "
        "The model is analogous to the diffusion equation in physics."
    )
    assert len(triples) >= 3
    # Should find DerivedFrom, UsesProcess, AnalogousTo, etc.
    relations = [r for _, r, _ in triples]
    assert any(r in relations for r in ("DerivedFrom", "UsesProcess", "AnalogousTo", "IsA", "UsedIn"))
