"""Shared, solver-independent domain models."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


class PackingError(Exception):
    """Base error for packing-domain failures."""


class InvalidInputError(PackingError):
    pass


class InvalidConfigError(PackingError):
    pass


class UnknownStrategyError(PackingError):
    pass


class UnpackableItemError(PackingError):
    """Raised when an item cannot fit any available carton."""

    def __init__(self, item_ids: list[str]):
        self.item_ids = item_ids
        super().__init__(f"No carton can contain physical item(s): {', '.join(item_ids)}")


class InvalidPackingPlanError(PackingError):
    """Raised when independent validation rejects a solver plan."""

    def __init__(self, validation: ValidationResult):
        self.validation = validation
        super().__init__("Invalid packing plan: " + "; ".join(e.message for e in validation.errors))


@dataclass(frozen=True)
class Item:
    code: str
    length: float
    width: float
    height: float
    weight: float
    quantity: int
    vertical_rotation: bool
    uom: str | None = None
    order_id: Any = None
    order_number: Any = None

    @property
    def volume(self) -> float:
        return self.length * self.width * self.height


@dataclass(frozen=True)
class PhysicalItem:
    instance_id: str
    source_item: Item

    @property
    def code(self) -> str:
        return self.source_item.code

    @property
    def weight(self) -> float:
        return self.source_item.weight

    @property
    def volume(self) -> float:
        return self.source_item.volume


@dataclass(frozen=True)
class Box:
    code: str
    length: float
    width: float
    height: float
    max_weight: float

    @property
    def external_volume(self) -> float:
        return self.length * self.width * self.height


@dataclass(frozen=True)
class Orientation:
    length: float
    width: float
    height: float

    @property
    def volume(self) -> float:
        return self.length * self.width * self.height


@dataclass(frozen=True)
class Position:
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class Placement:
    item_instance_id: str
    item_code: str
    box_instance_id: str
    orientation: Orientation
    position: Position


@dataclass
class PackedBox:
    box_code: str
    instance_id: str
    usable_dimensions: Orientation
    placements: list[Placement] = field(default_factory=list)


@dataclass
class PackingPlan:
    packed_boxes: list[PackedBox] = field(default_factory=list)
    unpacked_item_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def placements(self) -> list[Placement]:
        return [p for box in self.packed_boxes for p in box.placements]


@dataclass(frozen=True)
class PackingConfig:
    strategy: str = "first_fit"
    max_fill_pct: float = 100.0
    high_item_count_threshold: int = 6
    high_item_count_max_fill_pct: float = 70.0
    bin_buffer: Orientation = Orientation(0.0, 0.0, 6.0)
    max_runtime_ms: float = 900.0
    min_support_pct: float = 100.0
    deterministic: bool = True


@dataclass(frozen=True)
class ValidationError:
    code: str
    message: str
    item_instance_id: str | None = None
    box_instance_id: str | None = None


@dataclass
class ValidationResult:
    valid: bool
    errors: list[ValidationError] = field(default_factory=list)


@dataclass(frozen=True)
class BoxMetrics:
    box_instance_id: str
    packed_weight: float
    packed_volume: float
    usable_utilization_pct: float


@dataclass(frozen=True)
class PackingMetrics:
    box_count: int
    total_external_box_volume: float
    total_packed_item_volume: float
    overall_utilization_pct: float
    packed_item_count: int
    unpacked_item_count: int
    runtime_ms: float
    boxes: list[BoxMetrics] = field(default_factory=list)


@dataclass
class PackingResult:
    order_id: Any
    order_number: Any
    status: str
    strategy: str
    packed_boxes: list[PackedBox]
    unpacked_item_ids: list[str]
    runtime_ms: float
    metrics: PackingMetrics
    validation: ValidationResult

    @property
    def placements(self) -> list[Placement]:
        return [p for box in self.packed_boxes for p in box.placements]

    def to_dict(self) -> dict[str, Any]:
        """Return only JSON-compatible built-in containers and scalar values."""
        return asdict(self)
