# tests/test_config.py
from tecs.config import load_config

def test_load_config_defaults():
    cfg = load_config("config.yaml")
    assert cfg.search.population_size == 50
    assert cfg.fitness.w_emergence == 0.4
    assert cfg.termination.max_hours == 48
    assert cfg.emergence.window_size == 10

def test_load_config_override():
    cfg = load_config("config.yaml", overrides={"search.population_size": 100})
    assert cfg.search.population_size == 100
