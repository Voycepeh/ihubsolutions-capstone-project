import pytest

from bin_packing_3d.models import InvalidConfigError, InvalidInputError, Item, Orientation, UnpackableItemError
from bin_packing_3d.rules import (allowed_orientations, ensure_individual_feasibility, expand_items,
    effective_max_fill_pct, normalize_boxes, normalize_config, normalize_order, packing_objective,
    usable_dimensions)


def item(**changes):
    values = dict(Code="A", Length=10, Width=5, Height=2, Weight=1, Quantity=1, VerticalRotation=1)
    values.update(changes); return values


def box(**changes):
    values = dict(Code="B", Length=20, Width=20, Height=20, MaxWeight=10)
    values.update(changes); return values


def test_quantity_expands_to_stable_unique_ids():
    _, _, items = normalize_order({"Items": [item(Quantity=3)]})
    assert [i.instance_id for i in expand_items(items)] == ["A#1", "A#2", "A#3"]

@pytest.mark.parametrize("change", [
    {"Length": 0}, {"Width": -1}, {"Height": float("nan")},
    {"Weight": 0}, {"Weight": float("inf")}, {"Quantity": 0}, {"Quantity": 1.5},
])
def test_invalid_items_are_rejected(change):
    with pytest.raises(InvalidInputError): normalize_order({"Items": [item(**change)]})

def test_missing_item_field_is_rejected():
    raw=item(); del raw["Height"]
    with pytest.raises(InvalidInputError, match="Height"): normalize_order({"Items": [raw]})

@pytest.mark.parametrize("boxes", [
    [], [{"Code":"B"}],
    [{"Code":"B","Length":1,"Width":1,"Height":1,"MaxWeight":-1}],
    [{"Code":"B","Length":float("inf"),"Width":1,"Height":1,"MaxWeight":1}],
])
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
    {"bin_buffer":{"length":-1}}, {"max_fill_pct":0}, {"max_fill_pct":101},
    {"high_item_count_max_fill_pct":0}, {"high_item_count_max_fill_pct":101},
    {"max_fill_pct":float("nan")},
    {"high_item_count_max_fill_pct":float("inf")}, {"max_runtime_ms":0},
    {"max_runtime_ms":float("inf")}, {"bin_buffer":{"width":float("nan")}},
    {"high_item_count_threshold":-1}, {"high_item_count_threshold":1.5}, {"strategy":""}, {"mode":"slow"},
])
def test_invalid_config_is_rejected(config):
    with pytest.raises(InvalidConfigError): normalize_config(config)

def test_buffer_reduces_usable_dimensions_and_cannot_consume_carton():
    cfg=normalize_config({"bin_buffer":{"length":1,"width":2,"height":3}})
    assert usable_dimensions(normalize_boxes([box()])[0], cfg) == Orientation(19,18,17)
    with pytest.raises(InvalidConfigError): usable_dimensions(normalize_boxes([box()])[0], normalize_config({"bin_buffer":{"length":20}}))

@pytest.mark.parametrize(("blanket", "count", "expected"), [
    (90, 5, 90),
    (90, 6, 90),
    (90, 7, 70),
    (100, 6, 100),
    (100, 7, 70),
    (80, 7, 70),
])
def test_effective_fill_percentage_at_threshold_boundaries(blanket, count, expected):
    config = normalize_config({
        "max_fill_pct": blanket,
        "high_item_count_threshold": 6,
        "high_item_count_max_fill_pct": 70,
    })
    assert effective_max_fill_pct(count, config) == expected

def test_expanded_quantity_drives_effective_fill_percentage():
    _, _, source = normalize_order({"Items": [item(Quantity=7)]})
    physical_items = expand_items(source)
    assert len(physical_items) == 7
    assert effective_max_fill_pct(len(physical_items), normalize_config({})) == 70


def test_packing_objective_orders_count_then_largest_then_total_volume():
    assert packing_objective([1000]) < packing_objective([1, 1])
    assert packing_objective([8, 8]) < packing_objective([10, 1])
    assert packing_objective([10, 5]) < packing_objective([10, 6])

def test_source_fill_parameter_names_are_accepted():
    config = normalize_config({
        "BinMaxFillCheckMinItemQty": 4,
        "BinMaxFillPct": 65,
    })
    assert config.high_item_count_threshold == 4
    assert config.high_item_count_max_fill_pct == 65

def test_dimension_precheck_rejects_false_volume_fit_and_overweight():
    cfg=normalize_config({"bin_buffer":{"height":0}}); boxes=normalize_boxes([box()])
    _,_,source=normalize_order({"Items":[item(Length=30,Width=10,Height=20)]})
    with pytest.raises(UnpackableItemError): ensure_individual_feasibility(expand_items(source),boxes,cfg)
    _,_,source=normalize_order({"Items":[item(Weight=11)]})
    with pytest.raises(UnpackableItemError): ensure_individual_feasibility(expand_items(source),boxes,cfg)


def test_user_modes_map_to_internal_strategies():
    assert normalize_config({}).mode == "fast"
    assert normalize_config({}).strategy == "fast_fit"
    assert normalize_config({"mode": "fast"}).strategy == "fast_fit"
    assert normalize_config({"mode": "best"}).strategy == "best_fit"
