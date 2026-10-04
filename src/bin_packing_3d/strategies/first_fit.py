"""Deterministic First Fit 3D packing strategy."""
from __future__ import annotations

from ..models import Box, PackedBox, PackingConfig, PackingPlan, PhysicalItem
from ..placement import feasible_placements
from ..rules import usable_dimensions


class FirstFitSolver:
    """Place each item in the first feasible carton and position.

    Items are processed largest-volume first for deterministic behavior.
    Existing cartons are tried in opening order. If none works, catalogue
    cartons are tried in the normalized smallest-external-volume order.
    The first feasible candidate is accepted immediately.
    """

    name = "first_fit"

    def solve(self, items: list[PhysicalItem], boxes: list[Box], config: PackingConfig) -> PackingPlan:
        """Build a complete First Fit plan using shared 3D feasibility checks."""
        item_by_id = {item.instance_id: item for item in items}
        # Packing larger cuboids first reduces the chance of stranding them later.
        ordered = sorted(items, key=lambda i: (-i.volume, -max(
            i.source_item.length, i.source_item.width, i.source_item.height
        ), i.instance_id))
        opened: list[tuple[PackedBox, Box]] = []

        for item in ordered:
            placed = False
            # First Fit: stop as soon as an already-open carton can take the item.
            for packed_box, box in opened:
                candidates = feasible_placements(item, packed_box, box, item_by_id, config)
                if candidates:
                    packed_box.placements.append(candidates[0])
                    placed = True
                    break
            if placed:
                continue

            # No open carton worked. Try catalogue cartons smallest-volume first.
            for box in boxes:
                instance_id = f"carton-{len(opened) + 1}"
                packed_box = PackedBox(box.code, instance_id, usable_dimensions(box, config))
                candidates = feasible_placements(item, packed_box, box, item_by_id, config)
                if candidates:
                    packed_box.placements.append(candidates[0])
                    opened.append((packed_box, box))
                    placed = True
                    break
            if not placed:
                return PackingPlan([p for p, _ in opened], [item.instance_id],
                                   {"item_order": "volume_desc"})

        return PackingPlan([p for p, _ in opened], metadata={"item_order": "volume_desc"})
