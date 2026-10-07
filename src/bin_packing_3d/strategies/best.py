"""Exact-assisted Best mode for lexicographic carton optimization."""
from __future__ import annotations

from itertools import combinations_with_replacement
from time import perf_counter
import sys
import types
from functools import lru_cache

from ..models import Box, Orientation, PackedBox, PackingConfig, PackingPlan, PhysicalItem, Placement, Position
from ..rules import allowed_orientations, effective_max_fill_pct, item_fits_box, usable_dimensions
from .fast import FastFitSolver


@lru_cache(maxsize=1)
def _cp_model_module():
    """Load OR-Tools while tolerating environments that block optional pandas binaries."""
    try:
        import pandas  # noqa: F401
    except (ImportError, OSError):
        for name in tuple(sys.modules):
            if name == "pandas" or name.startswith("pandas."):
                sys.modules.pop(name, None)
        stub = types.ModuleType("pandas")
        stub.Series = type("Series", (), {})
        stub.DataFrame = type("DataFrame", (), {})
        stub.Index = type("Index", (), {})
        sys.modules["pandas"] = stub
        try:
            from ortools.sat.python import cp_model
        finally:
            sys.modules.pop("pandas", None)
    else:
        from ortools.sat.python import cp_model
    return cp_model


class BestFitSolver:
    """Return the proven best carton objective within the configured time budget."""

    name = "best_fit"

    @staticmethod
    def prepare() -> None:
        """Load the exact-search dependency outside the measured warm solve."""
        _cp_model_module()

    def solve(self, items: list[PhysicalItem], boxes: list[Box], config: PackingConfig) -> PackingPlan:
        # The engine normally calls prepare() before its runtime timer. Keep this
        # cached call for direct strategy users.
        _cp_model_module()
        started = perf_counter()
        deadline = started + config.max_runtime_ms / 1000.0
        # Fast is the incumbent and fallback. Exact search only replaces it when
        # CP-SAT finds a better carton objective within the shared deadline.
        incumbent = FastFitSolver().solve(items, boxes, config)
        incumbent.metadata.update({"optimality_proven": False, "search_status": "time_limit"})
        max_count = len(incumbent.packed_boxes)

        # Carton selection stays outside CP-SAT. Enumerate combinations from
        # fewest cartons upward; CP-SAT only proves whether one fixed choice can pack.
        for carton_count in range(1, max_count + 1):
            choices = sorted(
                combinations_with_replacement(boxes, carton_count),
                key=lambda choice: (
                    max(box.external_volume for box in choice),
                    sum(box.external_volume for box in choice),
                    tuple(box.code for box in choice),
                ),
            )
            for choice in choices:
                remaining_ms = (deadline - perf_counter()) * 1000.0
                if remaining_ms <= 0:
                    return incumbent
                if not self._passes_aggregate_checks(items, choice, config):
                    continue
                plan, status = self._solve_choice(items, choice, config, deadline)
                if status == "UNKNOWN":
                    return incumbent
                if plan is not None:
                    plan.metadata.update({
                        "optimality_proven": True,
                        "search_status": "optimal",
                        "carton_search": "exact_cp_sat",
                    })
                    return plan

        incumbent.metadata.update({"optimality_proven": True, "search_status": "optimal"})
        return incumbent

    @staticmethod
    def _passes_aggregate_checks(
        items: list[PhysicalItem], choice: tuple[Box, ...], config: PackingConfig
    ) -> bool:
        fill = effective_max_fill_pct(len(items), config) / 100.0
        if sum(usable_dimensions(box, config).volume * fill for box in choice) < sum(i.volume for i in items):
            return False
        if sum(box.max_weight for box in choice) < sum(i.weight for i in items):
            return False
        return all(any(item_fits_box(item, box, config) for box in choice) for item in items)

    @staticmethod
    def _solve_choice(
        items: list[PhysicalItem],
        choice: tuple[Box, ...],
        config: PackingConfig,
        deadline: float,
    ) -> tuple[PackingPlan | None, str]:
        cp_model = _cp_model_module()
        scale = 1000
        weight_scale = 10000
        dims = [usable_dimensions(box, config) for box in choice]
        scaled_dims = [
            tuple(round(value * scale) for value in (dim.length, dim.width, dim.height))
            for dim in dims
        ]
        # Convert the fixed carton choice into integer/Boolean CP-SAT variables.
        # Dimensions use integer scaling because CP-SAT does not model floats.
        model = cp_model.CpModel()
        max_l = max(dim[0] for dim in scaled_dims)
        max_w = max(dim[1] for dim in scaled_dims)
        max_h = max(dim[2] for dim in scaled_dims)
        xs = []; ys = []; zs = []; dxs = []; dys = []; dzs = []; assignments = []
        volumes = []; weights = []

        for index, item in enumerate(items):
            x = model.NewIntVar(0, max_l, f"x{index}")
            y = model.NewIntVar(0, max_w, f"y{index}")
            z = model.NewIntVar(0, max_h, f"z{index}")
            dx = model.NewIntVar(1, max_l, f"dx{index}")
            dy = model.NewIntVar(1, max_w, f"dy{index}")
            dz = model.NewIntVar(1, max_h, f"dz{index}")
            # dx/dy/dz must be one orientation allowed by our rotation policy.
            model.AddAllowedAssignments(
                [dx, dy, dz],
                [
                    (
                        round(orientation.length * scale),
                        round(orientation.width * scale),
                        round(orientation.height * scale),
                    )
                    for orientation in allowed_orientations(item)
                ],
            )
            # One Boolean per candidate carton; every physical item goes to exactly one.
            assigned = [model.NewBoolVar(f"a{index}_{box_index}") for box_index in range(len(choice))]
            model.AddExactlyOne(assigned)
            for box_index, (length, width, height) in enumerate(scaled_dims):
                model.Add(x + dx <= length).OnlyEnforceIf(assigned[box_index])
                model.Add(y + dy <= width).OnlyEnforceIf(assigned[box_index])
                model.Add(z + dz <= height).OnlyEnforceIf(assigned[box_index])
            xs.append(x); ys.append(y); zs.append(z); dxs.append(dx); dys.append(dy); dzs.append(dz)
            assignments.append(assigned)
            volumes.append(round(item.volume * scale ** 3))
            weights.append(round(item.weight * weight_scale))

        fill_pct = effective_max_fill_pct(len(items), config)
        for box_index, box in enumerate(choice):
            length, width, height = scaled_dims[box_index]
            model.Add(sum(weights[i] * assignments[i][box_index] for i in range(len(items)))
                      <= round(box.max_weight * weight_scale))
            model.Add(sum(volumes[i] * assignments[i][box_index] for i in range(len(items))) * 100
                      <= round(length * width * height * fill_pct))

        # If two items share a carton, at least one of six axis separation
        # directions must hold. This is the actual 3D non-overlap constraint.
        for left in range(len(items)):
            for right in range(left + 1, len(items)):
                for box_index in range(len(choice)):
                    directions = [model.NewBoolVar(f"d{left}_{right}_{box_index}_{d}") for d in range(6)]
                    for direction in directions:
                        model.Add(direction <= assignments[left][box_index])
                        model.Add(direction <= assignments[right][box_index])
                    model.Add(sum(directions) >= assignments[left][box_index] + assignments[right][box_index] - 1)
                    model.Add(xs[left] + dxs[left] <= xs[right]).OnlyEnforceIf(directions[0])
                    model.Add(xs[right] + dxs[right] <= xs[left]).OnlyEnforceIf(directions[1])
                    model.Add(ys[left] + dys[left] <= ys[right]).OnlyEnforceIf(directions[2])
                    model.Add(ys[right] + dys[right] <= ys[left]).OnlyEnforceIf(directions[3])
                    model.Add(zs[left] + dzs[left] <= zs[right]).OnlyEnforceIf(directions[4])
                    model.Add(zs[right] + dzs[right] <= zs[left]).OnlyEnforceIf(directions[5])

        # Only the time remaining from the overall Best-mode budget is given to CP-SAT.
        solver = cp_model.CpSolver()
        remaining_seconds = deadline - perf_counter()
        if remaining_seconds <= 0:
            return None, "UNKNOWN"
        solver.parameters.max_time_in_seconds = max(0.001, remaining_seconds)
        solver.parameters.num_search_workers = 1 if config.deterministic else 8
        solver.parameters.random_seed = 0
        status = solver.Solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None, "INFEASIBLE" if status == cp_model.INFEASIBLE else "UNKNOWN"

        # Translate solver values back to project domain objects. The engine
        # independently validates this PackingPlan before exposing it to callers.
        packed = [PackedBox(box.code, f"carton-{i + 1}", dims[i]) for i, box in enumerate(choice)]
        for index, item in enumerate(items):
            box_index = next(i for i, assigned in enumerate(assignments[index]) if solver.Value(assigned))
            packed[box_index].placements.append(Placement(
                item.instance_id,
                item.code,
                packed[box_index].instance_id,
                Orientation(solver.Value(dxs[index]) / scale, solver.Value(dys[index]) / scale,
                            solver.Value(dzs[index]) / scale),
                Position(solver.Value(xs[index]) / scale, solver.Value(ys[index]) / scale,
                         solver.Value(zs[index]) / scale),
            ))
        return PackingPlan([box for box in packed if box.placements]), "FEASIBLE"
