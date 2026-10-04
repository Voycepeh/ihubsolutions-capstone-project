from bin_packing_3d.models import (
    Box, Orientation, PackedBox, PackingConfig, PackingPlan,
    PhysicalItem, Item, Placement, Position,
)
from bin_packing_3d.placement.geometry import feasible_placements, support_pct
from bin_packing_3d.validate import validate_plan


def _physical(code: str, length: float, width: float, height: float) -> PhysicalItem:
    return PhysicalItem(
        f"{code}#1",
        Item(code, length, width, height, 1.0, 1, False),
    )


def test_floor_placement_has_full_support():
    candidate = Placement("A#1", "A", "carton-1", Orientation(5, 5, 5), Position(3, 4, 0))
    assert support_pct(candidate, []) == 100.0


def test_floating_candidate_is_rejected():
    base = Placement("BASE#1", "BASE", "carton-1", Orientation(5, 5, 5), Position(0, 0, 0))
    floating = Placement("TOP#1", "TOP", "carton-1", Orientation(5, 5, 5), Position(5, 0, 5))
    assert support_pct(floating, [base]) == 0.0


def test_fully_supported_stack_is_accepted():
    base = Placement("BASE#1", "BASE", "carton-1", Orientation(10, 10, 5), Position(0, 0, 0))
    top = Placement("TOP#1", "TOP", "carton-1", Orientation(10, 10, 5), Position(0, 0, 5))
    assert support_pct(top, [base]) == 100.0


def test_partial_support_fails_default_100_percent_rule():
    base = Placement("BASE#1", "BASE", "carton-1", Orientation(5, 10, 5), Position(0, 0, 0))
    top = Placement("TOP#1", "TOP", "carton-1", Orientation(10, 10, 5), Position(0, 0, 5))
    assert support_pct(top, [base]) == 50.0


def test_validator_rejects_floating_plan():
    base_item = _physical("BASE", 5, 5, 5)
    top_item = _physical("TOP", 5, 5, 5)
    box = Box("B", 20, 20, 20, 20)
    packed = PackedBox(
        "B", "carton-1", Orientation(20, 20, 20),
        [
            Placement("BASE#1", "BASE", "carton-1", Orientation(5, 5, 5), Position(0, 0, 0)),
            Placement("TOP#1", "TOP", "carton-1", Orientation(5, 5, 5), Position(10, 0, 5)),
        ],
    )
    result = validate_plan(
        PackingPlan([packed]),
        [base_item, top_item],
        [box],
        PackingConfig(bin_buffer=Orientation(0, 0, 0)),
    )
    assert not result.valid
    assert "support" in {error.code for error in result.errors}


def test_feasible_placements_never_returns_floating_candidate():
    base_item = _physical("BASE", 5, 5, 5)
    top_item = _physical("TOP", 5, 5, 5)
    box = Box("B", 20, 20, 20, 20)
    packed = PackedBox(
        "B", "carton-1", Orientation(20, 20, 20),
        [Placement("BASE#1", "BASE", "carton-1", Orientation(5, 5, 5), Position(0, 0, 0))],
    )
    candidates = feasible_placements(
        top_item, packed, box, {"BASE#1": base_item, "TOP#1": top_item},
        PackingConfig(bin_buffer=Orientation(0, 0, 0)),
    )
    assert candidates
    assert all(
        candidate.position.z == 0 or support_pct(candidate, packed.placements) == 100.0
        for candidate in candidates
    )
