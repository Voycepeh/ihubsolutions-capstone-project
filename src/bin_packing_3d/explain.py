"""Human-readable solver tracing.

Tracing is intentionally separate from the packing strategy. It explains the
shared checks using the same normalized items, cartons, configuration, and
orientation rules that the production engine uses.
"""
from __future__ import annotations

from .models import Box, PackingConfig, PhysicalItem
from .rules import allowed_orientations, effective_max_fill_pct, usable_dimensions


def _fmt(value: float) -> str:
    """Format measurements compactly without hiding meaningful decimals."""
    return f"{value:g}"


def print_pre_solver_trace(
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
        else:
            print(f"  REJECTED by geometry: no allowed orientation fits {box.code}")
