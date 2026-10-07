"""Built-in production packing strategies."""
from ..solvers import register_solver
from .fast import FastFitSolver
from .best import BestFitSolver


def register_builtin_solvers() -> None:
    register_solver("fast_fit", FastFitSolver(), replace=True)
    register_solver("best_fit", BestFitSolver(), replace=True)


__all__ = ["BestFitSolver", "FastFitSolver", "register_builtin_solvers"]
