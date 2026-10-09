"""Fast mode: deterministic greedy 3D packing heuristic."""
from __future__ import annotations

from itertools import combinations_with_replacement
from math import ceil

from ..models import Box, PackedBox, PackingConfig, PackingPlan, PhysicalItem
from ..placement import (
    feasible_placements,
    placement_envelope_volume,
    placement_rejection_reason,
)
from ..rules import effective_max_fill_pct, item_fits_box, usable_dimensions


class FastFitSolver:
    """Return a deterministic greedy 3D packing without carton-count search."""

    name = "fast_fit"

    def solve(self, items: list[PhysicalItem], boxes: list[Box], config: PackingConfig) -> PackingPlan:
        """Greedy baseline plus a few promising fewer-carton attempts."""
        baseline = self._build_candidate(items, boxes, config)
        baseline.metadata.update({
            "selected_plan": "fast_heuristic_baseline",
            "optimality_proven": False,
            "search_status": "heuristic",
        })
        count = len(items)
        attempts = 3
        if len(baseline.packed_boxes) <= 1 or baseline.unpacked_item_ids:
            return baseline
        total_volume = sum(item.volume for item in items)
        total_weight = sum(item.weight for item in items)
        fill = effective_max_fill_pct(count, config) / 100.0
        item_by_id = {item.instance_id: item for item in items}
        ordered = sorted(items, key=lambda i: (
            -i.volume,
            -max(i.source_item.length, i.source_item.width, i.source_item.height),
            i.instance_id,
        ))
        box_volume = {box.code: box.external_volume for box in boxes}
        best = baseline
        tried = 0
        for carton_count in range(1, len(baseline.packed_boxes)):
            if tried >= attempts:
                break
            # Prefer smaller overall carton volume. Avoid materializing all
            # combinations, which was a major source of scaling overhead.
            for choice in combinations_with_replacement(boxes, carton_count):
                if tried >= attempts:
                    break
                dims = [usable_dimensions(box, config) for box in choice]
                if sum(dim.volume * fill for dim in dims) < total_volume:
                    continue
                if sum(box.max_weight for box in choice) < total_weight:
                    continue
                if not all(any(item_fits_box(item, box, config) for box in choice) for item in items):
                    continue
                tried += 1
                opened = [
                    (PackedBox(box.code, f"carton-{index + 1}", dim), box)
                    for index, (box, dim) in enumerate(zip(choice, dims))
                ]
                complete = True
                for item in ordered:
                    options = []
                    for box_index, (packed_box, box) in enumerate(opened):
                        for placement in feasible_placements(item, packed_box, box, item_by_id, config):
                            options.append((
                                placement_envelope_volume(packed_box, placement),
                                box_index,
                                placement.position.z,
                                placement.position.y,
                                placement.position.x,
                                placement.orientation.height,
                                placement.orientation.width,
                                placement.orientation.length,
                                packed_box.box_code,
                                packed_box.instance_id,
                                item.instance_id,
                                packed_box,
                                placement,
                            ))
                    if not options:
                        complete = False
                        break
                    *_, selected_box, placement = min(options, key=lambda entry: entry[:-2])
                    selected_box.placements.append(placement)
                if complete:
                    candidate = PackingPlan([packed for packed, _ in opened if packed.placements])
                    def score(plan: PackingPlan) -> tuple[int, float]:
                        volumes = [box_volume[packed.box_code] for packed in plan.packed_boxes]
                        return (len(volumes), sum(volumes))
                    if score(candidate) < score(best):
                        best = candidate
                        best.metadata.update({
                            "selected_plan": "bounded_carton_improvement",
                            "optimality_proven": False,
                            "search_status": "heuristic",
                        })
        best.metadata["improvement_attempts"] = tried
        return best

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

        for item_index, item in enumerate(ordered):
            remaining_items = ordered[item_index:]
            remaining_volume = sum(pending.volume for pending in remaining_items)
            remaining_weight = sum(pending.weight for pending in remaining_items)
            remaining_fill = effective_max_fill_pct(len(items), config) / 100.0
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
            # No open carton works. Rank carton types by how many would be
            # needed for the remaining order, then by external carton volume.
            # Volume/weight are only screening estimates: placements still
            # require full 3D feasibility checks.
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
                    capacity = packed_box.usable_dimensions.volume * remaining_fill
                    projected_by_volume = ceil(remaining_volume / capacity) if capacity > 0 else len(remaining_items)
                    projected_by_weight = (ceil(remaining_weight / box.max_weight)
                                           if box.max_weight > 0 else len(remaining_items))
                    projected_cartons = max(projected_by_volume, projected_by_weight)
                    # Prefer fewer estimated cartons; among equally promising
                    # options choose the smaller external carton.
                    score = (projected_cartons, box.external_volume, remaining, box.code)
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
                    "reason": "remaining-order capacity estimate and valid 3D placement",
                    "placement": candidate,
                })

        return PackingPlan(
            [p for p, _ in opened],
            metadata={"item_order": "volume_desc", "search_trace": trace},
        )

