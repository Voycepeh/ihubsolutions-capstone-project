import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from bin_packing_3d import register_solver, solve_order, visualize_result
from bin_packing_3d import visualize as visualize_module
from tests.helpers import RowSolver


def test_visualize_result_draws_validated_carton_and_items():
    register_solver("visual-test", RowSolver())
    order = {
        "Items": [
            {
                "Code": "A", "Length": 5, "Width": 5, "Height": 5,
                "Weight": 1, "Quantity": 2, "VerticalRotation": 0,
            }
        ]
    }
    boxes = [{"Code": "B", "Length": 20, "Width": 10, "Height": 10, "MaxWeight": 10}]
    result = solve_order(
        order,
        boxes,
        strategy="visual-test",
        bin_buffer={"height": 0},
    )

    figure, axes = visualize_result(result, show=False)

    assert len(axes) == 1
    assert axes[0].get_title().startswith("Packed Box 1 — type B")
    assert len(axes[0].collections) == 2
    assert axes[0].elev == 25
    assert axes[0].azim == 135
    plt.close(figure)


def test_solve_order_can_request_visualization(monkeypatch):
    register_solver("visual-option-test", RowSolver())
    calls = []

    def fake_visualize(result, **kwargs):
        calls.append((result.validation.valid, kwargs))

    monkeypatch.setattr(visualize_module, "visualize_result", fake_visualize)
    result = solve_order(
        {
            "Items": [
                {
                    "Code": "A", "Length": 5, "Width": 5, "Height": 5,
                    "Weight": 1, "Quantity": 1, "VerticalRotation": 0,
                }
            ]
        },
        [{"Code": "B", "Length": 10, "Width": 10, "Height": 10, "MaxWeight": 10}],
        strategy="visual-option-test",
        bin_buffer={"height": 0},
        visualize=True,
        visualization_kwargs={"show": False, "azimuth": 210},
    )

    assert result.validation.valid
    assert calls == [(True, {"show": False, "azimuth": 210})]
