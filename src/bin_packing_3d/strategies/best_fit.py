"""Deterministic Best Fit 3D packing strategy."""
from __future__ import annotations

from itertools import combinations_with_replacement

from ..models import Box, PackedBox, PackingConfig, PackingPlan, PhysicalItem
from ..placement import (
    feasible_placements,
    placement_envelope_volume,
    placement_rejection_reason,
)
from ..rules import effective_max_fill_pct, packing_objective, usable_dimensions


class FastFitSolver:
    """Return a strong deterministic packing without exact backtracking.

    The search scores every feasible placement in every open carton, then tries
    promising fixed-carton combinations to escape the smallest-carton-first
    trap. It is the production Fast mode because it is substantially stronger
    than plain First Fit while remaining a bounded heuristic.

    This is a bounded heuristic comparison, not a proof of global optimality.
    """

    name = "fast_fit"

    def solve(self, items: list[PhysicalItem], boxes: list[Box], config: PackingConfig) -> PackingPlan:
        """Return the best candidate found by the bounded heuristic search."""
        baseline = self._build_candidate(items, boxes, config)
        candidates = [
            baseline,
            self._search_fewer_cartons(items, boxes, config, len(baseline.packed_boxes)),
        ]
        box_volume = {box.code: box.external_volume for box in boxes}

        def score(plan: PackingPlan) -> tuple[int, int, float, float]:
            volumes = [
                box_volume.get(box.box_code, float("inf")) for box in plan.packed_boxes
            ]
            return (len(plan.unpacked_item_ids), *packing_objective(volumes))

        candidate = min((plan for plan in candidates if plan is not None), key=score)
        if score(candidate) < score(baseline):
            candidate.metadata.update({
                "selected_plan": "fixed_carton_candidate",
                "optimality_proven": False,
                "search_status": "heuristic",
            })
            return candidate
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

    def _search_fewer_cartons(
        self,
        items: list[PhysicalItem],
        boxes: list[Box],
        config: PackingConfig,
        baseline_count: int,
    ) -> PackingPlan | None:
        """Try fixed carton combinations, minimizing count before volume.

        Pre-opening a combination avoids the greedy trap where selecting the
        smallest carton for the first item later forces extra cartons. The 3D
        placement within each combination remains heuristic, so Fast does not
        claim mathematical optimality.
        """
        if baseline_count <= 1:
            return None

        total_volume = sum(item.volume for item in items)
        total_weight = sum(item.weight for item in items)
        fill_fraction = effective_max_fill_pct(len(items), config) / 100.0
        ordered_items = sorted(items, key=lambda item: (
            -item.volume,
            -max(item.source_item.length, item.source_item.width, item.source_item.height),
            item.instance_id,
        ))
        item_by_id = {item.instance_id: item for item in items}

        for carton_count in range(1, baseline_count):
            combinations = sorted(
                combinations_with_replacement(boxes, carton_count),
                key=lambda choice: (
                    *packing_objective(box.external_volume for box in choice),
                    tuple(box.code for box in choice),
                ),
            )
            valid_plans: list[PackingPlan] = []
            for choice in combinations:
                usable = [usable_dimensions(box, config) for box in choice]
                if sum(dim.volume * fill_fraction for dim in usable) < total_volume:
                    continue
                if sum(box.max_weight for box in choice) < total_weight:
                    continue

                opened = [
                    (PackedBox(box.code, f"carton-{index + 1}", dimensions), box)
                    for index, (box, dimensions) in enumerate(zip(choice, usable))
                ]
                complete = True
                for item in ordered_items:
                    options = []
                    for box_index, (packed_box, box) in enumerate(opened):
                        for placement in feasible_placements(
                            item, packed_box, box, item_by_id, config
                        ):
                            used_volume = sum(
                                item_by_id[current.item_instance_id].volume
                                for current in packed_box.placements
                            )
                            options.append((
                                placement_envelope_volume(packed_box, placement),
                                packed_box.usable_dimensions.volume - used_volume - item.volume,
                                box_index,
                                placement.position.z,
                                placement.position.y,
                                placement.position.x,
                                placement.orientation.height,
                                placement.orientation.width,
                                placement.orientation.length,
                                packed_box,
                                placement,
                            ))
                    if not options:
                        complete = False
                        break
                    *_, packed_box, placement = min(options)
                    packed_box.placements.append(placement)

                if complete:
                    used = [packed_box for packed_box, _ in opened if packed_box.placements]
                    valid_plans.append(PackingPlan(
                        used,
                        metadata={
                            "item_order": "volume_desc",
                            "carton_search": "fixed_combinations",
                        },
                    ))

            if valid_plans:
                volume_by_code = {box.code: box.external_volume for box in boxes}
                return min(
                    valid_plans,
                    key=lambda plan: packing_objective(
                        volume_by_code[packed.box_code] for packed in plan.packed_boxes
                    ),
                )
        return None
