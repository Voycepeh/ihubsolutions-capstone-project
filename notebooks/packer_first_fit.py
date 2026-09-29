"""
packer_first_fit.py

3D extreme-point carton packer (first-fit bin selection) + dataset runner,
combined into one file. Put data_sample_v1.json next to this script and run:

    python packer_first_fit.py
    python packer_first_fit.py path/to/file.json
    python packer_first_fit.py --limit 100
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import random
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd

EPS = 1e-9


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Item:
    code: str
    length: float
    width: float
    height: float
    weight: float
    quantity: int = 1
    vertical_rotation: int = 1  # 0 = upright only, 1 = any orientation


@dataclass(frozen=True)
class Box:
    code: str
    length: float
    width: float
    height: float
    max_weight: float

    @property
    def volume(self) -> float:
        return self.length * self.width * self.height


@dataclass
class Config:
    bin_buffer_length: float = 0.0
    bin_buffer_width: float = 0.0
    bin_buffer_height: float = 6.0
    bin_max_fill_pct: float = 70.0
    bin_max_fill_check_min_item_qty: int = 6
    max_box_weight: float = 20.0
    min_support_ratio: float = 0.8
    use_compaction: bool = True
    multi_box_branching: int = 3
    max_seconds_per_order: float = 1.0


@dataclass(frozen=True)
class Unit:
    code: str
    index: int
    length: float
    width: float
    height: float
    weight: float
    vertical_rotation: int

    @property
    def volume(self) -> float:
        return self.length * self.width * self.height


@dataclass(frozen=True)
class Placement:
    unit: Unit
    x: float
    y: float
    z: float
    dx: float
    dy: float
    dz: float

    def overlaps(self, x, y, z, dx, dy, dz) -> bool:
        return (x < self.x + self.dx - EPS and self.x < x + dx - EPS and
                y < self.y + self.dy - EPS and self.y < y + dy - EPS and
                z < self.z + self.dz - EPS and self.z < z + dz - EPS)

    def contains_point(self, px, py, pz) -> bool:
        return (self.x - EPS <= px < self.x + self.dx - EPS and
                self.y - EPS <= py < self.y + self.dy - EPS and
                self.z - EPS <= pz < self.z + self.dz - EPS)


@dataclass
class CartonResult:
    box: Box
    placements: list[Placement]
    packed_weight: float
    packed_volume: float
    usable_volume: float

    @property
    def item_count(self) -> int:
        return len(self.placements)

    @property
    def utilization_pct(self) -> float:
        return 100.0 * self.packed_volume / self.usable_volume


@dataclass
class UnpackedItem:
    unit: Unit
    reason: str


@dataclass
class PackResult:
    cartons: list[CartonResult] = field(default_factory=list)
    unpacked: list[UnpackedItem] = field(default_factory=list)
    status: str = "PACKED"
    runtime_s: float = 0.0

    @property
    def carton_count(self) -> int:
        return len(self.cartons)


# ---------------------------------------------------------------------------
# Orientations
# ---------------------------------------------------------------------------

def orientations(l, w, h, vertical_rotation):
    upright = [(l, w, h), (w, l, h)]
    if vertical_rotation == 0:
        return upright
    all_six = upright + [(l, h, w), (h, l, w), (w, h, l), (h, w, l)]
    return list(dict.fromkeys(all_six))


def _ordered_orientations(unit: Unit, preference: str):
    opts = orientations(unit.length, unit.width, unit.height, unit.vertical_rotation)
    if preference == "flat":
        return sorted(opts, key=lambda o: o[2])
    return sorted(opts, key=lambda o: (0 if abs(o[2] - unit.height) < EPS else 1, o[2]))


# ---------------------------------------------------------------------------
# Pre-processing
# ---------------------------------------------------------------------------

def expand_items(items: list[Item]) -> list[Unit]:
    units = []
    for it in items:
        for i in range(1, it.quantity + 1):
            units.append(Unit(it.code, i, it.length, it.width, it.height,
                              it.weight, it.vertical_rotation))
    return units


def usable_dims(box: Box, cfg: Config):
    return (box.length - cfg.bin_buffer_length,
            box.width - cfg.bin_buffer_width,
            box.height - cfg.bin_buffer_height)


def usable_volume(box: Box, cfg: Config) -> float:
    l, w, h = usable_dims(box, cfg)
    return max(l, 0) * max(w, 0) * max(h, 0)


def weight_limit(box: Box, cfg: Config) -> float:
    return min(box.max_weight, cfg.max_box_weight)


def why_unpackable(unit: Unit, boxes: list[Box], cfg: Config) -> Optional[str]:
    if all(unit.weight > weight_limit(b, cfg) + EPS for b in boxes):
        return "exceeds maximum box weight"
    for b in boxes:
        if unit.weight > weight_limit(b, cfg) + EPS:
            continue
        cl, cw, ch = usable_dims(b, cfg)
        for dx, dy, dz in orientations(unit.length, unit.width, unit.height,
                                       unit.vertical_rotation):
            if dx <= cl + EPS and dy <= cw + EPS and dz <= ch + EPS:
                return None
    return "does not fit any box in an allowed orientation"


def _biggest_face(u: Unit) -> float:
    a, b, _ = sorted((u.length, u.width, u.height), reverse=True)
    return a * b


ORDERINGS = {
    "volume":    lambda u: (-u.volume, u.vertical_rotation, u.code, u.index),
    "longest":   lambda u: (-max(u.length, u.width, u.height), -u.volume, u.code, u.index),
    "footprint": lambda u: (-_biggest_face(u), -u.volume, u.code, u.index),
    "upright":   lambda u: (u.vertical_rotation, -u.volume, u.code, u.index),
}
POLICIES = [("upright", "zyx"), ("flat", "zyx"), ("upright", "zxy"), ("flat", "zxy")]


# ---------------------------------------------------------------------------
# Extreme-point placement
# ---------------------------------------------------------------------------

def _overlap_1d(a0, al, b0, bl) -> bool:
    return a0 < b0 + bl - EPS and b0 < a0 + al - EPS


def _is_supported(x, y, z, dx, dy, placed, min_ratio) -> bool:
    if z < EPS:
        return True
    supported_area = 0.0
    for p in placed:
        if abs((p.z + p.dz) - z) < EPS:
            ox = min(x + dx, p.x + p.dx) - max(x, p.x)
            oy = min(y + dy, p.y + p.dy) - max(y, p.y)
            if ox > 0 and oy > 0:
                supported_area += ox * oy
    return supported_area >= min_ratio * dx * dy - EPS


def _compact(x, y, z, dx, dy, dz, placed, min_support):
    for _ in range(6):
        moved = False
        nz = max((p.z + p.dz for p in placed
                  if p.z + p.dz <= z + EPS and _overlap_1d(x, dx, p.x, p.dx)
                  and _overlap_1d(y, dy, p.y, p.dy)), default=0.0)
        if nz < z - EPS and _is_supported(x, y, nz, dx, dy, placed, min_support):
            z, moved = nz, True
        ny = max((p.y + p.dy for p in placed
                  if p.y + p.dy <= y + EPS and _overlap_1d(x, dx, p.x, p.dx)
                  and _overlap_1d(z, dz, p.z, p.dz)), default=0.0)
        if ny < y - EPS and _is_supported(x, ny, z, dx, dy, placed, min_support):
            y, moved = ny, True
        nx = max((p.x + p.dx for p in placed
                  if p.x + p.dx <= x + EPS and _overlap_1d(y, dy, p.y, p.dy)
                  and _overlap_1d(z, dz, p.z, p.dz)), default=0.0)
        if nx < x - EPS and _is_supported(nx, y, z, dx, dy, placed, min_support):
            x, moved = nx, True
        if not moved:
            break
    return x, y, z


def _find_spot(unit: Unit, points, placed, dims, cfg: Config, policy):
    cl, cw, ch = dims
    pref, point_order = policy
    orients = _ordered_orientations(unit, pref)
    keyfn = (lambda p: (p[2], p[1], p[0])) if point_order == "zyx" else (lambda p: (p[2], p[0], p[1]))
    for pt in sorted(points, key=keyfn):
        px, py, pz = pt
        for dx, dy, dz in orients:
            if px + dx > cl + EPS or py + dy > cw + EPS or pz + dz > ch + EPS:
                continue
            if any(p.overlaps(px, py, pz, dx, dy, dz) for p in placed):
                continue
            if not _is_supported(px, py, pz, dx, dy, placed, cfg.min_support_ratio):
                continue
            x, y, z = (_compact(px, py, pz, dx, dy, dz, placed, cfg.min_support_ratio)
                       if cfg.use_compaction else (px, py, pz))
            return pt, x, y, z, dx, dy, dz
    return None


def pack_into_box(box: Box, units: list[Unit], cfg: Config, apply_fill_cap: bool,
                  policy=POLICIES[0]):
    dims = usable_dims(box, cfg)
    if min(dims) <= 0:
        return [], list(units)

    w_limit = weight_limit(box, cfg)
    max_fill_volume = usable_volume(box, cfg) * cfg.bin_max_fill_pct / 100.0

    placed: list[Placement] = []
    leftover: list[Unit] = []
    points = {(0.0, 0.0, 0.0)}
    total_weight = 0.0
    total_volume = 0.0

    for u in units:
        if total_weight + u.weight > w_limit + EPS:
            leftover.append(u)
            continue
        if apply_fill_cap and total_volume + u.volume > max_fill_volume + EPS:
            leftover.append(u)
            continue

        spot = _find_spot(u, points, placed, dims, cfg, policy)
        if spot is None:
            leftover.append(u)
            continue

        pt, x, y, z, dx, dy, dz = spot
        placed.append(Placement(u, x, y, z, dx, dy, dz))
        total_weight += u.weight
        total_volume += u.volume

        points.discard(pt)
        points.update({(x + dx, y, z), (x, y + dy, z), (x, y, z + dz)})
        points = {q for q in points
                  if q[0] < dims[0] - EPS and q[1] < dims[1] - EPS and q[2] < dims[2] - EPS
                  and not any(pl.contains_point(*q) for pl in placed)}

    return placed, leftover


def best_attempt(box: Box, units: list[Unit], cfg: Config, apply_fill_cap: bool):
    best = None
    for key in ORDERINGS.values():
        ordered = sorted(units, key=key)
        for policy in POLICIES:
            placed, left = pack_into_box(box, ordered, cfg, apply_fill_cap, policy)
            if not left:
                return placed, left
            score = (sum(p.unit.volume for p in placed), -len(left))
            if best is None or score > best[0]:
                best = (score, placed, left)
    return best[1], best[2]


def _to_carton(box: Box, placed: list[Placement], cfg: Config) -> CartonResult:
    return CartonResult(box, placed,
                        sum(p.unit.weight for p in placed),
                        sum(p.unit.volume for p in placed),
                        usable_volume(box, cfg))


# ---------------------------------------------------------------------------
# Order-level engine (first fit)
# ---------------------------------------------------------------------------

def _choose_complete(candidates, cfg: Config):
    # first fit: smallest box that holds everything
    return min(candidates, key=lambda c: (c[0].volume, c[0].code))


def _plan(remaining: list[Unit], boxes: list[Box], cfg: Config, apply_fill_cap: bool,
          depth: int, deadline: float):
    attempts = [(b, *best_attempt(b, remaining, cfg, apply_fill_cap)) for b in boxes]

    complete = [a for a in attempts if not a[2]]
    if complete:
        box, placed, _ = _choose_complete(complete, cfg)
        return [_to_carton(box, placed, cfg)], []

    useful = [a for a in attempts if a[1]]
    if not useful:
        return [], list(remaining)

    useful.sort(key=lambda a: (-sum(p.unit.volume for p in a[1]), a[0].volume, a[0].code))
    k = cfg.multi_box_branching if time.perf_counter() < deadline else 1

    best = None
    for box, placed, left in useful[:k]:
        sub_cartons, sub_unpacked = _plan(left, boxes, cfg, apply_fill_cap, depth + 1, deadline)
        cartons = [_to_carton(box, placed, cfg)] + sub_cartons
        score = (len(sub_unpacked), len(cartons), sum(c.box.volume for c in cartons))
        if best is None or score < best[0]:
            best = (score, cartons, sub_unpacked)
    return best[1], best[2]


def pack_order(items: list[Item], boxes: list[Box], cfg: Config) -> PackResult:
    t0 = time.perf_counter()
    result = PackResult()

    packable: list[Unit] = []
    for u in expand_items(items):
        reason = why_unpackable(u, boxes, cfg)
        if reason:
            result.unpacked.append(UnpackedItem(u, reason))
        else:
            packable.append(u)

    total_items = len(packable) + len(result.unpacked)
    apply_fill_cap = total_items > cfg.bin_max_fill_check_min_item_qty

    if packable:
        cartons, leftover = _plan(packable, boxes, cfg, apply_fill_cap, 0,
                                  t0 + cfg.max_seconds_per_order)
        result.cartons = cartons
        for u in leftover:
            result.unpacked.append(
                UnpackedItem(u, "no feasible placement under weight/fill rules"))

    if not result.unpacked:
        result.status = "PACKED"
    elif result.cartons:
        result.status = "PARTIAL"
    else:
        result.status = "FAILED"
    result.runtime_s = time.perf_counter() - t0
    return result


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

def validate_result(result: PackResult, cfg: Config) -> list[str]:
    errors = []
    total_items = sum(c.item_count for c in result.cartons) + len(result.unpacked)
    fill_rule_active = total_items > cfg.bin_max_fill_check_min_item_qty
    for n, c in enumerate(result.cartons, 1):
        cl, cw, ch = usable_dims(c.box, cfg)
        for i, p in enumerate(c.placements):
            tag = f"carton {n} {p.unit.code}#{p.unit.index}"
            if p.x < -EPS or p.y < -EPS or p.z < -EPS or \
               p.x + p.dx > cl + EPS or p.y + p.dy > cw + EPS or p.z + p.dz > ch + EPS:
                errors.append(f"{tag}: outside box bounds")
            if p.unit.vertical_rotation == 0 and abs(p.dz - p.unit.height) > EPS:
                errors.append(f"{tag}: upright-only item was tipped")
            if sorted((p.dx, p.dy, p.dz)) != sorted((p.unit.length, p.unit.width, p.unit.height)):
                errors.append(f"{tag}: dimensions do not match the item")
            for q in c.placements[i + 1:]:
                if p.overlaps(q.x, q.y, q.z, q.dx, q.dy, q.dz):
                    errors.append(f"{tag}: overlaps {q.unit.code}#{q.unit.index}")
            others = [o for o in c.placements if o is not p]
            if not _is_supported(p.x, p.y, p.z, p.dx, p.dy, others, cfg.min_support_ratio):
                errors.append(f"{tag}: not supported from below")
        if c.packed_weight > weight_limit(c.box, cfg) + EPS:
            errors.append(f"carton {n}: over weight limit")
        if fill_rule_active and c.utilization_pct > cfg.bin_max_fill_pct + EPS:
            errors.append(f"carton {n}: exceeds max fill {cfg.bin_max_fill_pct}%")
    return errors


# ---------------------------------------------------------------------------
# Dataset runner
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent
DATA_FILENAME = "data_samples_v2.json"

DEFAULT_BOXES = [
    Box("Box2", 270, 170, 115, 20),
    Box("Box4", 340, 260, 150, 20),
    Box("Box5", 340, 260, 235, 20),
    Box("Box6", 340, 260, 280, 20),
    Box("Box8", 290, 180, 280, 20),
    Box("Box9", 440, 345, 280, 20),
]


def parse_items(inp: dict) -> list[Item]:
    return [Item(code=str(r["Code"]),
                 length=float(r["Length"]), width=float(r["Width"]), height=float(r["Height"]),
                 weight=float(r["Weight"]),
                 quantity=int(r["Quantity"]),
                 vertical_rotation=int(bool(r["VerticalRotation"])))
            for r in inp["Items"]["ItemsList"]]


def parse_boxes(bins: dict) -> list[Box]:
    for value in bins.values():
        if isinstance(value, list) and value and isinstance(value[0], dict) and "MaxWeight" in value[0]:
            return [Box(str(b["Code"]), float(b["Length"]), float(b["Width"]),
                        float(b["Height"]), float(b["MaxWeight"])) for b in value]
    return DEFAULT_BOXES


def parse_config(bins: dict, base: Config) -> Config:
    p = bins.get("Parameters", {}) or {}
    buf = p.get("BinBuffer", {}) or {}
    return dataclasses.replace(
        base,
        bin_buffer_length=float(buf.get("Length", base.bin_buffer_length)),
        bin_buffer_width=float(buf.get("Width", base.bin_buffer_width)),
        bin_buffer_height=float(buf.get("Height", base.bin_buffer_height)),
        bin_max_fill_pct=float(p.get("BinMaxFillPct", base.bin_max_fill_pct)),
        bin_max_fill_check_min_item_qty=int(p.get("BinMaxFillCheckMinItemQty",
                                                  base.bin_max_fill_check_min_item_qty)),
    )


def item_order_sensitivity(items: list[Item], boxes: list[Box], cfg: Config,
                           trials: int = 10, seed: int = 0) -> set:
    """Shuffle the input item-line order `trials` times and re-pack each time.
    Returns the set of distinct outcomes seen: (carton_count, box codes, unpacked
    count). One unique outcome means the result does not depend on item order."""
    rng = random.Random(seed)
    outcomes = set()
    for _ in range(trials):
        shuffled = items[:]
        rng.shuffle(shuffled)
        r = pack_order(shuffled, boxes, cfg)
        outcomes.add((r.carton_count, tuple(sorted(c.box.code for c in r.cartons)), len(r.unpacked)))
    return outcomes


def check_order_sensitivity(records: list[dict], trials: int = 10) -> None:
    base = Config()
    unstable = 0
    for rec in records:
        inp = rec["input"]
        items = parse_items(inp)
        boxes = parse_boxes(inp.get("Bins", {}) or {})
        cfg = parse_config(inp.get("Bins", {}) or {}, base)
        outcomes = item_order_sensitivity(items, boxes, cfg, trials=trials)
        if len(outcomes) > 1:
            unstable += 1
            print(f"  order {inp.get('OrderId')}: {len(outcomes)} different outcomes -> {outcomes}")
    print(f"Item-order sensitivity: {unstable} / {len(records)} orders gave a different "
          f"result depending on input item order (should be 0)")


def run(records: list[dict]) -> pd.DataFrame:
    rows = []
    base = Config()
    for rec in records:
        inp = rec["input"]
        bins = inp.get("Bins", {}) or {}
        items = parse_items(inp)
        boxes = parse_boxes(bins)
        cfg = parse_config(bins, base)

        res = pack_order(items, boxes, cfg)

        hist = (rec.get("output", {}).get("Data", {}) or {}).get("BinsPacked", []) or []
        hist_util = [b["UsedSpace"] for b in hist if "UsedSpace" in b]
        ours_util = [c.utilization_pct for c in res.cartons]
        vol_of = {b.code: b.volume for b in boxes}
        vol_ours = sum(c.box.volume for c in res.cartons)
        vol_hist = sum(vol_of.get(str(b.get("Code")), 0.0) for b in hist)

        rows.append({
            "order_id": inp.get("OrderId"),
            "item_count": sum(i.quantity for i in items),
            "status": res.status,
            "cartons_ours": res.carton_count,
            "cartons_hist": len(hist),
            "boxes_ours": "+".join(sorted(c.box.code for c in res.cartons)),
            "boxes_hist": "+".join(sorted(str(b.get("Code")) for b in hist)),
            "carton_volume_ours_L": round(vol_ours / 1e6, 2),
            "carton_volume_hist_L": round(vol_hist / 1e6, 2),
            "avg_util_ours": round(statistics.mean(ours_util), 1) if ours_util else 0.0,
            "avg_util_hist": round(statistics.mean(hist_util), 1) if hist_util else None,
            "unpacked": len(res.unpacked),
            "runtime_ms": round(res.runtime_s * 1000, 3),
            "latency_hist_ms": rec.get("latency_ms"),
            "violations": len(validate_result(res, cfg)),
        })
    return pd.DataFrame(rows)


def p95(series: pd.Series) -> float:
    s = sorted(series.dropna())
    return s[min(len(s) - 1, int(0.95 * len(s)))] if s else float("nan")


def summarize(df: pd.DataFrame) -> None:
    d = df["cartons_ours"] - df["cartons_hist"]
    print("\n--- first_fit ---")
    print(f"Orders: {len(df)} | " + ", ".join(f"{k}: {v}" for k, v in df["status"].value_counts().items()))
    print(f"Feasibility violations: {int(df['violations'].sum())} (should be 0)")
    print(f"Carton count vs history -> fewer: {(d < 0).sum()}, same: {(d == 0).sum()}, more: {(d > 0).sum()}")
    print(f"Total cartons: ours {df['cartons_ours'].sum()} vs history {df['cartons_hist'].sum()}")
    print(f"Total carton volume: ours {df['carton_volume_ours_L'].sum():.0f} L vs history "
          f"{df['carton_volume_hist_L'].sum():.0f} L (lower = smaller boxes)")
    print(f"Same carton mix as history: {(df['boxes_ours'] == df['boxes_hist']).mean() * 100:.1f}% of orders")
    print(f"Avg utilization: ours {df['avg_util_ours'].mean():.1f}% vs history {df['avg_util_hist'].mean():.1f}%")
    print(f"Runtime ms (ours)   -> median {df['runtime_ms'].median():.2f}, "
          f"P95 {p95(df['runtime_ms']):.2f}, max {df['runtime_ms'].max():.2f}")
    print(f"Latency ms (history) -> median {df['latency_hist_ms'].median():.2f}, "
          f"P95 {p95(df['latency_hist_ms']):.2f}, max {df['latency_hist_ms'].max():.2f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--check-order-sensitivity", action="store_true",
                    help="shuffle each order's item lines and confirm the result doesn't change")
    args = ap.parse_args()

    path = Path(args.file) if args.file else ROOT / DATA_FILENAME
    if not path.exists():
        raise SystemExit(f"Data file not found: {path}\n"
                         f"Place {DATA_FILENAME} in {ROOT} or pass its path: "
                         "python packer_first_fit.py <path>")
    print(f"Reading {path}")
    records = json.loads(path.read_text(encoding="utf-8"))
    if args.limit:
        records = records[:args.limit]

    if args.check_order_sensitivity:
        check_order_sensitivity(records)
        return

    df = run(records)
    out = ROOT / "results_first_fit.csv"
    df.to_csv(out, index=False)
    summarize(df)
    print(f"Saved per-order results to {out}")


if __name__ == "__main__":
    main()
