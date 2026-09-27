"""Minimal solver protocol and explicit registry."""
from __future__ import annotations

from typing import Protocol

from .models import Box, PackingConfig, PackingPlan, PhysicalItem, UnknownStrategyError


class PackingSolver(Protocol):
    name: str

    def solve(self, items: list[PhysicalItem], boxes: list[Box], config: PackingConfig) -> PackingPlan:
        ...


_REGISTRY: dict[str, PackingSolver] = {}


def register_solver(name: str, solver: PackingSolver, *, replace: bool = False) -> None:
    normalized = name.strip().lower()
    if not normalized:
        raise ValueError("Solver strategy name must not be empty")
    if normalized in _REGISTRY and not replace:
        raise ValueError(f"Solver strategy '{normalized}' is already registered")
    if not callable(getattr(solver, "solve", None)):
        raise TypeError("Registered solver must provide a callable solve method")
    _REGISTRY[normalized] = solver


def get_solver(name: str) -> PackingSolver:
    normalized = name.strip().lower()
    try:
        return _REGISTRY[normalized]
    except KeyError as exc:
        available = ", ".join(list_registered_solvers()) or "none"
        raise UnknownStrategyError(
            f"Unknown strategy '{name}'; registered strategies: {available}"
        ) from exc


def list_registered_solvers() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


def unregister_solver(name: str) -> None:
    """Remove a registration; primarily useful for isolated applications and tests."""
    _REGISTRY.pop(name.strip().lower(), None)
