# tecs/components/base.py
from __future__ import annotations
from typing import Protocol, runtime_checkable
from tecs.types import TopologyState


@runtime_checkable
class Component(Protocol):
    name: str
    layer: str
    compatible_types: list[str]

    def configure(self, params: dict) -> None: ...
    def execute(self, state: TopologyState) -> TopologyState: ...
    def measure(self, state: TopologyState) -> dict[str, float]: ...
    def cost(self) -> float: ...


@runtime_checkable
class VerificationComponent(Component, Protocol):
    def verify(self, state: TopologyState, reference: TopologyState) -> dict[str, float]: ...
