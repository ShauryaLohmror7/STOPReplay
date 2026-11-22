"""Adapter registry: adapters can be independently enabled, disabled or replaced."""
from __future__ import annotations

from .base import CollectionAdapter


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, CollectionAdapter] = {}
        self._enabled: set[str] = set()

    def register(self, adapter: CollectionAdapter, *, enabled: bool = True) -> CollectionAdapter:
        self._adapters[adapter.name] = adapter  # replacing by name is allowed
        if enabled:
            self._enabled.add(adapter.name)
        else:
            self._enabled.discard(adapter.name)
        return adapter

    def enable(self, name: str) -> None:
        if name not in self._adapters:
            raise KeyError(name)
        self._enabled.add(name)

    def disable(self, name: str) -> None:
        self._enabled.discard(name)

    def get(self, name: str) -> CollectionAdapter:
        return self._adapters[name]

    def is_enabled(self, name: str) -> bool:
        return name in self._enabled

    def enabled_adapters(self) -> list[CollectionAdapter]:
        return [a for n, a in self._adapters.items() if n in self._enabled]

    def names(self) -> list[str]:
        return sorted(self._adapters)
