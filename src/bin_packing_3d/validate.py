"""Independent validation of solver-proposed packing plans."""
from __future__ import annotations

from collections import Counter

from .models import (
    Box, PackingConfig, PackingPlan, PhysicalItem, Placement, ValidationError, ValidationResult,
)
from .rules import allowed_orientations, fill_cap_applies, usable_dimensions

_EPSILON = 1e-9


def _overlap(a: Placement, b: Placement) -> bool:
    """Return true only when cuboid interiors intersect; touching is valid."""
    return not (
        a.position.x + a.orientation.length <= b.position.x + _EPSILON
        or b.position.x + b.orientation.length <= a.position.x + _EPSILON
        or a.position.y + a.orientation.width <= b.position.y + _EPSILON
        or b.position.y + b.orientation.width <= a.position.y + _EPSILON
        or a.position.z + a.orientation.height <= b.position.z + _EPSILON
        or b.position.z + b.orientation.height <= a.position.z + _EPSILON
    )


def validate_plan(plan: PackingPlan, items: list[PhysicalItem], boxes: list[Box], config: PackingConfig) -> ValidationResult:
    errors: list[ValidationError] = []
    item_by_id = {item.instance_id: item for item in items}
    box_by_code = {box.code: box for box in boxes}
    seen_box_ids: set[str] = set()
    placements = plan.placements
    packed_ids = [p.item_instance_id for p in placements]
    unpacked_ids = list(plan.unpacked_item_ids)

    for item_id, count in Counter(packed_ids).items():
        if count > 1:
            errors.append(ValidationError("duplicate_item", f"Physical item '{item_id}' is packed {count} times", item_id))
    for item_id, count in Counter(unpacked_ids).items():
        if count > 1:
            errors.append(ValidationError("duplicate_unpacked_item", f"Physical item '{item_id}' is listed unpacked {count} times", item_id))
    for item_id in sorted((set(packed_ids) | set(unpacked_ids)) - set(item_by_id)):
        errors.append(ValidationError("unknown_item", f"Unknown physical item '{item_id}' appears in plan", item_id))
    for item_id in sorted(set(packed_ids) & set(unpacked_ids)):
        errors.append(ValidationError("conflicting_item_state", f"Physical item '{item_id}' is both packed and unpacked", item_id))
    accounted = set(packed_ids) | set(unpacked_ids)
    for item_id in sorted(set(item_by_id) - accounted):
        errors.append(ValidationError("missing_item", f"Physical item '{item_id}' is missing from plan", item_id))

    for packed_box in plan.packed_boxes:
        box_id = packed_box.instance_id
        if box_id in seen_box_ids:
            errors.append(ValidationError("duplicate_box_id", f"Carton instance '{box_id}' appears more than once", box_instance_id=box_id))
        seen_box_ids.add(box_id)
        box = box_by_code.get(packed_box.box_code)
        if box is None:
            errors.append(ValidationError("unknown_box", f"Unknown carton type '{packed_box.box_code}'", box_instance_id=box_id))
            continue
        expected_usable = usable_dimensions(box, config)
        if packed_box.usable_dimensions != expected_usable:
            errors.append(ValidationError("usable_dimensions", f"Carton '{box_id}' usable dimensions do not match configured buffer", box_instance_id=box_id))
        packed_weight = 0.0
        packed_volume = 0.0
        for placement in packed_box.placements:
            item = item_by_id.get(placement.item_instance_id)
            if placement.box_instance_id != box_id:
                errors.append(ValidationError("box_reference", f"Placement for '{placement.item_instance_id}' references carton '{placement.box_instance_id}', not '{box_id}'", placement.item_instance_id, box_id))
            if item is None:
                continue
            if placement.item_code != item.code:
                errors.append(ValidationError("item_code", f"Placement item code '{placement.item_code}' does not match '{item.code}'", item.instance_id, box_id))
            if placement.orientation not in allowed_orientations(item):
                errors.append(ValidationError("orientation", f"Orientation for '{item.instance_id}' is not permitted", item.instance_id, box_id))
            if min(placement.position.x, placement.position.y, placement.position.z) < 0:
                errors.append(ValidationError("negative_coordinate", f"Placement for '{item.instance_id}' has a negative coordinate", item.instance_id, box_id))
            if (placement.position.x + placement.orientation.length > expected_usable.length + _EPSILON
                    or placement.position.y + placement.orientation.width > expected_usable.width + _EPSILON
                    or placement.position.z + placement.orientation.height > expected_usable.height + _EPSILON):
                errors.append(ValidationError("boundary", f"Placement for '{item.instance_id}' exceeds carton '{box_id}' usable boundary", item.instance_id, box_id))
            packed_weight += item.weight
            packed_volume += item.volume
        if packed_weight > box.max_weight + _EPSILON:
            errors.append(ValidationError("weight", f"Carton '{box_id}' packed weight {packed_weight:g} exceeds maximum {box.max_weight:g}", box_instance_id=box_id))
        if fill_cap_applies(len(items), config):
            cap = expected_usable.volume * config.bin_max_fill_pct / 100.0
            if packed_volume > cap + _EPSILON:
                errors.append(ValidationError("fill_cap", f"Carton '{box_id}' packed volume {packed_volume:g} exceeds configured cap {cap:g}", box_instance_id=box_id))
        for index, first in enumerate(packed_box.placements):
            for second in packed_box.placements[index + 1:]:
                if _overlap(first, second):
                    errors.append(ValidationError("overlap", f"Physical items '{first.item_instance_id}' and '{second.item_instance_id}' overlap in carton '{box_id}'", first.item_instance_id, box_id))
    return ValidationResult(not errors, errors)
