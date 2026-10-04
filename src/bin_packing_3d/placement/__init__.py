"""Shared placement mechanics for 3D packing strategies."""
from .geometry import candidate_positions, feasible_placements, placement_envelope_volume

__all__ = ["candidate_positions", "feasible_placements", "placement_envelope_volume"]
