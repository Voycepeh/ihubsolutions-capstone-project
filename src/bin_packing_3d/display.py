"""Dependency-light notebook tables for packing inputs and results."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from html import escape
from typing import Any

from .models import PackingResult


@dataclass(frozen=True)
class DisplayTable:
    """Tabular data with native rich rendering in Jupyter notebooks."""

    rows: tuple[Mapping[str, Any], ...]
    columns: tuple[str, ...]

    def _repr_html_(self) -> str:
        """Return a safe HTML table used automatically by Jupyter."""
        header = "".join(f"<th>{escape(column)}</th>" for column in self.columns)
        body = "".join(
            "<tr>" + "".join(
                f"<td>{escape(str(row.get(column, '')))}</td>" for column in self.columns
            ) + "</tr>"
            for row in self.rows
        )
        return (
            '<table style="border-collapse:collapse">'
            f"<thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>"
        )


def make_table(
    rows: Sequence[Mapping[str, Any]],
    columns: Sequence[str] | None = None,
) -> DisplayTable:
    """Create a reusable Jupyter-renderable table without external packages."""
    copied_rows = tuple(dict(row) for row in rows)
    resolved_columns = tuple(columns or (tuple(copied_rows[0]) if copied_rows else ()))
    return DisplayTable(copied_rows, resolved_columns)


def display_table(
    rows: Sequence[Mapping[str, Any]],
    columns: Sequence[str] | None = None,
) -> None:
    """Display mappings as a rich notebook table."""
    table = make_table(rows, columns)
    try:
        from IPython.display import display
    except ImportError as exc:
        raise ImportError(
            "Notebook table display requires IPython; install requirements.txt."
        ) from exc
    display(table)


def result_tables(result: PackingResult) -> tuple[DisplayTable, DisplayTable]:
    """Return summary and placement tables for a packing result.

    Dimensions and coordinates are millimetres, volumes are cubic
    millimetres, weights are kilograms, and runtime is milliseconds.
    """
    metrics_by_box = {
        metric.box_instance_id: metric for metric in result.metrics.boxes
    }
    summary = make_table([
        {
            "Status": result.status,
            "Strategy": result.strategy,
            "Total cartons": result.metrics.box_count,
            "Carton number": index,
            "Carton": packed_box.instance_id,
            "Box type": packed_box.box_code,
            "Item qty": len(packed_box.placements),
            "Usable fill (%)": round(
                metrics_by_box[packed_box.instance_id].usable_utilization_pct, 2
            ),
            "Runtime (ms)": round(result.runtime_ms, 3),
            "Valid": result.validation.valid,
        }
        for index, packed_box in enumerate(result.packed_boxes, start=1)
    ])
    placement_columns = (
        "Carton",
        "Box type",
        "Item",
        "Packed L (mm)",
        "Packed W (mm)",
        "Packed H (mm)",
        "X (mm)",
        "Y (mm)",
        "Z (mm)",
        "Volume (mm^3)",
    )
    placements = make_table([
        {
            "Carton": box.instance_id,
            "Box type": box.box_code,
            "Item": placement.item_instance_id,
            "Packed L (mm)": placement.orientation.length,
            "Packed W (mm)": placement.orientation.width,
            "Packed H (mm)": placement.orientation.height,
            "X (mm)": placement.position.x,
            "Y (mm)": placement.position.y,
            "Z (mm)": placement.position.z,
            "Volume (mm^3)": placement.orientation.volume,
        }
        for box in result.packed_boxes
        for placement in box.placements
    ], columns=placement_columns)
    return summary, placements


def display_result(result: PackingResult) -> None:
    """Display a packing result as summary and placement notebook tables."""
    summary, placements = result_tables(result)
    try:
        from IPython.display import display
    except ImportError as exc:
        raise ImportError(
            "Notebook result display requires IPython; install requirements.txt."
        ) from exc
    display(summary)
    display(placements)
