import pytest

from bin_packing_3d import solve_order
from bin_packing_3d.models import UnpackableItemError


BOXES = [
    {"Code": "A", "Length": 10, "Width": 10, "Height": 20, "MaxWeight": 20},
    {"Code": "B", "Length": 12, "Width": 12, "Height": 15, "MaxWeight": 20},
]


def _order(items):
    return {"OrderId": 1, "OrderNo": "T-1", "Items": items}


@pytest.mark.parametrize("strategy", ["fast_fit", "best_fit"])
def test_builtin_strategies_produce_valid_3d_plan(strategy):
    order = _order([
        {"Code": "A", "Length": 5, "Width": 5, "Height": 5, "Weight": 1,
         "Quantity": 3, "VerticalRotation": 0},
    ])
    result = solve_order(order, BOXES, strategy=strategy, bin_buffer={"height": 0})
    assert result.validation.valid
    assert result.metrics.packed_item_count == 3
    assert result.metrics.unpacked_item_count == 0


@pytest.mark.parametrize("strategy", ["fast_fit", "best_fit"])
def test_single_item_uses_smallest_feasible_external_volume_carton(strategy):
    order = _order([
        {"Code": "A", "Length": 8, "Width": 8, "Height": 8, "Weight": 1,
         "Quantity": 1, "VerticalRotation": 0},
    ])
    result = solve_order(order, BOXES, strategy=strategy)
    assert result.packed_boxes[0].box_code == "A"


def test_builtin_strategy_respects_rotation_rules():
    boxes = [{"Code": "B", "Length": 20, "Width": 10, "Height": 10, "MaxWeight": 20}]
    rotatable = _order([
        {"Code": "A", "Length": 10, "Width": 20, "Height": 10, "Weight": 1,
         "Quantity": 1, "VerticalRotation": 0},
    ])
    result = solve_order(rotatable, boxes, strategy="fast_fit", bin_buffer={"height": 0})
    assert result.validation.valid
    assert result.placements[0].orientation.length == 20
    assert result.placements[0].orientation.width == 10


def test_geometry_precheck_still_rejects_volume_only_false_positive():
    impossible = _order([
        {"Code": "A", "Length": 30, "Width": 10, "Height": 20, "Weight": 1,
         "Quantity": 1, "VerticalRotation": 1},
    ])
    with pytest.raises(UnpackableItemError) as exc:
        solve_order(
            impossible,
            [{"Code": "Cube", "Length": 20, "Width": 20, "Height": 20, "MaxWeight": 20}],
            strategy="best_fit",
            bin_buffer={"height": 0},
        )
    assert "No carton can contain" in str(exc.value)


@pytest.mark.parametrize(("mode", "strategy"), [("fast", "fast_fit"), ("best", "best_fit")])
def test_public_modes_select_expected_builtin_strategy(mode, strategy):
    order = _order([
        {"Code": "A", "Length": 5, "Width": 5, "Height": 5, "Weight": 1,
         "Quantity": 2, "VerticalRotation": 0},
    ])
    result = solve_order(order, BOXES, mode=mode, bin_buffer={"height": 0})
    assert result.strategy == strategy
    assert result.validation.valid


def test_best_mode_never_returns_a_worse_objective_than_fast_mode():
    order = _order([
        {"Code": "large", "Length": 8, "Width": 8, "Height": 8, "Weight": 1,
         "Quantity": 2, "VerticalRotation": 1},
        {"Code": "small", "Length": 4, "Width": 4, "Height": 4, "Weight": 1,
         "Quantity": 3, "VerticalRotation": 1},
    ])
    fast = solve_order(order, BOXES, mode="fast", bin_buffer={"height": 0})
    best = solve_order(order, BOXES, mode="best", bin_buffer={"height": 0})

    assert best.objective <= fast.objective
    assert best.packed_boxes


def test_best_prioritizes_one_larger_carton_over_two_smaller_cartons():
    boxes = [
        {"Code": "Small", "Length": 5, "Width": 6, "Height": 6, "MaxWeight": 20},
        {"Code": "Large", "Length": 10, "Width": 10, "Height": 6, "MaxWeight": 20},
    ]
    order = _order([
        {"Code": "item", "Length": 5, "Width": 6, "Height": 6, "Weight": 1,
         "Quantity": 2, "VerticalRotation": 0},
    ])

    fast = solve_order(order, boxes, mode="fast", bin_buffer={"height": 0})
    best = solve_order(order, boxes, mode="best", bin_buffer={"height": 0})

    assert len(fast.packed_boxes) in {1, 2}
    assert [box.box_code for box in best.packed_boxes] == ["Large"]
    assert best.optimality_proven
    assert best.search_status == "optimal"


def test_exact_best_repairs_confirmed_greedy_geometry_trap():
    boxes = [
        {"Code": "Box2", "Length": 270, "Width": 170, "Height": 115, "MaxWeight": 20},
        {"Code": "Box4", "Length": 340, "Width": 260, "Height": 150, "MaxWeight": 20},
        {"Code": "Box5", "Length": 340, "Width": 260, "Height": 235, "MaxWeight": 20},
        {"Code": "Box6", "Length": 340, "Width": 260, "Height": 280, "MaxWeight": 20},
        {"Code": "Box8", "Length": 290, "Width": 180, "Height": 280, "MaxWeight": 20},
        {"Code": "Box9", "Length": 440, "Width": 345, "Height": 280, "MaxWeight": 20},
    ]
    order = _order([
        {"Code": "188", "Length": 70, "Width": 70, "Height": 142,
         "Weight": 0.4167, "Quantity": 1, "VerticalRotation": 0},
        {"Code": "232", "Length": 189, "Width": 70, "Height": 185,
         "Weight": 0.38, "Quantity": 1, "VerticalRotation": 1},
        {"Code": "9", "Length": 255, "Width": 40, "Height": 192,
         "Weight": 1.25, "Quantity": 1, "VerticalRotation": 1},
        {"Code": "136", "Length": 80, "Width": 80, "Height": 210,
         "Weight": 0.65, "Quantity": 1, "VerticalRotation": 0},
        {"Code": "62", "Length": 65, "Width": 65, "Height": 125,
         "Weight": 0.2321, "Quantity": 1, "VerticalRotation": 1},
    ])

    fast = solve_order(order, boxes, mode="fast")
    best = solve_order(order, boxes, mode="best")

    assert [box.box_code for box in fast.packed_boxes] == ["Box4", "Box8"]
    assert [box.box_code for box in best.packed_boxes] == ["Box8"]
    assert best.validation.valid
    assert best.optimality_proven


def test_best_reports_time_limit_when_proof_budget_is_exhausted():
    order = _order([
        {"Code": "A", "Length": 5, "Width": 5, "Height": 5, "Weight": 1,
         "Quantity": 2, "VerticalRotation": 0},
    ])

    result = solve_order(
        order,
        BOXES,
        mode="best",
        bin_buffer={"height": 0},
        max_runtime_ms=0.000001,
    )

    assert result.validation.valid
    assert not result.optimality_proven
    assert result.search_status == "time_limit"
