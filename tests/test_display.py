from bin_packing_3d import register_solver, result_tables, solve_order
from tests.helpers import RowSolver


def test_result_tables_expose_summary_and_mm_placements():
    register_solver("display-test", RowSolver())
    result = solve_order(
        {
            "Items": [{
                "Code": "A", "Length": 50, "Width": 40, "Height": 30,
                "Weight": 1, "Quantity": 1, "VerticalRotation": 0,
            }],
        },
        [{"Code": "B", "Length": 100, "Width": 100, "Height": 100, "MaxWeight": 10}],
        strategy="display-test",
        bin_buffer={"height": 0},
    )

    summary, placements = result_tables(result)

    assert summary.rows[0]["Status"] == "success"
    assert summary.rows[0]["Total cartons"] == 1
    assert summary.rows[0]["Carton number"] == 1
    assert summary.rows[0]["Box type"] == "B"
    assert summary.rows[0]["Item qty"] == 1
    assert summary.rows[0]["Usable fill (%)"] == 6
    assert summary.rows[0]["Runtime (ms)"] == round(result.runtime_ms, 3)
    assert placements.rows[0]["Item"] == "A#1"
    assert placements.rows[0]["Packed L (mm)"] == 50
    assert placements.rows[0]["Volume (mm^3)"] == 60_000
    assert "<table" in placements._repr_html_()
