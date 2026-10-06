import pytest

from bin_packing_3d import solve_order


def test_trace_proves_volume_then_geometry_then_smallest_feasible_box(capsys):
    order = {
        "OrderId": 797,
        "Items": [{
            "Code": "5", "Length": 330, "Width": 215, "Height": 80,
            "Weight": 1.4167, "Quantity": 1, "VerticalRotation": 1,
        }],
    }
    boxes = [
        {"Code": "Box9", "Length": 440, "Width": 345, "Height": 280, "MaxWeight": 20},
        {"Code": "Box4", "Length": 340, "Width": 260, "Height": 150, "MaxWeight": 20},
        {"Code": "Box3", "Length": 270, "Width": 180, "Height": 180, "MaxWeight": 20},
        {"Code": "Box2", "Length": 220, "Width": 170, "Height": 115, "MaxWeight": 20},
    ]

    result = solve_order(order, boxes, strategy="fast_fit", logs=True)
    output = capsys.readouterr().out

    assert result.packed_boxes[0].box_code == "Box4"
    assert "Physical items" in output and "1" in output
    assert "Total item volume" in output and "5,676,000 mm^3" in output
    assert output.index("Box2") < output.index("Box3") < output.index("Box4")
    assert "REJECTED by volume" in output
    assert "REJECTED by geometry: no allowed orientation fits" in output
    assert "SELECTED: smallest feasible carton" in output
    assert "Final validated assignments" in output
    assert "5#1" in output
    assert "carton-1 (Box4)" in output
    assert "Not selected: Box2, Box3, Box9" in output


def test_logs_explain_item_level_rejections_and_carton_assignments(capsys):
    order = {
        "Items": [{
            "Code": "A", "Length": 5, "Width": 6, "Height": 6,
            "Weight": 1, "Quantity": 2, "VerticalRotation": 0,
        }],
    }
    boxes = [
        {"Code": "Tiny", "Length": 4, "Width": 7, "Height": 7, "MaxWeight": 20},
        {"Code": "Small", "Length": 6, "Width": 6, "Height": 6, "MaxWeight": 20},
    ]

    result = solve_order(
        order,
        boxes,
        strategy="fast_fit",
        bin_buffer={"height": 0},
        logs=True,
    )
    output = capsys.readouterr().out

    assert result.metrics.box_count == 2
    assert "3D search decisions" in output
    assert "3D geometry:" in output
    assert "fill limit:" in output
    assert "best-scoring new carton and 3D placement" in output
    assert "Final validated assignments" in output
    assert "A#1" in output and "carton-1 (Small)" in output
    assert "A#2" in output and "carton-2 (Small)" in output
