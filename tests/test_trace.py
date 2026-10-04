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

    result = solve_order(order, boxes, {"strategy": "first_fit"}, trace=True)
    output = capsys.readouterr().out

    assert result.packed_boxes[0].box_code == "Box4"
    assert "Total item count: 1" in output
    assert "Total item volume: 5.676e+06 mm^3" in output
    assert output.index("Box2:") < output.index("Box3:") < output.index("Box4:")
    assert "REJECTED by volume" in output
    assert "REJECTED by geometry: no allowed orientation fits Box3" in output
    assert "SELECTED: Box4 is the smallest feasible carton by external volume" in output
    assert "Box9:" not in output
