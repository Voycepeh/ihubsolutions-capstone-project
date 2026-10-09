"""Fast mode: deterministic greedy 3D packing heuristic."""
from __future__ import annotations

from ..models import Box, PackedBox, PackingConfig, PackingPlan, PhysicalItem
from ..placement import (
    feasible_placements,
    placement_envelope_volume,
    placement_rejection_reason,
)
from ..rules import usable_dimensions


class FastFitSolver:
    """Return a deterministic greedy 3D packing without carton-count search."""

    name = "fast_fit"

    def solve(self, items: list[PhysicalItem], boxes: list[Box], config: PackingConfig) -> PackingPlan:
        """Return a single greedy packing candidate."""
        # Fast is deliberately a single greedy pass. Carton-count search belongs
        # to Best; avoid combinatorial re-packing in the latency-first mode.
        baseline = self._build_candidate(items, boxes, config)
        baseline.metadata.update({
            "selected_plan": "fast_heuristic_baseline",
            "optimality_proven": False,
            "search_status": "heuristic",
        })
        return baseline

    def _build_candidate(
        self,
        items: list[PhysicalItem],
        boxes: list[Box],
        config: PackingConfig,
    ) -> PackingPlan:
        """Build the greedy tighter-placement candidate."""
        item_by_id = {item.instance_id: item for item in items}
        # Large-first ordering reduces fragmentation while remaining deterministic.
        # Large items are placed first because they have fewer viable spaces and
        # are more likely to cause fragmentation if deferred.
        ordered = sorted(items, key=lambda i: (-i.volume, -max(
            i.source_item.length, i.source_item.width, i.source_item.height
        ), i.instance_id))
        opened: list[tuple[PackedBox, Box]] = []
        trace: list[dict[str, object]] = []

        for item in ordered:
            # Score every feasible placement in every carton already opened.
            existing = []
            for box_index, (packed_box, box) in enumerate(opened):
                feasible = feasible_placements(item, packed_box, box, item_by_id, config)
                if not feasible and config.trace_enabled:
                    trace.append({
                        "item": item.instance_id,
                        "carton": packed_box.instance_id,
                        "box": box.code,
                        "outcome": "REJECTED",
                        "reason": placement_rejection_reason(
                            item, packed_box, box, item_by_id, config
                        ),
                    })
                for candidate in feasible:
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
            # Prefer an already-open carton whenever any valid placement exists.
            if existing:
                _, packed_box, candidate = min(existing, key=lambda entry: entry[0])
                packed_box.placements.append(candidate)
                if config.trace_enabled:
                    trace.append({
                        "item": item.instance_id,
                        "carton": packed_box.instance_id,
                        "box": packed_box.box_code,
                        "outcome": "PLACED",
                        "reason": "best-scoring feasible position among already-open cartons",
                        "placement": candidate,
                    })
                continue

            # If a new carton is required, score every feasible catalogue option.
            # No open carton works, so evaluate every carton type and choose the
            # smallest feasible external carton with a valid 3D placement.
            new_options = []
            for box in boxes:
                instance_id = f"carton-{len(opened) + 1}"
                packed_box = PackedBox(box.code, instance_id, usable_dimensions(box, config))
                candidates = feasible_placements(item, packed_box, box, item_by_id, config)
                if not candidates and config.trace_enabled:
                    trace.append({
                        "item": item.instance_id,
                        "carton": instance_id,
                        "box": box.code,
                        "outcome": "REJECTED",
                        "reason": placement_rejection_reason(
                            item, packed_box, box, item_by_id, config
                        ),
                    })
                for candidate in candidates:
                    remaining = packed_box.usable_dimensions.volume - item.volume
                    # New-carton objective: smallest feasible external carton first.
                    score = (box.external_volume, remaining, box.code)
                    new_options.append((score, packed_box, box, candidate))
            if not new_options:
                return PackingPlan([p for p, _ in opened], [item.instance_id],
                                   {"item_order": "volume_desc", "search_trace": trace})
            _, packed_box, box, candidate = min(new_options, key=lambda entry: entry[0])
            packed_box.placements.append(candidate)
            opened.append((packed_box, box))
            if config.trace_enabled:
                trace.append({
                    "item": item.instance_id,
                    "carton": packed_box.instance_id,
                    "box": box.code,
                    "outcome": "PLACED",
                    "reason": "best-scoring new carton and 3D placement",
                    "placement": candidate,
                })

        return PackingPlan(
            [p for p, _ in opened],
            metadata={"item_order": "volume_desc", "search_trace": trace},
        )

