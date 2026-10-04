"""Readable orchestration around interchangeable packing solvers."""
from __future__ import annotations

from collections.abc import Mapping
from time import perf_counter
from typing import Any

from .models import Box, BoxMetrics, InvalidPackingPlanError, PackingMetrics, PackingPlan, PackingResult, PhysicalItem, ValidationError
from .rules import allowed_orientations, effective_max_fill_pct, ensure_individual_feasibility, expand_items, normalize_boxes, normalize_config, normalize_order, usable_dimensions
from .solvers import get_solver
from .validate import validate_plan


def _fmt(value: float) -> str:
    """Format measurements compactly without hiding meaningful decimals."""
    return f"{value:g}"


def _print_trace(
    items: list[PhysicalItem],
    boxes: list[Box],
    config: PackingConfig,
) -> None:
    """Print the deterministic checks performed before 3D search.

    The catalogue has already been normalized and sorted by external carton
    volume. For a single physical item this gives a complete, easy-to-follow
    proof of why smaller cartons are rejected before the first feasible carton
    is selected. For multiple items the aggregate volume check is only a
    necessary check; the solver must still prove that all cuboids can coexist.
    """
    total_volume = sum(item.volume for item in items)
    total_weight = sum(item.weight for item in items)
    fill_pct = effective_max_fill_pct(len(items), config)

    print("=== 3D packing trace ===")
    print(f"Total item count: {len(items)}")
    print(f"Total item volume: {_fmt(total_volume)} mm^3")
    print(f"Total item weight: {_fmt(total_weight)} kg")
    print(f"Effective maximum fill: {_fmt(fill_pct)}%")
    print("Candidate cartons: sorted by external volume (smallest first)")

    for box in boxes:
        usable = usable_dimensions(box, config)
        usable_cap = usable.volume * fill_pct / 100.0
        print(
            f"\n{box.code}: external volume={_fmt(box.external_volume)} mm^3; "
            f"usable={_fmt(usable.length)} x {_fmt(usable.width)} x {_fmt(usable.height)} mm; "
            f"volume cap={_fmt(usable_cap)} mm^3"
        )

        if total_weight > box.max_weight:
            print(
                f"  REJECTED by weight: {_fmt(total_weight)} kg > "
                f"{_fmt(box.max_weight)} kg"
            )
            continue

        if total_volume > usable_cap:
            print(
                f"  REJECTED by volume: {_fmt(total_volume)} mm^3 > "
                f"{_fmt(usable_cap)} mm^3"
            )
            continue

        print(
            f"  Volume check ACCEPTED: {_fmt(total_volume)} mm^3 <= "
            f"{_fmt(usable_cap)} mm^3"
        )

        if len(items) != 1:
            print("  Geometry: deferred to the multi-item 3D placement solver")
            continue

        item = items[0]
        fitting = []
        print(
            f"  Item {item.instance_id}: "
            f"{_fmt(item.source_item.length)} x {_fmt(item.source_item.width)} x "
            f"{_fmt(item.source_item.height)} mm; "
            f"VerticalRotation={'Yes' if item.source_item.vertical_rotation else 'No'}"
        )
        for orientation in allowed_orientations(item):
            failures = []
            if orientation.length > usable.length:
                failures.append(f"L {_fmt(orientation.length)} > {_fmt(usable.length)}")
            if orientation.width > usable.width:
                failures.append(f"W {_fmt(orientation.width)} > {_fmt(usable.width)}")
            if orientation.height > usable.height:
                failures.append(f"H {_fmt(orientation.height)} > {_fmt(usable.height)}")
            label = (
                f"{_fmt(orientation.length)} x {_fmt(orientation.width)} x "
                f"{_fmt(orientation.height)}"
            )
            if failures:
                print(f"    orientation {label}: rejected ({', '.join(failures)})")
            else:
                print(f"    orientation {label}: fits")
                fitting.append(orientation)

        if fitting:
            print(f"  GEOMETRY ACCEPTED: {box.code} is feasible for this item")
            print(f"  SELECTED: {box.code} is the smallest feasible carton by external volume")
            break
        else:
            print(f"  REJECTED by geometry: no allowed orientation fits {box.code}")


def calculate_metrics(plan: PackingPlan, items: list[PhysicalItem], boxes: list[Box], runtime_ms: float) -> PackingMetrics:
    item_by_id = {item.instance_id: item for item in items}
    box_by_code = {box.code: box for box in boxes}
    total_external = sum(box_by_code[b.box_code].external_volume for b in plan.packed_boxes if b.box_code in box_by_code)
    total_packed = sum(item_by_id[p.item_instance_id].volume for p in plan.placements if p.item_instance_id in item_by_id)
    per_box: list[BoxMetrics] = []
    for packed_box in plan.packed_boxes:
        known = [item_by_id[p.item_instance_id] for p in packed_box.placements if p.item_instance_id in item_by_id]
        volume = sum(item.volume for item in known)
        usable_volume = packed_box.usable_dimensions.volume
        per_box.append(BoxMetrics(packed_box.instance_id, sum(item.weight for item in known), volume,
                                  100.0 * volume / usable_volume if usable_volume else 0.0))
    return PackingMetrics(
        box_count=len(plan.packed_boxes), total_external_box_volume=total_external,
        total_packed_item_volume=total_packed,
        overall_utilization_pct=100.0 * total_packed / total_external if total_external else 0.0,
        packed_item_count=len(plan.placements), unpacked_item_count=len(plan.unpacked_item_ids),
        runtime_ms=runtime_ms, boxes=per_box,
    )


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
        _print_trace(physical_items, normalized_boxes, normalized_config)
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
