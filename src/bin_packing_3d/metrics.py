"""Common measurements calculated independently of solver implementations."""
from __future__ import annotations

from .models import Box, BoxMetrics, PackingMetrics, PackingPlan, PhysicalItem


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
