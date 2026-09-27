from dataclasses import replace

from bin_packing_3d.models import Box, Item, Orientation, PackedBox, PackingPlan, PhysicalItem, Placement, Position
from bin_packing_3d.rules import normalize_config, usable_dimensions
from bin_packing_3d.validate import validate_plan


def build(item_dimensions=(15,10,10), count=2, box_dimensions=(20,20,20), max_weight=10, weight=1, positions=None, config=None):
    cfg=normalize_config(config or {"bin_buffer":{"height":0}})
    source=Item("A",*item_dimensions,weight,count,False)
    items=[PhysicalItem(f"A#{i+1}",source) for i in range(count)]
    box=Box("B",*box_dimensions,max_weight)
    positions=positions or [Position(0,i*10,0) for i in range(count)]
    placements=[Placement(item.instance_id,"A","B-1",Orientation(*item_dimensions),pos) for item,pos in zip(items,positions)]
    plan=PackingPlan([PackedBox("B","B-1",usable_dimensions(box,cfg),placements)])
    return plan,items,[box],cfg


def codes(result): return {e.code for e in result.errors}

def test_known_two_item_geometry_is_valid_and_touching_is_allowed():
    plan,items,boxes,cfg=build()
    assert validate_plan(plan,items,boxes,cfg).valid

def test_overlap_is_rejected():
    args=build(positions=[Position(0,0,0),Position(5,0,0)])
    assert "overlap" in codes(validate_plan(*args))

def test_exact_boundary_passes_slightly_outside_and_negative_fail():
    plan,items,boxes,cfg=build(count=1, positions=[Position(5,10,10)])
    assert validate_plan(plan,items,boxes,cfg).valid
    plan.packed_boxes[0].placements[0]=replace(plan.placements[0],position=Position(5.001,10,10))
    assert "boundary" in codes(validate_plan(plan,items,boxes,cfg))
    plan.packed_boxes[0].placements[0]=replace(plan.placements[0],position=Position(-0.1,0,0))
    assert "negative_coordinate" in codes(validate_plan(plan,items,boxes,cfg))

def test_weight_exactly_at_limit_passes_and_above_fails():
    assert validate_plan(*build(count=1,weight=10)).valid
    assert "weight" in codes(validate_plan(*build(count=2,weight=6)))

def test_fill_cap_below_and_at_threshold_is_not_applied():
    for count in (5,6):
        plan,items,boxes,cfg=build(item_dimensions=(10,10,1),count=count,box_dimensions=(10,10,10),max_weight=20,
                                   positions=[Position(0,0,i) for i in range(count)])
        assert validate_plan(plan,items,boxes,cfg).valid

def test_fill_cap_exact_percentage_passes_and_above_fails():
    exact=build(item_dimensions=(10,10,1),count=7,box_dimensions=(10,10,10),max_weight=20,
                positions=[Position(0,0,i) for i in range(7)])
    assert validate_plan(*exact).valid
    above=build(item_dimensions=(10,10,1),count=8,box_dimensions=(10,10,10),max_weight=20,
                positions=[Position(0,0,i) for i in range(8)])
    assert "fill_cap" in codes(validate_plan(*above))

def test_blanket_fill_cap_applies_below_high_item_threshold():
    case=build(item_dimensions=(10,10,1),count=5,box_dimensions=(10,10,10),max_weight=20,
               positions=[Position(0,0,i) for i in range(5)],
               config={"bin_buffer":{"height":0},"max_fill_pct":40})
    assert "fill_cap" in codes(validate_plan(*case))

def test_item_accounting_missing_duplicate_unknown_and_reconciled_unpacked():
    plan,items,boxes,cfg=build()
    plan.packed_boxes[0].placements.pop()
    assert "missing_item" in codes(validate_plan(plan,items,boxes,cfg))
    plan.unpacked_item_ids=["A#2"]
    assert validate_plan(plan,items,boxes,cfg).valid
    plan.packed_boxes[0].placements.append(plan.packed_boxes[0].placements[0])
    assert "duplicate_item" in codes(validate_plan(plan,items,boxes,cfg))
    plan.unpacked_item_ids.append("X#1")
    assert "unknown_item" in codes(validate_plan(plan,items,boxes,cfg))

def test_orientation_box_identity_and_usable_dimensions_are_checked():
    plan,items,boxes,cfg=build(count=1)
    plan.packed_boxes[0].placements[0]=replace(plan.placements[0],orientation=Orientation(10,10,15))
    assert "orientation" in codes(validate_plan(plan,items,boxes,cfg))
    plan.packed_boxes[0].box_code="unknown"
    assert "unknown_box" in codes(validate_plan(plan,items,boxes,cfg))
