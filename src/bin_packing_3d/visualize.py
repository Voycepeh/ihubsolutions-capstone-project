"""Optional 3D visualization for validated packing results."""
from __future__ import annotations

import math
from typing import Any

from .models import Orientation, PackingResult, Placement


def _cuboid_faces(placement: Placement) -> list[list[tuple[float, float, float]]]:
    """Return the six faces of a placement cuboid."""
    x, y, z = placement.position.x, placement.position.y, placement.position.z
    length = placement.orientation.length
    width = placement.orientation.width
    height = placement.orientation.height
    x1, y1, z1 = x + length, y + width, z + height

    return [
        [(x, y, z), (x1, y, z), (x1, y1, z), (x, y1, z)],
        [(x, y, z1), (x1, y, z1), (x1, y1, z1), (x, y1, z1)],
        [(x, y, z), (x1, y, z), (x1, y, z1), (x, y, z1)],
        [(x, y1, z), (x1, y1, z), (x1, y1, z1), (x, y1, z1)],
        [(x, y, z), (x, y1, z), (x, y1, z1), (x, y, z1)],
        [(x1, y, z), (x1, y1, z), (x1, y1, z1), (x1, y, z1)],
    ]


def _draw_carton_edges(axis: Any, dimensions: Orientation) -> None:
    """Draw the usable carton boundary as a wireframe."""
    length, width, height = dimensions.length, dimensions.width, dimensions.height
    corners = [
        (0, 0, 0), (length, 0, 0), (length, width, 0), (0, width, 0),
        (0, 0, height), (length, 0, height),
        (length, width, height), (0, width, height),
    ]
    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7),
    ]
    for start, end in edges:
        xs, ys, zs = zip(corners[start], corners[end])
        axis.plot(xs, ys, zs, color="black", linewidth=1.2, alpha=0.8)


def visualize_result(
    result: PackingResult,
    *,
    show: bool = True,
    elevation: float = 25,
    azimuth: float = 135,
) -> tuple[Any, list[Any]]:
    """Plot item cuboids inside each carton and return ``(figure, axes)``.

    The plot is an explanatory view of an already validated result. Geometry
    validation remains authoritative because a 3D projection can hide overlap.
    Matplotlib is imported lazily so non-visual solver use stays lightweight.
    """
    try:
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    except ImportError as exc:
        raise ImportError(
            "Packing visualization requires matplotlib; install requirements.txt."
        ) from exc

    if not result.packed_boxes:
        raise ValueError("Cannot visualize a packing result with no packed cartons")

    carton_count = len(result.packed_boxes)
    columns = min(3, carton_count)
    rows = math.ceil(carton_count / columns)
    figure = plt.figure(figsize=(5.5 * columns, 5.2 * rows))
    figure.subplots_adjust(left=0.03, right=0.97, bottom=0.08, top=0.82,
                           wspace=0.25, hspace=0.35)
    axes: list[Any] = []
    colors = plt.get_cmap("tab20")
    metrics_by_box = {metric.box_instance_id: metric for metric in result.metrics.boxes}

    for carton_index, carton in enumerate(result.packed_boxes):
        axis = figure.add_subplot(rows, columns, carton_index + 1, projection="3d")
        axes.append(axis)
        dimensions = carton.usable_dimensions
        _draw_carton_edges(axis, dimensions)

        for item_index, placement in enumerate(carton.placements):
            color = colors(item_index % colors.N)
            faces = Poly3DCollection(
                _cuboid_faces(placement),
                facecolors=color,
                edgecolors="black",
                linewidths=0.7,
                alpha=0.6,
            )
            axis.add_collection3d(faces)

            center_x = placement.position.x + placement.orientation.length / 2
            center_y = placement.position.y + placement.orientation.width / 2
            center_z = placement.position.z + placement.orientation.height / 2
            axis.text(
                center_x,
                center_y,
                center_z,
                placement.item_instance_id,
                ha="center",
                va="center",
                fontsize=7,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.65, "pad": 1},
            )

        metric = metrics_by_box.get(carton.instance_id)
        utilization = metric.usable_utilization_pct if metric else 0.0
        axis.set_title(
            f"Packed Box {carton_index + 1} — type {carton.box_code}\n"
            f"used {utilization:.1f}% · free {100.0 - utilization:.1f}%",
            pad=4,
        )
        axis.set_xlabel("X / length (mm)")
        axis.set_ylabel("Y / width (mm)")
        axis.set_zlabel("Z / height (mm)")
        axis.set_xlim(0, dimensions.length)
        axis.set_ylim(0, dimensions.width)
        axis.set_zlim(0, dimensions.height)
        axis.set_box_aspect((dimensions.length, dimensions.width, dimensions.height))
        # View the origin corner from the opposite side so flush placements do
        # not dominate the foreground or hide the remaining carton space.
        axis.view_init(elev=elevation, azim=azimuth)

    if show:
        plt.show()
    return figure, axes
