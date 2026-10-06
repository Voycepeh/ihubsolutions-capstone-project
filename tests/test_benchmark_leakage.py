import copy
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "notebooks"))

from benchmark_solver_modes import benchmark  # noqa: E402


def test_reference_answer_cannot_change_solver_recommendation():
    records = json.loads(
        (ROOT / "data" / "raw" / "data_samples_v2.json").read_text(
            encoding="utf-8"
        )
    )
    original = next(record for record in records if record["input"]["OrderId"] == 428)
    changed_reference = copy.deepcopy(original)
    changed_reference["output"]["Data"]["BinsPacked"] = [
        {"Code": "Box9", "UsedSpace": 1.0}
    ]
    changed_reference["latency_ms"] = 999_999

    original_row = benchmark([original])[0]
    changed_row = benchmark([changed_reference])[0]

    solver_fields = (
        "fast_boxes",
        "fast_cartons",
        "fast_external_volume_mm3",
        "best_boxes",
        "best_cartons",
        "best_external_volume_mm3",
    )
    assert {
        field: original_row[field] for field in solver_fields
    } == {
        field: changed_row[field] for field in solver_fields
    }
    assert original_row["ihub_boxes"] != changed_row["ihub_boxes"]
    assert original_row["ihub_latency_ms"] != changed_row["ihub_latency_ms"]
