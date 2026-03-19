# tests/test_components/test_registry.py
from tecs.components.registry import ComponentRegistry
from tecs.components.base import Component
from tecs.types import TopologyState, LAYERS, COMPONENT_POOL
import numpy as np

class FakeComponent:
    name = "fake"
    layer = "representation"
    compatible_types = ["simplicial"]

    def configure(self, params: dict) -> None:
        self.params = params

    def execute(self, state: TopologyState) -> TopologyState:
        return state

    def measure(self, state: TopologyState) -> dict[str, float]:
        return {"test": 1.0}

    def cost(self) -> float:
        return 0.1

def test_register_and_get():
    reg = ComponentRegistry()
    comp = FakeComponent()
    reg.register(comp)
    assert reg.get("representation", "fake") is comp

def test_get_missing_raises():
    import pytest
    reg = ComponentRegistry()
    with pytest.raises(KeyError):
        reg.get("representation", "nonexistent")

def test_check_compatibility_pass():
    reg = ComponentRegistry()
    comp = FakeComponent()
    reg.register(comp)
    state = TopologyState.empty("simplicial")
    assert reg.check_compatible(comp, state) is True

def test_check_compatibility_fail():
    reg = ComponentRegistry()
    comp = FakeComponent()
    reg.register(comp)
    state = TopologyState.empty("graph")
    assert reg.check_compatible(comp, state) is False

def test_list_layers():
    reg = ComponentRegistry()
    reg.register(FakeComponent())
    assert "representation" in reg.list_layers()
