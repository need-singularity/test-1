# tecs/components/registry.py
from __future__ import annotations
from tecs.components.base import Component
from tecs.types import TopologyState


class ComponentRegistry:
    def __init__(self):
        self._components: dict[str, dict[str, Component]] = {}

    def register(self, component: Component) -> None:
        layer = component.layer
        name = component.name
        self._components.setdefault(layer, {})[name] = component

    def get(self, layer: str, name: str) -> Component:
        try:
            return self._components[layer][name]
        except KeyError:
            raise KeyError(f"Component '{name}' not found in layer '{layer}'")

    def check_compatible(self, component: Component, state: TopologyState) -> bool:
        return state.complex_type in component.compatible_types

    def list_layers(self) -> list[str]:
        return list(self._components.keys())

    def list_components(self, layer: str) -> list[str]:
        return list(self._components.get(layer, {}).keys())
