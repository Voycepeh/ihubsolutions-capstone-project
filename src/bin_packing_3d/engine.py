"""Readable orchestration around interchangeable packing solvers."""
from __future__ import annotations

from collections.abc import Mapping
from time import perf_counter
from typing import Any

from .metrics import calculate_metrics
from .models import InvalidPackingPlanError, PackingPlan, PackingResult, ValidationError
from .rules import ensure_individual_feasibility, expand_items, normalize_boxes, normalize_config, normalize_order, usable_dimensions
from .solvers import get_solver
from .validate import validate_plan


def solve_order(
    order: Mapping[str, Any],
    boxes: Any,
    config: Mapping[str, Any] | None = None,
    *,
    trace: bool = False,
) -> PackingResult:
    """Solve one order through the same production path used by a future API.

    Args:
        order: Raw order containing item dimensions, weight, quantity, and
            VerticalRotation.
        boxes: Configurable carton catalogue. The engine sorts cartons by
            external volume from smallest to largest during normalization.
        config: Shared packing configuration including strategy, fill limits,
            and carton buffer.
        trace: When true, print human-readable pre-solver decisions. This is
            intended for demonstrations and debugging; it does not alter the
            selected strategy or packing result.

    Returns:
        A validated PackingResult with carton selections, XYZ placements,
        metrics, and runtime.

    Raises:
        PackingError subclasses when input, configuration, feasibility, or a
        solver-proposed plan is invalid.
    """
    order_id, order_number, source_items = normalize_order(order)
    normalized_boxes = normalize_boxes(boxes)
    normalized_config = normalize_config(config)
    # Validate buffers against every catalogue entry before a plugin sees the data.
    for box in normalized_boxes:
        usable_dimensions(box, normalized_config)
    physical_items = expand_items(source_items)
    ensure_individual_feasibility(physical_items, normalized_boxes, normalized_config)
    if trace:
        from .explain import print_pre_solver_trace
        print_pre_solver_trace(physical_items, normalized_boxes, normalized_config)
    if normalized_config.strategy in {"first_fit", "best_fit"}:
        # Register lazily so applications and tests can still manage custom plugins.
        from .strategies import register_builtin_solvers
        register_builtin_solvers()
    solver = get_solver(normalized_config.strategy)

    started = perf_counter()
    plan = solver.solve(physical_items, normalized_boxes, normalized_config)
    runtime_ms = (perf_counter() - started) * 1000.0
    if not isinstance(plan, PackingPlan):
        raise TypeError(f"Solver '{normalized_config.strategy}' must return PackingPlan")
    validation = validate_plan(plan, physical_items, normalized_boxes, normalized_config)
    # Accounting for an item as unpacked makes a plan structurally inspectable,
    # but it is not a successful solution. Every item passed to the solver has
    # already been proven to fit at least one available carton.
    for item_id in plan.unpacked_item_ids:
        validation.errors.append(ValidationError(
            "unpacked_item",
            f"Physical item '{item_id}' was not packed by strategy '{normalized_config.strategy}'",
            item_instance_id=item_id,
        ))
    validation.valid = not validation.errors
    if not validation.valid:
        raise InvalidPackingPlanError(validation)
    metrics = calculate_metrics(plan, physical_items, normalized_boxes, runtime_ms)
    return PackingResult(order_id, order_number, "success", normalized_config.strategy,
                         plan.packed_boxes, plan.unpacked_item_ids, runtime_ms, metrics, validation)
