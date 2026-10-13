"""
api.py

FastAPI wrapper around the packing engine (Stretch Goal MVP).

Exposes a self-hosted HTTP microservice that accepts item dimensions/weights
and returns the recommended box selection -- a functional replacement for a
third-party cartonization API call.

Run it:
    pip install fastapi uvicorn
    uvicorn api:app --reload --port 8000

Then either open http://localhost:8000/docs for interactive Swagger UI, or:

    curl -X POST http://localhost:8000/pack -H "Content-Type: application/json" -d '{
      "items": [
        {"code": "BOOK", "length": 210, "width": 150, "height": 30,
         "weight": 0.8, "quantity": 4, "vertical_rotation": 1}
      ]
    }'
"""

from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import packer_first_fit as ff_engine
import packer_best_fit as bf_engine

ENGINES = {"first_fit": ff_engine, "best_fit": bf_engine}

app = FastAPI(
    title="Open Source 3D Bin Packing Solution",
    description="Self-hosted microservice: send item dimensions/weights, get back the recommended carton(s).",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class ItemIn(BaseModel):
    code: str
    length: float = Field(gt=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    weight: float = Field(ge=0)
    quantity: int = Field(default=1, ge=1)
    vertical_rotation: int = Field(default=1, ge=0, le=1,
                                   description="0 = must stay upright, 1 = any orientation")


class BoxIn(BaseModel):
    code: str
    length: float = Field(gt=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    max_weight: float = Field(gt=0)


class ConfigIn(BaseModel):
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


class PackRequest(BaseModel):
    items: list[ItemIn]
    boxes: Optional[list[BoxIn]] = Field(
        default=None, description="Omit to use the default 6-box catalogue")
    config: Optional[ConfigIn] = None
    strategy: str = Field(default="first_fit", pattern="^(first_fit|best_fit)$")


class PlacementOut(BaseModel):
    code: str
    index: int
    x: float
    y: float
    z: float
    dx: float
    dy: float
    dz: float


class CartonOut(BaseModel):
    box_code: str
    item_count: int
    packed_weight: float
    utilization_pct: float
    placements: list[PlacementOut]


class UnpackedOut(BaseModel):
    code: str
    index: int
    reason: str


class PackResponse(BaseModel):
    status: str
    strategy: str
    carton_count: int
    cartons: list[CartonOut]
    unpacked: list[UnpackedOut]
    runtime_ms: float
    violations: list[str]


# ---------------------------------------------------------------------------
# Core logic (kept separate from the route so it can be unit-tested without
# a running HTTP server)
# ---------------------------------------------------------------------------

def solve(request: PackRequest) -> PackResponse:
    engine = ENGINES[request.strategy]

    items = [engine.Item(code=i.code, length=i.length, width=i.width, height=i.height,
                         weight=i.weight, quantity=i.quantity,
                         vertical_rotation=i.vertical_rotation)
             for i in request.items]

    if request.boxes:
        boxes = [engine.Box(code=b.code, length=b.length, width=b.width,
                            height=b.height, max_weight=b.max_weight)
                 for b in request.boxes]
    else:
        boxes = engine.DEFAULT_BOXES

    cfg = engine.Config(**request.config.model_dump()) if request.config else engine.Config()

    result = engine.pack_order(items, boxes, cfg)
    violations = engine.validate_result(result, cfg)

    cartons_out = [
        CartonOut(
            box_code=c.box.code,
            item_count=c.item_count,
            packed_weight=round(c.packed_weight, 3),
            utilization_pct=round(c.utilization_pct, 2),
            placements=[
                PlacementOut(code=p.unit.code, index=p.unit.index,
                            x=p.x, y=p.y, z=p.z, dx=p.dx, dy=p.dy, dz=p.dz)
                for p in c.placements
            ],
        )
        for c in result.cartons
    ]

    unpacked_out = [
        UnpackedOut(code=u.unit.code, index=u.unit.index, reason=u.reason)
        for u in result.unpacked
    ]

    return PackResponse(
        status=result.status,
        strategy=request.strategy,
        carton_count=result.carton_count,
        cartons=cartons_out,
        unpacked=unpacked_out,
        runtime_ms=round(result.runtime_s * 1000, 3),
        violations=violations,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    """Liveness check."""
    return {"status": "ok"}


@app.get("/boxes")
def default_boxes(strategy: str = "first_fit"):
    """Returns the default box catalogue used when a request omits `boxes`."""
    if strategy not in ENGINES:
        raise HTTPException(400, f"Unknown strategy '{strategy}'. Use 'first_fit' or 'best_fit'.")
    engine = ENGINES[strategy]
    return [{"code": b.code, "length": b.length, "width": b.width,
             "height": b.height, "max_weight": b.max_weight} for b in engine.DEFAULT_BOXES]


@app.post("/pack", response_model=PackResponse)
def pack(request: PackRequest):
    """
    Accepts item dimensions/weights (and optionally a box catalogue and
    packing rules) and returns the recommended carton(s), where every item
    goes, and whether anything couldn't be packed.
    """
    if not request.items:
        raise HTTPException(400, "At least one item is required.")
    try:
        return solve(request)
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(500, f"Packing failed: {exc}") from exc
