import pytest

from bin_packing_3d.solvers import list_registered_solvers, unregister_solver


@pytest.fixture(autouse=True)
def clean_solver_registry():
    for name in list_registered_solvers():
        unregister_solver(name)
    yield
    for name in list_registered_solvers():
        unregister_solver(name)
