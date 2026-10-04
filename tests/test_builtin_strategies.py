import pytest

from bin_packing_3d import solve_order


BOXES = [
    {"Code": "A", "Length": 10, "Width": 10, "Height": 20, "MaxWeight": 20},
    {"Code": "B", "Length": 12, "Width": 12, "Height": 15, "MaxWeight": 20},
]


def _order(items):
    return {"OrderId": 1, "OrderNo": "T-1", "Items": items}


@pytest.mark.parametrize("strategy", ["first_fit", "best_fit"])
def test_builtin_strategies_produce_valid_3d_plan(strategy):
    order = _order([
        {"Code": "A", "Length": 5, "Width": 5, "Height": 5, "Weight": 1,
         "Quantity": 3, "VerticalRotation": 0},
    ])
    result = solve_order(order, BOXES, {"strategy": strategy, "bin_buffer": {"height": 0}})
    assert result.validation.valid
    assert result.metrics.packed_item_count == 3
    assert result.metrics.unpacked_item_count == 0


def test_first_fit_and_best_fit_have_distinct_carton_selection_semantics():
    order = _order([
        {"Code": "A", "Length": 8, "Width": 8, "Height": 8, "Weight": 1,
         "Quantity": 1, "VerticalRotation": 0},
    ])
    first = solve_order(order, BOXES, {"strategy": "first_fit"})
    best = solve_order(order, BOXES, {"strategy": "best_fit"})
    assert first.packed_boxes[0].box_code == "A"
    assert best.packed_boxes[0].box_code == "B"


def test_builtin_strategy_respects_rotation_rules():
    boxes = [{"Code": "B", "Length": 20, "Width": 10, "Height": 10, "MaxWeight": 20}]
    rotatable = _order([
        {"Code": "A", "Length": 10, "Width": 20, "Height": 10, "Weight": 1,
         "Quantity": 1, "VerticalRotation": 0},
    ])
    result = solve_order(rotatable, boxes, {"strategy": "first_fit", "bin_buffer": {"height": 0}})
    assert result.validation.valid
    assert result.placements[0].orientation.length == 20
    assert result.placements[0].orientation.width == 10


def test_geometry_precheck_still_rejects_volume_only_false_positive():
    impossible = _order([
        {"Code": "A", "Length": 30, "Width": 10, "Height": 20, "Weight": 1,
         "Quantity": 1, "VerticalRotation": 1},
    ])
    with pytest.raises(Exception) as exc:
        solve_order(
            impossible,
            [{"Code": "Cube", "Length": 20, "Width": 20, "Height": 20, "MaxWeight": 20}],
            {"strategy": "best_fit", "bin_buffer": {"height": 0}},
        )
    assert "No carton can contain" in str(exc.value)
