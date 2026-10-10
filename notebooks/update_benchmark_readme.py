"""Regenerate README comparison and tornado from the saved solver benchmark CSV."""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "notebooks/artifacts/benchmark_2000_best_vs_ihub.csv"
README = ROOT / "README.md"
TORNADO = ROOT / "benchmark_results/solver_demo/fast_best_ihub_tornado.svg"

def score(row, prefix):
    return (int(row[f"{prefix}_cartons"]), float(row[f"{prefix}_external_volume_mm3"]))

def main():
    with CSV.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 2000 or len({r["order_id"] for r in rows}) != 2000:
        raise ValueError("Expected 2000 unique orders")
    eligible = [r for r in rows if r["ihub_box9_over_fill_cap"].lower() != "true"]
    totals = {}
    breakdown = {}
    for mode in ("fast", "best"):
        counts = {"better": 0, "equal": 0, "worse": 0}
        reasons = {"carton_count": {"better": 0, "worse": 0}, "total_volume": {"better": 0, "worse": 0}}
        for row in eligible:
            current, reference = score(row, mode), score(row, "ihub")
            verdict = "better" if current < reference else "worse" if current > reference else "equal"
            counts[verdict] += 1
            if verdict != "equal":
                reason = "carton_count" if current[0] != reference[0] else "total_volume"
                reasons[reason][verdict] += 1
        totals[mode], breakdown[mode] = counts, reasons

    fig, ax = plt.subplots(figsize=(10, 3.7))
    labels = ["Fewer / more cartons", "Lower / higher total volume"]
    for i, reason in enumerate(("carton_count", "total_volume")):
        fast = breakdown["fast"][reason]
        best = breakdown["best"][reason]
        ax.barh(i - .17, fast["better"], height=.3, label="Fast better" if i == 0 else None)
        ax.barh(i - .17, -fast["worse"], height=.3, label="Fast worse" if i == 0 else None)
        ax.barh(i + .17, best["better"], height=.3, label="Best better" if i == 0 else None)
        ax.barh(i + .17, -best["worse"], height=.3, label="Best worse" if i == 0 else None)
    ax.set_yticks(range(2), labels)
    ax.axvline(0, color="gray", linewidth=.8)
    ax.set_xlabel("Worse than iHub ← Orders → Better than iHub")
    ax.set_title("What drives the difference? (policy-screened orders)")
    ax.legend(ncol=4, loc="lower center", bbox_to_anchor=(.5, -.4), frameon=False)
    fig.tight_layout()
    TORNADO.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(TORNADO, bbox_inches="tight")
    plt.close(fig)

    def summary(mode):
        c = totals[mode]
        return f"**{mode.title()}: {c['better']:,} better / {c['equal']:,} equal / {c['worse']:,} worse**"
    def table_row(reason, label):
        values = [breakdown[m][reason][v] for m,v in (("fast","better"),("fast","worse"),("best","better"),("best","worse"))]
        return "| " + label + " | " + " | ".join(str(x) for x in values) + " |"
    section = f"""### Fast vs Best vs iHub: carton recommendation quality

![Fast and Best compared with iHub on policy-compliant orders](benchmark_results/solver_demo/fast_best_ihub_comparison.svg)

**Fresh 5-second Best benchmark:** {len(rows):,} orders; {len(rows)-len(eligible):,} flagged iHub fill-cap exceptions excluded; {len(eligible):,} policy-screened comparisons. The objective is **fewest cartons, then lowest total external carton volume**. {summary('fast')}; {summary('best')}.

#### What drives improvements and losses

![Breakdown by first differing objective](benchmark_results/solver_demo/fast_best_ihub_tornado.svg)

| First differing objective | Fast better | Fast worse | Best better | Best worse |
| --- | ---: | ---: | ---: | ---: |
{table_row('carton_count', 'Carton count')}
{table_row('total_volume', 'Total external carton volume')}

The historical iHub output does not include independently verifiable 3D item placements, so reference recommendations are comparisons, not proven feasible packing solutions. The counts above are generated from the same saved CSV as the chart and Solver Demo.

[Download the 2,000-order benchmark CSV](notebooks/artifacts/benchmark_2000_best_vs_ihub.csv) · [Open the executed Solver Demo](notebooks/Solver%20Demo.ipynb)

"""
    old = README.read_text(encoding="utf-8")
    start = old.index("### Fast vs Best vs iHub: carton recommendation quality")
    end = old.index("</details>", start)
    README.write_text(old[:start] + section + old[end:], encoding="utf-8")
    print(f"Updated README and tornado from {len(rows)} rows: {totals}")

if __name__ == "__main__":
    main()
