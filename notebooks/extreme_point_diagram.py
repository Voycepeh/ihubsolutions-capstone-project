"""
Extreme-Point Placement Diagram Generator
------------------------------------------
Illustrates the extreme-point (EP) placement rule used in 3D bin packing
(Crainic, Perboli & Tadei, 2008): after an item is placed, it exposes
exactly three new candidate points -- one to its right, one behind it,
and one above it -- where the next item can be tried.

Usage:
    pip install matplotlib
    python extreme_point_diagram.py

Output:
    extreme_point_diagram.png
"""

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


def draw_box(ax, origin, size, color, alpha=0.3, label=None, label_offset=0.3):
    """Draw a cuboid at `origin` with dimensions `size` = (dx, dy, dz)."""
    x, y, z = origin
    dx, dy, dz = size

    verts = [
        [(x, y, z), (x + dx, y, z), (x + dx, y + dy, z), (x, y + dy, z)],                     # bottom
        [(x, y, z + dz), (x + dx, y, z + dz), (x + dx, y + dy, z + dz), (x, y + dy, z + dz)], # top
        [(x, y, z), (x + dx, y, z), (x + dx, y, z + dz), (x, y, z + dz)],                     # front
        [(x, y + dy, z), (x + dx, y + dy, z), (x + dx, y + dy, z + dz), (x, y + dy, z + dz)], # back
        [(x, y, z), (x, y + dy, z), (x, y + dy, z + dz), (x, y, z + dz)],                     # left
        [(x + dx, y, z), (x + dx, y + dy, z), (x + dx, y + dy, z + dz), (x + dx, y, z + dz)], # right
    ]
    poly = Poly3DCollection(verts, facecolors=color, edgecolors="black",
                             linewidths=1.0, alpha=alpha)
    ax.add_collection3d(poly)

    if label:
        ax.text(x + dx / 2, y + dy / 2, z + dz + label_offset, label,
                ha="center", fontsize=9, fontweight="bold")


def main():
    fig = plt.figure(figsize=(8, 7))
    ax = fig.add_subplot(111, projection="3d")

    # ---- The carton (outline only, nearly transparent) ----
    CARTON = (8, 6, 5)
    draw_box(ax, (0, 0, 0), CARTON, color="white", alpha=0.05, label="Carton")

    # ---- Item 1: placed at the origin corner (0,0,0) ----
    item1_size = (3, 2, 2)
    draw_box(ax, (0, 0, 0), item1_size, color="steelblue", alpha=0.65, label="Item 1")

    # ---- Item 2: placed at the "right" extreme point, to show it in use ----
    ix, iy, iz = item1_size
    item2_size = (2, 2, 3)
    draw_box(ax, (ix, 0, 0), item2_size, color="darkorange", alpha=0.55, label="Item 2")

    # ---- The three extreme points exposed by Item 1 (drawn LAST so they sit on top) ----
    # Offsets are pushed further out and away from the boxes so labels don't collide
    # with the orange Item 2 box or get buried inside Item 1's footprint.
    extreme_points = {
        "P: right":  ((ix, 0, 0),          (0.25, -0.9, 0.3)),
        "P: behind": ((0, iy, 0),          (0.4, 0.5, 0.5)),
        "P: above":  ((0, 0, iz),          (0.4, -0.5, 0.4)),
    }
    for label, ((px, py, pz), (ox, oy, oz)) in extreme_points.items():
        ax.scatter(px, py, pz, color="red", s=90, depthshade=False, zorder=10)
        ax.text(px + ox, py + oy, pz + oz, label,
                fontsize=9, color="red", fontweight="bold", zorder=10,
                bbox=dict(boxstyle="round,pad=0.15", facecolor="white",
                          edgecolor="red", linewidth=0.8, alpha=0.9))

    # ---- Axes, labels, framing ----
    ax.set_xlim(-1, CARTON[0])
    ax.set_ylim(0, CARTON[1])
    ax.set_zlim(0, CARTON[2] + 1)
    ax.set_xlabel("Length (X)")
    ax.set_ylabel("Width (Y)")
    ax.set_zlabel("Height (Z)")
    ax.set_box_aspect(CARTON)
    ax.view_init(elev=22, azim=-55)
    ax.set_title("Extreme-Point Placement: Candidate Points After Item 1",
                 fontsize=12, fontweight="bold", pad=20)

    plt.tight_layout()
    plt.savefig("extreme_point_diagram.png", dpi=200, bbox_inches="tight")
    print("Saved extreme_point_diagram.png")
    plt.show()


if __name__ == "__main__":
    main()
