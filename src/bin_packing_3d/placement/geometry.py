"""Shared axis-aligned 3D placement primitives used by packing strategies."""
from __future__ import annotations

from ..models import Box, Orientation, PackedBox, PackingConfig, PhysicalItem, Placement, Position
from ..rules import allowed_orientations, effective_max_fill_pct


_EPSILON = 1e-9


def _overlap(a: Placement, b: Placement) -> bool:
    """Return true when two cuboid interiors overlap; touching is allowed."""
    return not (
        a.position.x + a.orientation.length <= b.position.x + _EPSILON
        or b.position.x + b.orientation.length <= a.position.x + _EPSILON
        or a.position.y + a.orientation.width <= b.position.y + _EPSILON
        or b.position.y + b.orientation.width <= a.position.y + _EPSILON
        or a.position.z + a.orientation.height <= b.position.z + _EPSILON
        or b.position.z + b.orientation.height <= a.position.z + _EPSILON
    )


def candidate_positions(packed_box: PackedBox) -> tuple[Position, ...]:
    """Return deterministic exposed corners worth trying next.

    The origin is always a candidate. Every placed cuboid contributes one
    point after its length, width, and height. Points are tried bottom first,
    then front to back, then left to right.
    """
    points = {(0.0, 0.0, 0.0)}
    for placed in packed_box.placements:
        p, o = placed.position, placed.orientation
        points.add((p.x + o.length, p.y, p.z))
        points.add((p.x, p.y + o.width, p.z))
        points.add((p.x, p.y, p.z + o.height))
    return tuple(Position(*point) for point in sorted(points, key=lambda p: (p[2], p[1], p[0])))


def support_pct(candidate: Placement, placements: list[Placement]) -> float:
    """Return the percentage of the candidate base supported from below.

    A floor placement has 100% support. For a stacked placement, only items
    whose top face exactly meets the candidate bottom face can provide support.
    The overlap of their XY footprints is measured against the candidate base.
    Overlapping support rectangles are merged exactly so support is never
    double-counted.
    """
    if candidate.position.z <= _EPSILON:
        return 100.0

    x1 = candidate.position.x
    x2 = x1 + candidate.orientation.length
    y1 = candidate.position.y
    y2 = y1 + candidate.orientation.width
    rectangles = []
    for placed in placements:
        top = placed.position.z + placed.orientation.height
        if abs(top - candidate.position.z) > _EPSILON:
            continue
        px1, px2 = placed.position.x, placed.position.x + placed.orientation.length
        py1, py2 = placed.position.y, placed.position.y + placed.orientation.width
        ox1, ox2 = max(x1, px1), min(x2, px2)
        oy1, oy2 = max(y1, py1), min(y2, py2)
        if ox2 > ox1 + _EPSILON and oy2 > oy1 + _EPSILON:
            rectangles.append((ox1, ox2, oy1, oy2))

    if not rectangles:
        return 0.0

    xs = sorted({x for rect in rectangles for x in rect[:2]})
    supported_area = 0.0
    for left, right in zip(xs, xs[1:]):
        intervals = sorted(
            (bottom, top)
            for rx1, rx2, bottom, top in rectangles
            if rx1 < right - _EPSILON and rx2 > left + _EPSILON
        )
        if not intervals:
            continue
        merged_y = 0.0
        start, end = intervals[0]
        for next_start, next_end in intervals[1:]:
            if next_start <= end + _EPSILON:
                end = max(end, next_end)
            else:
                merged_y += end - start
                start, end = next_start, next_end
        merged_y += end - start
        supported_area += (right - left) * merged_y

    base_area = candidate.orientation.length * candidate.orientation.width
    return 100.0 * supported_area / base_area


def feasible_placements(
    item: PhysicalItem,
    packed_box: PackedBox,
    box: Box,
    item_by_id: dict[str, PhysicalItem],
    config: PackingConfig,
) -> list[Placement]:
    """Enumerate valid XYZ/orientation placements for one item in one carton.

    Cheap carton-wide constraints are checked first: weight and configured
    fill cap. We then try every candidate point and allowed orientation,
    rejecting placements that cross a usable boundary or overlap an item
    already in the carton.
    """
    current_weight = sum(item_by_id[p.item_instance_id].weight for p in packed_box.placements)
    if current_weight + item.weight > box.max_weight + _EPSILON:
        return []
    current_volume = sum(item_by_id[p.item_instance_id].volume for p in packed_box.placements)
    fill_cap = packed_box.usable_dimensions.volume * effective_max_fill_pct(len(item_by_id), config) / 100.0
    if current_volume + item.volume > fill_cap + _EPSILON:
        return []

    feasible: list[Placement] = []
    for position in candidate_positions(packed_box):
        for orientation in allowed_orientations(item):
            if (
                position.x + orientation.length > packed_box.usable_dimensions.length + _EPSILON
                or position.y + orientation.width > packed_box.usable_dimensions.width + _EPSILON
                or position.z + orientation.height > packed_box.usable_dimensions.height + _EPSILON
            ):
                continue
            candidate = Placement(item.instance_id, item.code, packed_box.instance_id, orientation, position)
            if any(_overlap(candidate, placed) for placed in packed_box.placements):
                continue
            if support_pct(candidate, packed_box.placements) + _EPSILON < config.min_support_pct:
                continue
            feasible.append(candidate)
    return feasible


def placement_envelope_volume(packed_box: PackedBox, candidate: Placement) -> float:
    """Volume of the smallest origin-anchored cuboid enclosing placements.

    Best Fit uses this only as a deterministic tie breaker after remaining
    usable carton space. A smaller envelope keeps placements compact.
    """
    placements = [*packed_box.placements, candidate]
    max_x = max(p.position.x + p.orientation.length for p in placements)
    max_y = max(p.position.y + p.orientation.width for p in placements)
    max_z = max(p.position.z + p.orientation.height for p in placements)
    return max_x * max_y * max_z
