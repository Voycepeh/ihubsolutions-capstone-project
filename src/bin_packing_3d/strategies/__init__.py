"""Built-in production packing strategies."""
from ..solvers import register_solver
from .best_fit import BestFitSolver
from .first_fit import FirstFitSolver


def register_builtin_solvers() -> None:
    register_solver("first_fit", FirstFitSolver(), replace=True)
    register_solver("best_fit", BestFitSolver(), replace=True)


__all__ = ["BestFitSolver", "FirstFitSolver", "register_builtin_solvers"]
