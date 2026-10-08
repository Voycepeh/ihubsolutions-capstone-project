"""Normalization and deterministic business rules shared by every solver."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import isfinite
from numbers import Real
from typing import Any

from .models import (
    Box, InvalidConfigError, InvalidInputError, Item, Orientation, PackingConfig,
    PhysicalItem, UnpackableItemError,
)


def _lookup(data: Mapping[str, Any], *names: str, required: bool = True, default: Any = None) -> Any:
    for name in names:
        if name in data:
            return data[name]
    if required:
        raise InvalidInputError(f"Missing required field '{names[0]}'")
    return default


def _positive_number(value: Any, field: str) -> float:
    if (isinstance(value, bool) or not isinstance(value, Real)
            or not isfinite(value) or value <= 0):
        raise InvalidInputError(f"{field} must be a positive number")
    return float(value)


def _sequence(raw: Any, wrapper: str, subject: str) -> Sequence[Mapping[str, Any]]:
    if isinstance(raw, Mapping) and wrapper in raw:
        raw = raw[wrapper]
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        raise InvalidInputError(f"{subject} must be a list")
    return raw


def normalize_order(order: Mapping[str, Any]) -> tuple[Any, Any, list[Item]]:
    if not isinstance(order, Mapping):
        raise InvalidInputError("order must be a mapping")
    raw_items = _lookup(order, "Items", "items")
    items_data = _sequence(raw_items, "ItemsList", "Items")
    if not items_data:
        raise InvalidInputError("Order must contain at least one item")
    order_id = _lookup(order, "OrderId", "order_id", required=False)
    order_number = _lookup(order, "OrderNo", "order_number", required=False)
    items: list[Item] = []
    for index, raw in enumerate(items_data):
        if not isinstance(raw, Mapping):
            raise InvalidInputError(f"Item at index {index} must be a mapping")
        code = _lookup(raw, "Code", "code")
        if not isinstance(code, str) or not code.strip():
            raise InvalidInputError(f"Item at index {index} Code must be a non-empty string")
        quantity = _lookup(raw, "Quantity", "quantity")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise InvalidInputError(f"Item '{code}' Quantity must be a positive integer")
        rotation = _lookup(raw, "VerticalRotation", "vertical_rotation")
        if rotation not in (0, 1, False, True):
            raise InvalidInputError(f"Item '{code}' VerticalRotation must be boolean or 0/1")
        items.append(Item(
            code=code, length=_positive_number(_lookup(raw, "Length", "length"), f"Item '{code}' Length"),
            width=_positive_number(_lookup(raw, "Width", "width"), f"Item '{code}' Width"),
            height=_positive_number(_lookup(raw, "Height", "height"), f"Item '{code}' Height"),
            weight=_positive_number(_lookup(raw, "Weight", "weight"), f"Item '{code}' Weight"),
            quantity=quantity, vertical_rotation=bool(rotation),
            uom=_lookup(raw, "UOM", "uom", required=False), order_id=order_id, order_number=order_number,
        ))
    return order_id, order_number, items


def normalize_boxes(boxes: Any) -> list[Box]:
    if isinstance(boxes, Mapping) and "Bins" in boxes:
        boxes = boxes["Bins"]
    data = _sequence(boxes, "BinsList", "boxes")
    if not data:
        raise InvalidInputError("Carton catalogue must not be empty")
    result: list[Box] = []
    seen: set[str] = set()
    for index, raw in enumerate(data):
        if not isinstance(raw, Mapping):
            raise InvalidInputError(f"Carton at index {index} must be a mapping")
        code = _lookup(raw, "Code", "code")
        if not isinstance(code, str) or not code.strip():
            raise InvalidInputError(f"Carton at index {index} Code must be a non-empty string")
        if code in seen:
            raise InvalidInputError(f"Duplicate carton Code '{code}'")
        seen.add(code)
        result.append(Box(code, _positive_number(_lookup(raw, "Length", "length"), f"Carton '{code}' Length"),
                          _positive_number(_lookup(raw, "Width", "width"), f"Carton '{code}' Width"),
                          _positive_number(_lookup(raw, "Height", "height"), f"Carton '{code}' Height"),
                          _positive_number(_lookup(raw, "MaxWeight", "max_weight"), f"Carton '{code}' MaxWeight")))
    return sorted(result, key=lambda b: (b.external_volume, b.code))


def normalize_config(raw: Mapping[str, Any] | PackingConfig | None) -> PackingConfig:
    if isinstance(raw, PackingConfig):
        config = raw
    else:
        raw = raw or {}
        if not isinstance(raw, Mapping):
            raise InvalidConfigError("config must be a mapping")
        buffer = raw.get("bin_buffer", raw.get("BinBuffer", {}))
        if not isinstance(buffer, Mapping):
            raise InvalidConfigError("bin_buffer must be a mapping")
        def b(name: str) -> Any:
            return buffer.get(name, buffer.get(name.title(), 6 if name == "height" else 0))
        mode = raw.get("mode", "fast")
        if "strategy" in raw and "mode" not in raw:
            # strategy remains an advanced extension hook for registered custom solvers.
            strategy = raw["strategy"]
            mode = "custom"
        else:
            strategy = {"fast": "fast_fit", "best": "best_fit"}.get(mode, "")
        config = PackingConfig(
            mode=mode,
            strategy=strategy,
            max_fill_pct=raw.get("max_fill_pct", 100),
            high_item_count_threshold=raw.get(
                "high_item_count_threshold",
                raw.get("BinMaxFillCheckMinItemQty", 6),
            ),
            high_item_count_max_fill_pct=raw.get(
                "high_item_count_max_fill_pct",
                raw.get("BinMaxFillPct", 70),
            ),
            bin_buffer=Orientation(b("length"), b("width"), b("height")),
            max_runtime_ms=raw.get("max_runtime_ms", 900),
            deterministic=raw.get("deterministic", True),
            trace_enabled=raw.get("trace_enabled", False),
        )
    if not isinstance(config.mode, str) or config.mode not in {"fast", "best", "custom"}:
        raise InvalidConfigError("mode must be 'fast' or 'best'")
    if not isinstance(config.strategy, str) or not config.strategy.strip():
        raise InvalidConfigError("strategy must be a non-empty string")
    if (isinstance(config.high_item_count_threshold, bool)
            or not isinstance(config.high_item_count_threshold, int)
            or config.high_item_count_threshold < 0):
        raise InvalidConfigError("high_item_count_threshold must be a non-negative integer")
    for value, name in (
        (config.max_fill_pct, "max_fill_pct"),
        (config.high_item_count_max_fill_pct, "high_item_count_max_fill_pct"),
    ):
        if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
            raise InvalidConfigError(f"{name} must be a finite number")
    for value, name in (
        (config.max_fill_pct, "max_fill_pct"),
        (config.high_item_count_max_fill_pct, "high_item_count_max_fill_pct"),
    ):
        if not 0 < value <= 100:
            raise InvalidConfigError(f"{name} must be greater than 0 and at most 100")
    if config.max_runtime_ms is not None:
        if isinstance(config.max_runtime_ms, bool) or not isinstance(config.max_runtime_ms, Real) or not isfinite(config.max_runtime_ms) or config.max_runtime_ms <= 0:
            raise InvalidConfigError("max_runtime_ms must be a finite positive number or None")
    for value, name in zip((config.bin_buffer.length, config.bin_buffer.width, config.bin_buffer.height), ("length", "width", "height")):
        if (isinstance(value, bool) or not isinstance(value, Real)
                or not isfinite(value) or value < 0):
            raise InvalidConfigError(f"bin_buffer.{name} must be a finite non-negative number")
    if not isinstance(config.deterministic, bool):
        raise InvalidConfigError("deterministic must be boolean")
    if not isinstance(config.trace_enabled, bool):
        raise InvalidConfigError("trace_enabled must be boolean")
    return PackingConfig(
        mode=config.mode,
        strategy=config.strategy.strip().lower(),
        max_fill_pct=float(config.max_fill_pct),
        high_item_count_threshold=config.high_item_count_threshold,
        high_item_count_max_fill_pct=float(config.high_item_count_max_fill_pct),
        bin_buffer=Orientation(*map(float, (
            config.bin_buffer.length, config.bin_buffer.width, config.bin_buffer.height,
        ))),
        max_runtime_ms=None if config.max_runtime_ms is None else float(config.max_runtime_ms),
        deterministic=config.deterministic,
        trace_enabled=config.trace_enabled,
    )


def expand_items(items: list[Item]) -> list[PhysicalItem]:
    counts: dict[str, int] = {}
    expanded: list[PhysicalItem] = []
    for item in items:
        for _ in range(item.quantity):
            counts[item.code] = counts.get(item.code, 0) + 1
            expanded.append(PhysicalItem(f"{item.code}#{counts[item.code]}", item))
    return expanded


def allowed_orientations(item: Item | PhysicalItem) -> tuple[Orientation, ...]:
    source = item.source_item if isinstance(item, PhysicalItem) else item
    l, w, h = source.length, source.width, source.height
    candidates = ((l,w,h),(w,l,h),(l,h,w),(h,l,w),(w,h,l),(h,w,l)) if source.vertical_rotation else ((l,w,h),(w,l,h))
    seen: set[tuple[float,float,float]] = set()
    result = []
    for dimensions in candidates:
        if dimensions not in seen:
            seen.add(dimensions); result.append(Orientation(*dimensions))
    return tuple(result)


def usable_dimensions(box: Box, config: PackingConfig) -> Orientation:
    dimensions = Orientation(box.length-config.bin_buffer.length, box.width-config.bin_buffer.width, box.height-config.bin_buffer.height)
    if min(dimensions.length, dimensions.width, dimensions.height) <= 0:
        raise InvalidConfigError(f"bin_buffer produces non-positive usable dimensions for carton '{box.code}'")
    return dimensions


def effective_max_fill_pct(physical_item_count: int, config: PackingConfig) -> float:
    """Return the shared carton fill limit for an expanded order quantity."""
    if physical_item_count > config.high_item_count_threshold:
        return min(config.max_fill_pct, config.high_item_count_max_fill_pct)
    return config.max_fill_pct


def item_fits_box(item: PhysicalItem, box: Box, config: PackingConfig) -> bool:
    if item.weight > box.max_weight:
        return False
    usable = usable_dimensions(box, config)
    return any(o.length <= usable.length and o.width <= usable.width and o.height <= usable.height for o in allowed_orientations(item))


def ensure_individual_feasibility(items: list[PhysicalItem], boxes: list[Box], config: PackingConfig) -> None:
    impossible = [item.instance_id for item in items if not any(item_fits_box(item, box, config) for box in boxes)]
    if impossible:
        raise UnpackableItemError(impossible)
