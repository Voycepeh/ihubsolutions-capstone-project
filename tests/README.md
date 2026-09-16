# Solver Test Strategy

Tests should be created together with each solver component rather than after the complete engine is built.

The functional expectations for every module are defined in [`../src/PRODUCT_SPEC.md`](../src/PRODUCT_SPEC.md). This folder will contain the executable tests that prove those contracts.

## Planned Structure

```text
tests/
  test_normalize.py
  test_orientation.py
  test_feasibility.py
  test_geometry.py
  test_spaces.py
  test_placement.py
  test_single_box.py
  test_multi_box.py
  test_improve.py
  test_validate.py
  test_solve_order.py
  fixtures/
```

## Test Rules

1. Every new solver module must be introduced with its unit tests.
2. Geometry tests should use small constructed cases where the expected answer can be reasoned about manually.
3. EMS behavior must be tested independently from placement behavior: initial space creation, splitting, duplicate removal, containment pruning, fit based pruning, candidate generation and configured space caps.
4. A successful packing result must always pass the independent validator.
5. Regression fixtures should be added whenever a bug is found so the same behavior cannot silently return.
6. Historical iHub dataset benchmarking should remain separate from normal unit tests because benchmark comparison measures performance and solution quality rather than basic correctness.
7. Tests should remain deterministic. Randomized search is outside the initial MVP.

## Required Early Geometry Fixtures

A `20 x 20 x 20` carton containing two `15 x 10 x 10` items must produce a valid non overlapping placement.

A `20 x 20 x 20` carton containing one `30 x 10 x 20` item must fail because no legal orientation fits inside the carton, even though volume alone is not the relevant proof.

A constructed EMS fixture must place one cuboid into an empty carton, update the remaining empty spaces, remove contained or duplicate spaces, and preserve at least one valid region for a second known item.

These fixtures are intended to make the XYZ solver understandable before more complicated benchmark orders are introduced.
