# Engine Test Strategy

Tests follow [`../src/PRODUCT_SPEC.md`](../src/PRODUCT_SPEC.md) and use small, manually understandable geometry. They do not depend on unfinished First Fit or Best Fit implementations.

- `test_rules.py`: normalization, configuration, expansion, orientation, buffer, threshold, and individual feasibility.
- `test_registry.py`: deterministic registration, lookup, duplicates, and unknown strategies.
- `test_validate.py`: independent accounting, orientation, boundary, overlap/touching, weight, fill, and carton checks.
- `test_engine.py`: complete fake-solver flow, rejection of incomplete/all-unpacked plans, failure handling, metrics, JSON serialization, and solver contract compatibility.
- `helpers.py`: a deliberately simple test-only solver and reusable `assert_solver_contract` helper for future plugins.

The geometry fixtures include two `15 × 10 × 10` items in a `20 × 20 × 20` carton and the impossible `30 × 10 × 20` item. Future solver suites may call `assert_solver_contract`; they must not assert identical arrangements across strategies. Dataset benchmarking and First Fit versus Best Fit conclusions remain outside unit tests and `solve_order()`.
