# Solver Test Strategy

Tests should be created together with each solver component rather than after the complete engine is built.

The functional expectations for every module are defined in [`../src/PRODUCT_SPEC.md`](../src/PRODUCT_SPEC.md). The shared terminology guide is [`../docs/TERMINOLOGY.md`](../docs/TERMINOLOGY.md).

## Planned Structure

```text
tests/
  test_normalize.py
  test_orientation.py
  test_feasibility.py
  test_geometry.py
  test_spaces.py
  test_placement.py
  test_strategies.py
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
3. Remaining-empty-space behavior must be tested independently from placement behavior: initial space creation, splitting, duplicate removal, contained-space removal, fit-based removal, candidate-position generation and configured space caps.
4. First Fit and Best Fit must use the same ordered candidate generator and the same geometry and business constraints.
5. First Fit tests must prove that search stops at the first valid candidate.
6. Best Fit tests must prove that all available valid candidates within the configured limits are considered before selection.
7. A successful packing result must always pass the independent validator.
8. Regression fixtures should be added whenever a bug is found so the same behavior cannot silently return.
9. Historical iHub dataset benchmarking should remain separate from normal unit tests because benchmark comparison measures performance and solution quality rather than basic correctness.
10. Tests should remain repeatable: the same input and settings should produce the same result.

## Required Early Geometry Fixtures

A `20 x 20 x 20` carton containing two `15 x 10 x 10` rectangular items must produce a valid non-overlapping placement.

A `20 x 20 x 20` carton containing one `30 x 10 x 20` item must fail because no allowed orientation fits inside the carton, even though volume alone is not the relevant proof.

A constructed empty-space fixture must place one rectangular item into an empty carton, update the remaining empty rectangular spaces, remove contained or duplicate spaces, and preserve at least one valid region for a second known item.

A strategy fixture must expose more than one valid candidate position so First Fit can be shown to stop at the first candidate while Best Fit evaluates the same candidates and may choose a different placement.

These fixtures are intended to make the XYZ solver and the First Fit versus Best Fit tradeoff understandable before more complicated benchmark orders are introduced.
