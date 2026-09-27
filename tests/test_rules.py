import pytest

from bin_packing_3d.models import InvalidConfigError, InvalidInputError, Item, Orientation, UnpackableItemError
from bin_packing_3d.rules import (allowed_orientations, ensure_individual_feasibility, expand_items,
    fill_cap_applies, normalize_boxes, normalize_config, normalize_order, usable_dimensions)


def item(**changes):
    values = dict(Code="A", Length=10, Width=5, Height=2, Weight=1, Quantity=1, VerticalRotation=1)
    values.update(changes); return values


def box(**changes):
    values = dict(Code="B", Length=20, Width=20, Height=20, MaxWeight=10)
    values.update(changes); return values


def test_quantity_expands_to_stable_unique_ids():
    _, _, items = normalize_order({"Items": [item(Quantity=3)]})
    assert [i.instance_id for i in expand_items(items)] == ["A#1", "A#2", "A#3"]

@pytest.mark.parametrize("change", [{"Length": 0}, {"Width": -1}, {"Weight": 0}, {"Quantity": 0}, {"Quantity": 1.5}])
def test_invalid_items_are_rejected(change):
    with pytest.raises(InvalidInputError): normalize_order({"Items": [item(**change)]})

def test_missing_item_field_is_rejected():
    raw=item(); del raw["Height"]
    with pytest.raises(InvalidInputError, match="Height"): normalize_order({"Items": [raw]})

@pytest.mark.parametrize("boxes", [[], [{"Code":"B"}], [{"Code":"B","Length":1,"Width":1,"Height":1,"MaxWeight":-1}]])
def test_bad_carton_catalogues_are_rejected(boxes):
    with pytest.raises(InvalidInputError): normalize_boxes(boxes)

def test_orientation_rules_and_duplicate_removal():
    rotating = Item("A", 1, 2, 3, 1, 1, True)
    upright = Item("A", 1, 2, 3, 1, 1, False)
    cube = Item("C", 2, 2, 2, 1, 1, True)
    assert len(allowed_orientations(rotating)) == 6
    assert allowed_orientations(upright) == (Orientation(1,2,3), Orientation(2,1,3))
    assert allowed_orientations(cube) == (Orientation(2,2,2),)

@pytest.mark.parametrize("config", [
    {"bin_buffer":{"length":-1}}, {"bin_max_fill_pct":0}, {"bin_max_fill_pct":101},
    {"max_runtime_ms":0}, {"bin_max_fill_check_min_item_qty":-1}, {"strategy":""},
])
def test_invalid_config_is_rejected(config):
    with pytest.raises(InvalidConfigError): normalize_config(config)

def test_buffer_reduces_usable_dimensions_and_cannot_consume_carton():
    cfg=normalize_config({"bin_buffer":{"length":1,"width":2,"height":3}})
    assert usable_dimensions(normalize_boxes([box()])[0], cfg) == Orientation(19,18,17)
    with pytest.raises(InvalidConfigError): usable_dimensions(normalize_boxes([box()])[0], normalize_config({"bin_buffer":{"length":20}}))

def test_fill_threshold_boundary():
    cfg=normalize_config({})
    assert not fill_cap_applies(5,cfg)
    assert not fill_cap_applies(6,cfg)
    assert fill_cap_applies(7,cfg)

def test_dimension_precheck_rejects_false_volume_fit_and_overweight():
    cfg=normalize_config({"bin_buffer":{"height":0}}); boxes=normalize_boxes([box()])
    _,_,source=normalize_order({"Items":[item(Length=30,Width=10,Height=20)]})
    with pytest.raises(UnpackableItemError): ensure_individual_feasibility(expand_items(source),boxes,cfg)
    _,_,source=normalize_order({"Items":[item(Weight=11)]})
    with pytest.raises(UnpackableItemError): ensure_individual_feasibility(expand_items(source),boxes,cfg)
