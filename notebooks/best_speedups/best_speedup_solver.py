"""Best mode with the five search speed-ups and the large-carton overflow fix.

Standalone version of ``src/bin_packing_3d/strategies/best.py``: the project's
own Best is left unchanged, and this module is registered as an extra solver.

    from best_speedup_solver import BestFitSolver
    register_solver("best_speedups", BestFitSolver())                 # all speed-ups on
    register_solver("best_original", BestFitSolver(reuse_incumbent=False, hint_incumbent=False,
                    carton_symmetry=False, item_symmetry=False, pair_pruning=False))

Changes against the project's Best:

* Overflow fix: the fill-cap constraint uses unscaled mm^3 volumes. The original
  scaled volumes by 1000^3, which exceeds CP-SAT's int64 range for cartons
  above about 92 L (e.g. 600 x 400 x 400 mm).
* Speed-ups (all on by default, each with an on/off switch; see the class docstring).
* New ``best_result_source`` value ``fast_proven_optimal``: Fast's layout was
  returned because every better carton combination was proven impossible.

Results and method: RESULTS.md in this folder.
"""
from __future__ import annotations

from itertools import combinations_with_replacement
from time import perf_counter
import sys
import types
from functools import lru_cache
from math import ceil, floor

from bin_packing_3d.models import Box, Orientation, PackedBox, PackingConfig, PackingPlan, PhysicalItem, Placement, Position
from bin_packing_3d.rules import allowed_orientations, effective_max_fill_pct, item_fits_box, usable_dimensions
from bin_packing_3d.strategies.fast import FastFitSolver


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


def _add_lex_less(model, first, second, name: str) -> None:
    """Require the integer tuple ``first`` to be lexicographically below ``second``.

    One Boolean per position k means "equal before k and strictly smaller at k";
    at least one of them must hold.
    """
    equal = []
    choices = []
    for k, (a, b) in enumerate(zip(first, second)):
        smaller_here = model.NewBoolVar(f"{name}_lt{k}")
        model.Add(a + 1 <= b).OnlyEnforceIf(smaller_here)
        for previous in equal:
            model.AddImplication(smaller_here, previous)
        choices.append(smaller_here)
        same = model.NewBoolVar(f"{name}_eq{k}")
        model.Add(a == b).OnlyEnforceIf(same)
        equal.append(same)
    model.AddBoolOr(choices)


