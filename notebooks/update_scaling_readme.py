"""Update the README's synthetic scaling conclusions from the latest 240-run CSV."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
folder = ROOT / "benchmark_results/solver_scaling_current"
with (folder / "raw_results.csv").open(newline="", encoding="utf-8") as stream:
    raw = list(csv.DictReader(stream))
with (folder / "summary.csv").open(newline="", encoding="utf-8") as stream:
    summary = list(csv.DictReader(stream))
assert len(raw) == 240, f"Expected 240 runs, got {len(raw)}"
assert len({(r["items"], r["box_types"], r["repeat"], r["mode"]) for r in raw}) == 240
for filename in ("solver_scaling_fast_heatmap.svg", "solver_scaling_best_heatmap.svg", "solver_scaling_best_breakdown.svg"):
    assert (folder / filename).is_file(), filename
selected = {r["mode"]: r for r in summary if int(r["items"]) == 100 and int(r["box_types"]) == 20}
assert set(selected) == {"fast", "best"}
fast = selected["fast"]
best = selected["best"]
text = ROOT.joinpath("README.md").read_text(encoding="utf-8")
start = text.index("**Conclusion:** Fast matched Best's median carton counts")
end = text.index("\n\n### Fast vs Best vs iHub:", start)
new = (
    "**Conclusion (refreshed uncapped 240-run simulation):** At 100 items and 20 carton types, "
    f"Fast's median runtime was **{float(fast['median_runtime_ms']):,.1f} ms** "
    f"and Best's was **{float(best['median_runtime_ms']):,.1f} ms**. "
    "These are synthetic, uncapped runs, not measurements of the 5-second production Best budget. "
    "The objective is fewest cartons, then lowest total external carton volume. "
    "The charts and figures are generated from the saved benchmark results, "
    "not estimated from the previous solver version."
)
text = text[:start] + new + text[end:]
ROOT.joinpath("README.md").write_text(text, encoding="utf-8")
print("Updated README from 240 validated benchmark rows")
