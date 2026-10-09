"""Readable orchestration around interchangeable packing solvers."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from time import perf_counter
from typing import Literal

from .models import Box, BoxMetrics, InvalidPackingPlanError, Orientation, PackingConfig, PackingMetrics, PackingPlan, PackingResult, PhysicalItem, ValidationError
from .rules import allowed_orientations, effective_max_fill_pct, ensure_individual_feasibility, expand_items, normalize_boxes, normalize_config, normalize_order, usable_dimensions
from .solvers import get_solver
from .validate import validate_plan


def _fmt(value: float) -> str:
    """Format measurements compactly without hiding meaningful decimals."""
    return f"{value:,.6f}".rstrip("0").rstrip(".")


OrderInput = Mapping[str, object]
BoxInput = Sequence[Mapping[str, object]] | Mapping[str, object]
VisualizationOptions = Mapping[str, float | bool]
DimensionUnit = Literal["mm"]
PackingMode = Literal["fast", "best"]


def _print_table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> None:
    """Print a small dependency-free table for diagnostic logs."""
    widths = [
        max(len(header), *(len(row[index]) for row in rows))
        for index, header in enumerate(headers)
    ]
    print(" | ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


def _print_logs(
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

    print("=== 3D packing log ===\n")
    print("Order summary")
    _print_table(
        ("Metric", "Value"),
        [
            ("Physical items", str(len(items))),
            ("Total item volume", f"{_fmt(total_volume)} mm^3"),
            ("Total item weight", f"{_fmt(total_weight)} kg"),
            ("Effective maximum fill", f"{_fmt(fill_pct)}%"),
        ],
    )

    candidate_rows: list[tuple[str, ...]] = []
    orientation_sections: list[tuple[str, list[tuple[str, ...]]]] = []

    for box in boxes:
        usable = usable_dimensions(box, config)
        usable_cap = usable.volume * fill_pct / 100.0
        usable_label = f"{_fmt(usable.length)} x {_fmt(usable.width)} x {_fmt(usable.height)}"

        if total_weight > box.max_weight:
            result = f"REJECTED by weight: {_fmt(total_weight)} > {_fmt(box.max_weight)} kg"
            candidate_rows.append((box.code, _fmt(box.external_volume), usable_label,
                                   _fmt(usable_cap), result))
            continue

        if total_volume > usable_cap:
            result = f"REJECTED by volume: {_fmt(total_volume)} > {_fmt(usable_cap)} mm^3"
            candidate_rows.append((box.code, _fmt(box.external_volume), usable_label,
                                   _fmt(usable_cap), result))
            continue

        if len(items) != 1:
            candidate_rows.append((
                box.code,
                _fmt(box.external_volume),
                usable_label,
                _fmt(usable_cap),
                "PASSED screen; evaluated during 3D search",
            ))
            continue

        item = items[0]
        fitting = []
        orientation_rows: list[tuple[str, ...]] = []
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
                orientation_rows.append((label, f"REJECTED: {', '.join(failures)}"))
            else:
                orientation_rows.append((label, "FITS"))
                fitting.append(orientation)
        orientation_sections.append((box.code, orientation_rows))

        if fitting:
            result = "SELECTED: smallest feasible carton"
            candidate_rows.append((box.code, _fmt(box.external_volume), usable_label,
                                   _fmt(usable_cap), result))
            break
        else:
            result = "REJECTED by geometry: no allowed orientation fits"
            candidate_rows.append((box.code, _fmt(box.external_volume), usable_label,
                                   _fmt(usable_cap), result))

    print("\nCandidate cartons (smallest external volume first)")
    _print_table(
        ("Carton", "External mm^3", "Usable L x W x H (mm)", "Fill cap mm^3", "Result"),
        candidate_rows,
    )
    for box_code, rows in orientation_sections:
        print(f"\nOrientation checks for {box_code}")
        _print_table(("L x W x H (mm)", "Result"), rows)


def _print_plan_logs(
    plan: PackingPlan,
    items: list[PhysicalItem],
    boxes: list[Box],
) -> None:
    """Print the actual solver decisions and final item assignments."""
    item_by_id = {item.instance_id: item for item in items}
    box_by_code = {box.code: box for box in boxes}
    trace = plan.metadata.get("search_trace", [])

    print("\n3D search decisions")
    if trace:
        rows = []
        for event in trace:
            rows.append((
                str(event["item"]),
                f"{event['carton']} ({event['box']})",
                str(event["outcome"]),
                str(event["reason"]),
            ))
        _print_table(("Item", "Carton attempted", "Outcome", "Why"), rows)
    else:
        selected_plan = plan.metadata.get("selected_plan", "strategy candidate")
        carton_search = plan.metadata.get("carton_search")
        explanation = f"Selected {selected_plan}."
        if carton_search == "fixed_combinations":
            explanation += " Best mode found a feasible fixed-carton combination with fewer cartons."
        print(explanation)

    print("\nFinal validated assignments")
    assignment_rows = []
    for packed_box in plan.packed_boxes:
        box = box_by_code[packed_box.box_code]
        packed_volume = sum(
            item_by_id[placement.item_instance_id].volume
            for placement in packed_box.placements
        )
        utilization = 100.0 * packed_volume / packed_box.usable_dimensions.volume
        for placement in packed_box.placements:
            orientation = placement.orientation
            position = placement.position
            assignment_rows.append((
                placement.item_instance_id,
                f"{packed_box.instance_id} ({box.code})",
                f"{_fmt(orientation.length)} x {_fmt(orientation.width)} x {_fmt(orientation.height)}",
                f"({_fmt(position.x)}, {_fmt(position.y)}, {_fmt(position.z)})",
                f"{_fmt(utilization)}% carton fill",
            ))
    _print_table(
        ("Item", "Assigned carton", "Packed L x W x H (mm)", "XYZ position (mm)", "Carton result"),
        assignment_rows,
    )

    selected_codes = [packed_box.box_code for packed_box in plan.packed_boxes]
    unused_codes = [box.code for box in boxes if box.code not in selected_codes]
    print("\nFinal decision")
    print(f"Selected carton(s): {', '.join(selected_codes)}")
    if unused_codes:
        print(
            "Not selected: " + ", ".join(unused_codes) + ". Passing the initial screen "
            "does not prove a complete 3D packing; larger alternatives are also left unused "
            "once the strategy has a complete plan."
        )


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
    order: OrderInput,
    boxes: BoxInput,
    *,
    mode: PackingMode = "fast",
    high_item_count_threshold: int = 6,
    high_item_count_max_fill_pct: float = 70,
    max_fill_pct: float = 100,
    bin_buffer: Mapping[str, object] | Orientation = Orientation(0, 0, 6),
    max_runtime_ms: float | None = 900,
    deterministic: bool = True,
    strategy: str | None = None,
    dimension_unit: DimensionUnit = "mm",
    logs: bool = False,
    visualize: bool = False,
    visualization_kwargs: VisualizationOptions | None = None,
) -> PackingResult:
    """Pack one order into the supplied carton catalogue.

    The function normalizes and validates the input, expands item quantities,
    runs the selected packing strategy, independently validates its plan, and
    returns a :class:`PackingResult`.

    Args:
        order: Mapping with ``OrderId``/``OrderNo`` and an ``Items`` list.
            Every item supplies ``Code``, dimensions in millimetres (mm),
            weight in kg,
            ``Quantity``, and ``VerticalRotation``.
        boxes: A sequence of carton mappings, or a mapping containing
            ``Bins``/``BinsList``. Every carton supplies ``Code``, dimensions
            in millimetres (mm), and ``MaxWeight`` in kg.
        mode: Public solver mode: ``"fast"`` or ``"best"``.
        high_item_count_threshold: Physical-item count above which the stricter
            fill limit applies.
        high_item_count_max_fill_pct: Maximum usable-volume fill percentage for
            orders above ``high_item_count_threshold``.
        max_fill_pct: Blanket maximum usable-volume fill percentage.
        bin_buffer: Clearance subtracted from carton length, width, and height,
            in millimetres. Accepts an :class:`Orientation` or a mapping with
            ``length``, ``width``, and ``height`` keys.
        max_runtime_ms: Optional search budget supplied to the strategy; None disables the limit.
        deterministic: Whether the strategy must use deterministic search.
        strategy: Advanced extension hook selecting a registered custom
            strategy. When supplied, it takes precedence over ``mode``.
        dimension_unit: Canonical dimension unit, fixed to ``"mm"``. Item
            dimensions, carton dimensions, buffer values, packed coordinates,
            and visualization axes are all millimetres. Derived volumes are
            cubic millimetres (mm^3). Weight values remain kilograms (kg).
        logs: When ``True``, print the normalized pre-solver checks and carton
            screening decisions. Logging does not change the packing result.
        visualize: When ``True``, display the validated result as a 3D plot.
        visualization_kwargs: Optional camera and display arguments forwarded
            to ``visualize_result``.

    Returns:
        A validated PackingResult with carton selections, XYZ placements,
        metrics, and runtime.

    Raises:
        PackingError subclasses when input, configuration, feasibility, or a
        solver-proposed plan is invalid.
    """
    if dimension_unit != "mm":
        raise ValueError("dimension_unit is fixed to 'mm'")
    if not isinstance(logs, bool):
        raise TypeError("logs must be True or False")
    if not isinstance(visualize, bool):
        raise TypeError("visualize must be True or False")

    order_id, order_number, source_items = normalize_order(order)
    normalized_boxes = normalize_boxes(boxes)
    raw_config: dict[str, object] = {
        "max_fill_pct": max_fill_pct,
        "high_item_count_threshold": high_item_count_threshold,
        "high_item_count_max_fill_pct": high_item_count_max_fill_pct,
        "bin_buffer": (
            {
                "length": bin_buffer.length,
                "width": bin_buffer.width,
                "height": bin_buffer.height,
            }
            if isinstance(bin_buffer, Orientation)
            else bin_buffer
        ),
        "max_runtime_ms": max_runtime_ms,
        "deterministic": deterministic,
        "trace_enabled": logs,
    }
    if strategy is None:
        raw_config["mode"] = mode
    else:
        raw_config["strategy"] = strategy
    normalized_config = normalize_config(raw_config)
    # Validate buffers against every catalogue entry before a plugin sees the data.
    for box in normalized_boxes:
        usable_dimensions(box, normalized_config)
    physical_items = expand_items(source_items)
    ensure_individual_feasibility(physical_items, normalized_boxes, normalized_config)
    if logs:
        _print_logs(physical_items, normalized_boxes, normalized_config)
    if normalized_config.strategy in {"fast_fit", "best_fit"}:
        # Register lazily so applications and tests can still manage custom plugins.
        from .strategies import register_builtin_solvers
        register_builtin_solvers()
    solver = get_solver(normalized_config.strategy)
    prepare = getattr(solver, "prepare", None)
    if callable(prepare):
        prepare()

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
    if logs:
        _print_plan_logs(plan, physical_items, normalized_boxes)
    metrics = calculate_metrics(plan, physical_items, normalized_boxes, runtime_ms)
    result = PackingResult(
        order_id,
        order_number,
        "success",
        normalized_config.strategy,
        plan.packed_boxes,
        plan.unpacked_item_ids,
        runtime_ms,
        metrics,
        validation,
        bool(plan.metadata.get("optimality_proven", False)),
        str(plan.metadata.get("search_status", "heuristic")),
    )
    if visualize:
        from .visualize import visualize_result

        visualize_result(result, **dict(visualization_kwargs or {}))
    return result