class BestFitSolver:
    """Return the proven best carton objective within the configured time budget.

    The keyword options switch individual search speed-ups on or off. They
    never change the carton objective Best proves, only how fast it gets
    there, and exist so benchmarks can measure each speed-up separately:

    * ``reuse_incumbent``: when the search reaches Fast's own carton
      combination, return Fast's validated layout instead of re-solving it.
    * ``hint_incumbent``: give CP-SAT Fast's layout as a starting hint when
      solving Fast's own carton combination.
    * ``carton_symmetry``: identical cartons in a combination are filled in
      non-increasing order of packed volume.
    * ``item_symmetry``: physically identical items are kept in a fixed
      order of (carton, z, y, x).
    * ``pair_pruning``: before solving, drop carton assignments and
      separation directions that simple dimension sums prove impossible.
    """

    name = "best_fit_speedups"

    def __init__(
        self,
        *,
        reuse_incumbent: bool = True,
        hint_incumbent: bool = True,
        carton_symmetry: bool = True,
        item_symmetry: bool = True,
        pair_pruning: bool = True,
    ) -> None:
        self.reuse_incumbent = reuse_incumbent
        self.hint_incumbent = hint_incumbent
        self.carton_symmetry = carton_symmetry
        self.item_symmetry = item_symmetry
        self.pair_pruning = pair_pruning

    @staticmethod
    def prepare() -> None:
        """Load the exact-search dependency outside the measured warm solve."""
        _cp_model_module()

    def solve(self, items: list[PhysicalItem], boxes: list[Box], config: PackingConfig) -> PackingPlan:
        # The engine normally calls prepare() before its runtime timer. Keep this
        # cached call for direct strategy users.
        _cp_model_module()
        # Fast is the incumbent and fallback. Exact search only replaces it when
        # CP-SAT finds a better carton objective within the shared deadline.
        incumbent = FastFitSolver().solve(items, boxes, config)
        deadline = None if config.max_runtime_ms is None else perf_counter() + config.max_runtime_ms / 1000.0
        incumbent.metadata.update({"optimality_proven": False, "search_status": "time_limit", "best_result_source": "fast_fallback"})
        max_count = len(incumbent.packed_boxes)
        incumbent_key = tuple(sorted(packed.box_code for packed in incumbent.packed_boxes))

        # Carton selection stays outside CP-SAT. Enumerate combinations from
        # fewest cartons upward; CP-SAT only proves whether one fixed choice can pack.
        for carton_count in range(1, max_count + 1):
            choices = sorted(
                combinations_with_replacement(boxes, carton_count),
                key=lambda choice: (
                    sum(box.external_volume for box in choice),
                    tuple(box.code for box in choice),
                ),
            )
            for choice in choices:
                remaining_ms = None if deadline is None else (deadline - perf_counter()) * 1000.0
                if remaining_ms is not None and remaining_ms <= 0:
                    return incumbent
                if not self._passes_aggregate_checks(items, choice, config):
                    continue
                is_incumbent_choice = tuple(sorted(box.code for box in choice)) == incumbent_key
                if self.reuse_incumbent and is_incumbent_choice and not incumbent.unpacked_item_ids:
                    # Every higher-ranked combination has been ruled out, and Fast
                    # already holds a valid layout for this one: it is optimal.
                    incumbent.metadata.update({
                        "optimality_proven": True,
                        "search_status": "optimal",
                        "best_result_source": "fast_proven_optimal",
                    })
                    return incumbent
                hint = incumbent if self.hint_incumbent and is_incumbent_choice else None
                plan, status = self._solve_choice(items, choice, config, deadline, hint)
                if status == "UNKNOWN":
                    return incumbent
                if plan is not None:
                    incumbent_score = (len(incumbent.packed_boxes), sum(box.external_volume for box in boxes for packed in incumbent.packed_boxes if packed.box_code == box.code))
                    plan_score = (len(plan.packed_boxes), sum(box.external_volume for box in boxes for packed in plan.packed_boxes if packed.box_code == box.code))
                    if plan_score > incumbent_score:
                        return incumbent
                    plan.metadata.update({
                        "optimality_proven": True,
                        "search_status": "optimal",
                        "carton_search": "exact_cp_sat",
                        "best_result_source": "best_calculation",
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

    def _solve_choice(
        self,
        items: list[PhysicalItem],
        choice: tuple[Box, ...],
        config: PackingConfig,
        deadline: float | None,
        hint: PackingPlan | None = None,
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
        # Scaled orientations of each item that fit inside each chosen carton.
        fitting = [
            [
                [
                    scaled for scaled in (
                        tuple(round(value * scale) for value in (o.length, o.width, o.height))
                        for o in allowed_orientations(item)
                    )
                    if all(scaled[axis] <= carton[axis] for axis in range(3))
                ]
                for carton in scaled_dims
            ]
            for item in items
        ]

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
            if self.pair_pruning:
                for box_index in range(len(choice)):
                    if not fitting[index][box_index]:
                        model.Add(assigned[box_index] == 0)
            for box_index, (length, width, height) in enumerate(scaled_dims):
                model.Add(x + dx <= length).OnlyEnforceIf(assigned[box_index])
                model.Add(y + dy <= width).OnlyEnforceIf(assigned[box_index])
                model.Add(z + dz <= height).OnlyEnforceIf(assigned[box_index])
            xs.append(x); ys.append(y); zs.append(z); dxs.append(dx); dys.append(dy); dzs.append(dz)
            assignments.append(assigned)
            # Volumes stay in unscaled mm^3: scaling by scale**3 overflows
            # CP-SAT's int64 bounds for cartons or orders above roughly 92 L.
            # Rounding item volume up keeps the fill check conservative.
            volumes.append(ceil(item.volume))
            weights.append(round(item.weight * weight_scale))

        fill_pct = effective_max_fill_pct(len(items), config)
        for box_index, box in enumerate(choice):
            model.Add(sum(weights[i] * assignments[i][box_index] for i in range(len(items)))
                      <= round(box.max_weight * weight_scale))
            model.Add(sum(volumes[i] * assignments[i][box_index] for i in range(len(items))) * 100
                      <= floor(dims[box_index].volume * fill_pct))

        # If two items share a carton, at least one of six axis separation
        # directions must hold. This is the actual 3D non-overlap constraint.
        positions = (xs, ys, zs)
        sizes = (dxs, dys, dzs)
        for left in range(len(items)):
            for right in range(left + 1, len(items)):
                for box_index in range(len(choice)):
                    left_in = assignments[left][box_index]
                    right_in = assignments[right][box_index]
                    axes = range(3)
                    if self.pair_pruning:
                        left_fits = fitting[left][box_index]
                        right_fits = fitting[right][box_index]
                        if not left_fits or not right_fits:
                            continue  # one of the items can never use this carton
                        # Separation along an axis is possible only if the two
                        # shortest fitting extents on that axis fit side by side.
                        axes = [
                            axis for axis in range(3)
                            if min(o[axis] for o in left_fits) + min(o[axis] for o in right_fits)
                            <= scaled_dims[box_index][axis]
                        ]
                        if not axes:
                            model.Add(left_in + right_in <= 1)
                            continue
                    directions = []
                    for axis in axes:
                        before = model.NewBoolVar(f"d{left}_{right}_{box_index}_{axis}_0")
                        after = model.NewBoolVar(f"d{left}_{right}_{box_index}_{axis}_1")
                        model.Add(positions[axis][left] + sizes[axis][left] <= positions[axis][right]).OnlyEnforceIf(before)
                        model.Add(positions[axis][right] + sizes[axis][right] <= positions[axis][left]).OnlyEnforceIf(after)
                        directions.extend((before, after))
                    for direction in directions:
                        model.Add(direction <= left_in)
                        model.Add(direction <= right_in)
                    model.Add(sum(directions) >= left_in + right_in - 1)

        if self.carton_symmetry:
            # Relabelling identical cartons gives the same packing, so require
            # their packed volumes to be non-increasing in combination order.
            for box_index in range(1, len(choice)):
                if choice[box_index].code == choice[box_index - 1].code:
                    model.Add(
                        sum(volumes[i] * assignments[i][box_index - 1] for i in range(len(items)))
                        >= sum(volumes[i] * assignments[i][box_index] for i in range(len(items)))
                    )

        if self.item_symmetry:
            # Swapping physically identical items gives the same packing, so keep
            # them in strictly increasing (carton, z, y, x) order. Identical items
            # in one carton cannot share a corner, so the order is always strict.
            # Swapping identical items leaves every carton's packed volume
            # unchanged, so this is compatible with the carton ordering above.
            groups: dict[tuple, list[int]] = {}
            for index, item in enumerate(items):
                source = item.source_item
                key = (source.length, source.width, source.height, source.weight, source.vertical_rotation)
                groups.setdefault(key, []).append(index)
            carton_of = []
            for index in range(len(items)):
                carton = model.NewIntVar(0, len(choice) - 1, f"c{index}")
                model.Add(carton == sum(b * assignments[index][b] for b in range(len(choice))))
                carton_of.append(carton)
            for members in groups.values():
                for first, second in zip(members, members[1:]):
                    _add_lex_less(
                        model,
                        [carton_of[first], zs[first], ys[first], xs[first]],
                        [carton_of[second], zs[second], ys[second], xs[second]],
                        f"s{first}_{second}",
                    )

        if hint is not None:
            # Map Fast's cartons onto this combination's carton slots by code.
            slots: dict[str, list[int]] = {}
            for box_index, box in enumerate(choice):
                slots.setdefault(box.code, []).append(box_index)
            index_of = {item.instance_id: index for index, item in enumerate(items)}
            for packed in hint.packed_boxes:
                box_index = slots[packed.box_code].pop(0)
                for placement in packed.placements:
                    index = index_of[placement.item_instance_id]
                    for b, var in enumerate(assignments[index]):
                        model.AddHint(var, int(b == box_index))
                    for var, value in (
                        (xs[index], placement.position.x), (ys[index], placement.position.y),
                        (zs[index], placement.position.z), (dxs[index], placement.orientation.length),
                        (dys[index], placement.orientation.width), (dzs[index], placement.orientation.height),
                    ):
                        model.AddHint(var, round(value * scale))

        # Only the time remaining from the overall Best-mode budget is given to CP-SAT.
        solver = cp_model.CpSolver()
        remaining_seconds = None if deadline is None else deadline - perf_counter()
        if remaining_seconds is not None:
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
