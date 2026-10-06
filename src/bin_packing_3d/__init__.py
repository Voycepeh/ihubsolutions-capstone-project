"""Public facade for the pluggable 3D packing engine."""
from .display import DisplayTable, display_result, display_table, make_table, result_tables
from .engine import solve_order
from .models import PackingObjective
from .rules import packing_objective
from .solvers import register_solver
from .visualize import visualize_result

__all__ = [
    "display_result",
    "display_table",
    "DisplayTable",
    "make_table",
    "PackingObjective",
    "packing_objective",
    "register_solver",
    "result_tables",
    "solve_order",
    "visualize_result",
]
