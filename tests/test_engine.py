import json
import pytest

from bin_packing_3d import register_solver, solve_order
from bin_packing_3d.models import InvalidPackingPlanError, PackingPlan, UnpackableItemError, UnknownStrategyError
from bin_packing_3d.rules import expand_items, normalize_boxes, normalize_config, normalize_order
from tests.helpers import RowSolver, assert_solver_contract

ORDER={"OrderId":42,"OrderNo":"N-42","Items":[{"Code":"A","Length":5,"Width":5,"Height":5,"Weight":1,"Quantity":2,"VerticalRotation":0}]}
BOXES=[{"Code":"B","Length":20,"Width":10,"Height":10,"MaxWeight":10}]
CONFIG={"strategy":"fake","bin_buffer":{"height":0}}


def test_complete_engine_flow_metrics_and_json_serialization():
    register_solver("fake",RowSolver())
    result=solve_order(ORDER,BOXES,CONFIG)
    assert result.status == "success" and result.validation.valid
    assert result.order_id == 42 and result.order_number == "N-42"
    assert result.metrics.box_count == 1
    assert result.metrics.packed_item_count == 2 and result.metrics.unpacked_item_count == 0
    assert result.metrics.total_external_box_volume == 2000
    assert result.metrics.total_packed_item_volume == 250
    assert result.metrics.overall_utilization_pct == 12.5
    assert result.runtime_ms == result.metrics.runtime_ms
    json.dumps(result.to_dict())

def test_solver_contract_helper():
    _,_,source=normalize_order(ORDER)
    assert_solver_contract(RowSolver(),expand_items(source),normalize_boxes(BOXES),normalize_config(CONFIG))

def test_unknown_strategy_fails_clearly():
    with pytest.raises(UnknownStrategyError): solve_order(ORDER,BOXES,{"strategy":"missing","bin_buffer":{"height":0}})

def test_precheck_fails_before_solver_is_called():
    class ShouldNotRun:
        name="fake"
        def solve(self,*args): raise AssertionError("solver was called")
    register_solver("fake",ShouldNotRun())
    impossible={"Items":[{"Code":"A","Length":30,"Width":10,"Height":20,"Weight":1,"Quantity":1,"VerticalRotation":1}]}
    with pytest.raises(UnpackableItemError): solve_order(impossible,[{"Code":"B","Length":20,"Width":20,"Height":20,"MaxWeight":10}],CONFIG)

def test_invalid_solver_plan_is_rejected():
    class EmptySolver:
        name="empty"
        def solve(self,items,boxes,config): return PackingPlan()
    register_solver("empty",EmptySolver())
    with pytest.raises(InvalidPackingPlanError) as exc:
        solve_order(ORDER,BOXES,{"strategy":"empty","bin_buffer":{"height":0}})
    assert {e.code for e in exc.value.validation.errors} == {"missing_item"}

def test_all_items_unpacked_cannot_be_reported_as_success():
    class AllUnpackedSolver:
        name="all_unpacked"
        def solve(self,items,boxes,config):
            return PackingPlan(unpacked_item_ids=[item.instance_id for item in items])
    register_solver("all_unpacked",AllUnpackedSolver())
    with pytest.raises(InvalidPackingPlanError) as exc:
        solve_order(ORDER,BOXES,{"strategy":"all_unpacked","bin_buffer":{"height":0}})
    assert {e.code for e in exc.value.validation.errors} == {"unpacked_item"}

def test_solver_must_return_standard_plan():
    class BadType:
        name="bad"
        def solve(self,*args): return {}
    register_solver("bad",BadType())
    with pytest.raises(TypeError,match="PackingPlan"): solve_order(ORDER,BOXES,{"strategy":"bad","bin_buffer":{"height":0}})
