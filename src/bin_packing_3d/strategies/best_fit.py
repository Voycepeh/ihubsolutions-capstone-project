"""Deterministic Best Fit 3D packing strategy."""
from __future__ import annotations

from ..models import Box, PackedBox, PackingConfig, PackingPlan, PhysicalItem
from ..placement import feasible_placements, placement_envelope_volume
from ..rules import usable_dimensions


class BestFitSolver:
    """Evaluate feasible choices and keep the tightest deterministic fit.

    Unlike First Fit, this strategy does not stop at the first feasible
    placement. It scores every feasible placement in every open carton.
    Remaining usable space is the primary score; placement compactness and
    coordinates provide stable tie breaking.
    """

    name = "best_fit"

    def solve(self, items: list[PhysicalItem], boxes: list[Box], config: PackingConfig) -> PackingPlan:
        """Build a complete Best Fit plan using shared 3D feasibility checks."""
        item_by_id = {item.instance_id: item for item in items}
        # Use the same item ordering as First Fit so strategy is the main variable.
        ordered = sorted(items, key=lambda i: (-i.volume, -max(
            i.source_item.length, i.source_item.width, i.source_item.height
        ), i.instance_id))
        opened: list[tuple[PackedBox, Box]] = []

        for item in ordered:
            # Score every feasible placement in every carton already opened.
            existing = []
            for box_index, (packed_box, box) in enumerate(opened):
                for candidate in feasible_placements(item, packed_box, box, item_by_id, config):
                    remaining = packed_box.usable_dimensions.volume - sum(
                        item_by_id[p.item_instance_id].volume for p in packed_box.placements
                    ) - item.volume
                    score = (
                        remaining,
                        placement_envelope_volume(packed_box, candidate),
                        candidate.position.z, candidate.position.y, candidate.position.x,
                        candidate.orientation.height, candidate.orientation.width, candidate.orientation.length,
                        box_index,
                    )
                    existing.append((score, packed_box, candidate))
            if existing:
                _, packed_box, candidate = min(existing, key=lambda entry: entry[0])
                packed_box.placements.append(candidate)
                continue

            # If a new carton is required, score every feasible catalogue option.
            new_options = []
            for box in boxes:
                instance_id = f"carton-{len(opened) + 1}"
                packed_box = PackedBox(box.code, instance_id, usable_dimensions(box, config))
                candidates = feasible_placements(item, packed_box, box, item_by_id, config)
                for candidate in candidates:
                    remaining = packed_box.usable_dimensions.volume - item.volume
                    # New-carton objective: smallest feasible external carton first.\n                    score = (box.external_volume, remaining, box.code)
                    new_options.append((score, packed_box, box, candidate))
            if not new_options:
                return PackingPlan([p for p, _ in opened], [item.instance_id],
                                   {"item_order": "volume_desc"})
            _, packed_box, box, candidate = min(new_options, key=lambda entry: entry[0])
            packed_box.placements.append(candidate)
            opened.append((packed_box, box))

        return PackingPlan([p for p, _ in opened], metadata={"item_order": "volume_desc"})
