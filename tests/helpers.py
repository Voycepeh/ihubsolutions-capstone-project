from bin_packing_3d.models import PackingPlan, PackedBox, Placement, Position
from bin_packing_3d.rules import allowed_orientations, usable_dimensions


class RowSolver:
    """Test-only solver placing items consecutively along X."""
    name = "fake"

    def solve(self, items, boxes, config):
        box = boxes[-1]
        instance = "carton-1"
        x = 0.0
        placements = []
        for item in items:
            orientation = allowed_orientations(item)[0]
            placements.append(Placement(item.instance_id, item.code, instance, orientation, Position(x, 0, 0)))
            x += orientation.length
        return PackingPlan([PackedBox(box.code, instance, usable_dimensions(box, config), placements)])


def assert_solver_contract(solver, items, boxes, config):
    """Reusable contract helper for future solver implementations."""
    from bin_packing_3d.models import PackingPlan
    from bin_packing_3d.validate import validate_plan
    plan = solver.solve(items, boxes, config)
    assert isinstance(plan, PackingPlan)
    assert validate_plan(plan, items, boxes, config).valid
