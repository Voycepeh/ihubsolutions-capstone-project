import pytest
from bin_packing_3d.models import UnknownStrategyError
from bin_packing_3d.solvers import get_solver, list_registered_solvers, register_solver
from tests.helpers import RowSolver


def test_registration_retrieval_and_deterministic_listing():
    one=RowSolver(); two=RowSolver()
    register_solver("zeta",one); register_solver("alpha",two)
    assert get_solver("zeta") is one
    assert list_registered_solvers() == ("alpha","zeta")

def test_duplicate_registration_is_explicit():
    register_solver("fake",RowSolver())
    with pytest.raises(ValueError,match="already registered"): register_solver("fake",RowSolver())

def test_unknown_strategy_has_domain_error():
    with pytest.raises(UnknownStrategyError,match="missing"): get_solver("missing")
