"""Report charts for the Best speed-ups (PNG + SVG in ``charts/``).

1. best_speedups_per_step   - 2,000 iHub orders, runtime per cumulative stage
2. best_heatmap_before_after - README scaling grid, Best before vs after
3. best_speedup_factor       - README scaling grid, before / after ratio
4. best_runtime_by_items     - README scaling grid at 20 box types

    python notebooks/best_speedups/plot_speedups.py
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, LogNorm, TwoSlopeNorm  # noqa: E402

HERE = Path(__file__).resolve().parent
CHARTS = HERE / "charts"

# Reference palette (dataviz skill, light mode).
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
BEFORE = "#eb6834"  # categorical slot 2
AFTER = "#2a78d6"   # categorical slot 1
BLUES = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
         "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
SEQUENTIAL = LinearSegmentedColormap.from_list("blues", BLUES)
# Diverging: red (slower) <- gray at 1x -> blue (faster).
DIVERGING = LinearSegmentedColormap.from_list("div", ["#e34948", "#f0efec", "#184f95"])

plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans", "sans-serif"],
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "text.color": INK, "axes.labelcolor": INK_2, "axes.edgecolor": AXIS,
    "xtick.color": INK_2, "ytick.color": INK_2, "axes.titlesize": 13, "axes.titleweight": "semibold",
})


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _save(figure, name: str) -> None:
    CHARTS.mkdir(exist_ok=True)
    figure.savefig(CHARTS / f"{name}.png", dpi=170, bbox_inches="tight")
    figure.savefig(CHARTS / f"{name}.svg", bbox_inches="tight")
    plt.close(figure)
    print("wrote", CHARTS / f"{name}.png")


def _seconds(ms: float) -> str:
    seconds = ms / 1000
    if seconds < 0.1:
        return f"{ms:,.0f} ms" if ms >= 10 else f"{ms:,.1f} ms"
    return f"{seconds:,.2f} s" if seconds < 10 else f"{seconds:,.1f} s"


def _clean(axis) -> None:
    for side in ("top", "right"):
        axis.spines[side].set_visible(False)
    axis.tick_params(length=0)


def per_step_chart() -> None:
    rows = _read(HERE / "dataset_summary.csv")
    labels = [f"{r['stage']}  {r['change'].replace('+ ', '')}" for r in rows]
    figure, axes = plt.subplots(1, 2, figsize=(13, 4.6), sharey=True)
    for axis, key, title in zip(axes, ("median_ms", "mean_ms"), ("Median runtime", "Mean runtime")):
        values = [float(r[key]) for r in rows]
        positions = range(len(rows))
        colors = [BEFORE] + [AFTER] * (len(rows) - 1)
        axis.barh(positions, values, color=colors, height=0.62)
        for position, value in zip(positions, values):
            axis.text(value + max(values) * 0.015, position, f"{value:,.1f} ms", va="center", fontsize=9, color=INK)
        axis.set_title(title, loc="left")
        axis.set_xlabel("Milliseconds per order")
        axis.set_xlim(0, max(values) * 1.18)
        axis.grid(axis="x", color=GRID, linewidth=0.8)
        axis.set_axisbelow(True)
        _clean(axis)
    axes[0].set_yticks(range(len(rows)), labels=labels)
    axes[0].invert_yaxis()
    figure.suptitle("Best solver speed-ups, added one at a time: 2,000 iHub orders", x=0.01, ha="left",
                    fontsize=14, fontweight="semibold")
    base, final = float(rows[0]["mean_ms"]), float(rows[-1]["mean_ms"])
    figure.text(0.01, -0.03,
                f"Orange = original Best (S0); blue = each later stage keeps the previous speed-ups. "
                f"Mean {base:,.0f} → {final:,.0f} ms ({base / final:.1f}× faster); same cartons proven on every "
                "order where both finished. 5 s budget, one CP-SAT worker.",
                fontsize=9, color=INK_2)
    figure.tight_layout()
    _save(figure, "best_speedups_per_step")


def _best_summary(variant: str) -> dict[tuple[int, int], float]:
    path = HERE / f"scaling_{variant}" / "summary.csv"
    return {(int(r["items"]), int(r["box_types"])): float(r["median_runtime_ms"])
            for r in _read(path) if r["mode"] == "best"}


def _heat(axis, matrix, items, boxes, norm, cmap, fmt):
    image = axis.imshow(matrix, aspect="auto", cmap=cmap, norm=norm)
    axis.set_xticks(range(len(boxes)), labels=boxes)
    axis.set_yticks(range(len(items)), labels=items)
    axis.set_xlabel("Available box types")
    for spine in axis.spines.values():
        spine.set_visible(False)
    axis.tick_params(length=0)
    for r, row in enumerate(matrix):
        for c, value in enumerate(row):
            shade = cmap(norm(value))
            luminance = 0.2126 * shade[0] + 0.7152 * shade[1] + 0.0722 * shade[2]
            axis.text(c, r, fmt(value), ha="center", va="center", fontsize=8.5,
                      color="#ffffff" if luminance < 0.5 else INK)
    return image


def scaling_charts() -> None:
    before, after = _best_summary("before"), _best_summary("after")
    items = sorted({key[0] for key in before})
    boxes = sorted({key[1] for key in before})
    grid_before = [[before[(i, b)] for b in boxes] for i in items]
    grid_after = [[after[(i, b)] for b in boxes] for i in items]

    # 2. Before / after heatmaps on one shared log colour scale.
    values = [v for row in grid_before + grid_after for v in row]
    norm = LogNorm(vmin=min(values), vmax=max(values))
    figure, axes = plt.subplots(1, 2, figsize=(14, 6.2), sharey=True)
    for axis, grid, title in zip(axes, (grid_before, grid_after), ("Before speed-ups", "After speed-ups")):
        image = _heat(axis, grid, items, boxes, norm, SEQUENTIAL, _seconds)
        axis.set_title(title, loc="left")
    axes[0].set_ylabel("Items in one order")
    bar = figure.colorbar(image, ax=axes, fraction=0.025, pad=0.02)
    bar.set_label("Median Best runtime (log scale)")
    bar.outline.set_visible(False)
    ticks = [t for t in (10, 100, 1_000, 10_000) if min(values) <= t <= max(values)]
    bar.set_ticks(ticks, labels=[_seconds(t) for t in ticks])
    figure.suptitle("Best execution time: items × box choices, before vs after speed-ups", x=0.01, ha="left",
                    fontsize=14, fontweight="semibold")
    figure.text(0.01, -0.02, "Same grid, seeds and uncapped search as the README scaling benchmark "
                "(3 synthetic orders per cell, median shown). Measured back to back on the same PC.",
                fontsize=9, color=INK_2)
    _save(figure, "best_heatmap_before_after")

    # 3. Speed-up factor.
    factors = [[b / a for b, a in zip(rb, ra)] for rb, ra in zip(grid_before, grid_after)]
    flat = [f for row in factors for f in row]
    span = max(abs(math.log10(min(flat))), abs(math.log10(max(flat))), 0.1)
    log_grid = [[math.log10(f) for f in row] for row in factors]
    norm = TwoSlopeNorm(vmin=-span, vcenter=0, vmax=span)
    figure, axis = plt.subplots(figsize=(8.5, 6.2))
    lookup = {math.log10(f): f for f in flat}
    image = _heat(axis, log_grid, items, boxes, norm, DIVERGING,
                  lambda v: f"{lookup.get(v, 10 ** v):,.1f}×")
    axis.set_ylabel("Items in one order")
    axis.set_title("How many times faster Best runs after the speed-ups", loc="left")
    bar = figure.colorbar(image, ax=axis, fraction=0.04, pad=0.03)
    bar.outline.set_visible(False)
    candidate = [0.25, 0.5, 1, 2, 5, 10, 50, 100]
    ticks = [math.log10(t) for t in candidate if -span <= math.log10(t) <= span]
    bar.set_ticks(ticks, labels=[f"{10 ** t:g}×" for t in ticks])
    bar.set_label("Before ÷ after (blue = faster, red = slower)")
    figure.text(0.01, -0.02, "Median runtime before divided by median after, per cell. 1× = no change.",
                fontsize=9, color=INK_2)
    _save(figure, "best_speedup_factor")

    # 4. Runtime by order size at the largest catalogue (like the README breakdown).
    widest = max(boxes)
    before_s = [before[(i, widest)] / 1000 for i in items]
    after_s = [after[(i, widest)] / 1000 for i in items]
    figure, axis = plt.subplots(figsize=(12, 5.4))
    width = 0.38
    xs = range(len(items))
    axis.bar([x - width / 2 - 0.01 for x in xs], before_s, width, color=BEFORE, label="Before speed-ups")
    axis.bar([x + width / 2 + 0.01 for x in xs], after_s, width, color=AFTER, label="After speed-ups")
    axis.set_yscale("log")
    axis.set_xticks(list(xs), labels=items)
    axis.set_xlabel("Items in one order")
    axis.set_ylabel("Median Best runtime (seconds, log scale)")
    axis.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:g}"))
    for x, b, a in zip(xs, before_s, after_s):
        axis.text(x + width / 2 + 0.01, a * 1.15, f"{b / a:,.0f}×" if b / a >= 1.5 else "≈", ha="center",
                  fontsize=9, color=INK, fontweight="semibold")
    axis.legend(frameon=False, loc="upper left")
    axis.grid(axis="y", color=GRID, linewidth=0.8)
    axis.set_axisbelow(True)
    _clean(axis)
    axis.set_title(f"Best runtime by order size ({widest} box types), before vs after", loc="left")
    figure.text(0.01, -0.03, "Labels above the blue bars show how many times faster; ≈ means under 1.5×. "
                "Median of 3 synthetic orders per size, uncapped search.", fontsize=9, color=INK_2)
    figure.tight_layout()
    _save(figure, "best_runtime_by_items")


if __name__ == "__main__":
    per_step_chart()
    if (HERE / "scaling_before" / "summary.csv").exists() and (HERE / "scaling_after" / "summary.csv").exists():
        scaling_charts()
    else:
        print("Scaling results not finished yet; skipped scaling charts.")
