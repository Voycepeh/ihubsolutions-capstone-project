"""Synchronize the README scorecard and tornado chart from the saved 2,000-order CSV."""
from __future__ import annotations

from benchmark_comparison import read_benchmark, eligible_rows, summarize
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "notebooks/artifacts/benchmark_2000_best_vs_ihub.csv"
README = ROOT / "README.md"
TORNADO = ROOT / "benchmark_results/solver_demo/fast_best_ihub_tornado.svg"
START = "### Fast vs Best vs iHub: carton recommendation quality"


def main() -> None:
    rows = read_benchmark(CSV)
    eligible = eligible_rows(rows)
    score = summarize(rows)
    reasons = ("carton", "single", "multi")
    labels = ("Number of cartons", "Smaller box (single-box orders)", "Total box volume (multi-box orders)")
    totals = {mode: {label.lower(): score[mode][label] for label in ("Better", "Same", "Worse")} for mode in ("fast", "best")}
    breakdown = {mode: {reason: {label.lower(): score[f"{mode}_reasons"][reason][label] for label in ("Better", "Worse")} for reason in reasons} for mode in ("fast", "best")}

    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    max_bar = max((breakdown[m][r][v] for m in ("fast", "best") for r in reasons for v in ("better", "worse")), default=1)
    for ax, mode in zip(axes, ("fast", "best")):
        for index, reason in enumerate(reasons):
            better = breakdown[mode][reason]["better"]
            worse = breakdown[mode][reason]["worse"]
            ax.barh(index, -better, color="#008b91", height=0.48)
            ax.barh(index, worse, color="#db783e", height=0.48)
            ax.text(-better - max_bar * .02, index, str(better), ha="right", va="center", fontsize=10)
            ax.text(worse + max_bar * .02, index, str(worse), ha="left", va="center", fontsize=10)
        ax.set_yticks(range(3), labels)
        ax.invert_yaxis()
        ax.set_title(mode.title(), loc="left", fontweight="bold")
        ax.axvline(0, color="#9aa9b5", lw=1)
        ax.set_xlim(-max_bar * 1.45, max_bar * 1.45)
        ax.spines[["top", "right", "bottom", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0)
        ax.tick_params(axis="x", bottom=False, labelbottom=False)
    fig.suptitle("Why Fast and Best win or lose against iHub", x=.08, ha="left", fontsize=16, fontweight="bold")
    fig.text(.08, .91, f"First differing objective across {len(eligible):,} policy-screened orders · counts, not percentages", fontsize=10, color="#526577")
    fig.text(.08, .875, "Teal = Better (left)     Orange = Worse (right)", fontsize=10)
    fig.text(.08, .02, f"Source: notebooks/artifacts/benchmark_2000_best_vs_ihub.csv · {len(rows)-len(eligible)} fill-cap exceptions excluded", fontsize=9, color="#526577")
    fig.subplots_adjust(left=.39, right=.93, top=.82, bottom=.10, hspace=.5)
    TORNADO.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(TORNADO, format="svg")
    plt.close(fig)

    def line(mode: str) -> str:
        t = totals[mode]
        return f"**{mode.title()}: {t['better']:,} better / {t['same']:,} same / {t['worse']:,} worse**"
    def table_row(reason: str, label: str) -> str:
        values = [breakdown[m][reason][v] for m, v in (("fast", "better"), ("fast", "worse"), ("best", "better"), ("best", "worse"))]
        return "| " + label + " | " + " | ".join(str(v) for v in values) + " |"

    section = f"""### Fast vs Best vs iHub: carton recommendation quality

![Fast and Best compared with iHub on policy-compliant orders](benchmark_results/solver_demo/fast_best_ihub_comparison.svg)

The canonical saved benchmark evaluates **{len(rows):,} orders** from v2. **{len(rows)-len(eligible):,} iHub Box9 fill-cap exceptions** are excluded, leaving **{len(eligible):,} policy-screened comparisons**. The comparison ranks **fewer cartons first**, then **lower total external carton volume** when counts tie.

- {line("fast")}
- {line("best")}

#### What drives improvements and losses

![Fast and Best differences by first differing objective](benchmark_results/solver_demo/fast_best_ihub_tornado.svg)

| First differing objective | Fast better | Fast worse | Best better | Best worse |
| --- | ---: | ---: | ---: | ---: |
{table_row("carton", "Number of cartons")}
{table_row("single", "Smaller box (single-box orders)")}
{table_row("multi", "Lower total box volume (multi-box orders)")}

Each non-equal order is counted once, against the first differing objective. A matching result means the **ranked carton objective** ties, not necessarily that carton types or item placements match. iHub's recorded recommendations are historical references, not independently verified three-dimensional packings.

[Download the 2,000-order benchmark CSV](notebooks/artifacts/benchmark_2000_best_vs_ihub.csv) · [Open the executed Solver Demo](notebooks/Solver%20Demo.ipynb)

"""
    old = README.read_text(encoding="utf-8")
    start = old.index(START)
    end = old.index("</details>", start)
    README.write_text(old[:start] + section + old[end:], encoding="utf-8")
    print(f"Updated README and tornado from {len(rows)} orders: {totals}")


if __name__ == "__main__":
    main()
