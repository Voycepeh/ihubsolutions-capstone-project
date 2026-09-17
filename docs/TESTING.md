# Testing

Tests are part of each implementation milestone rather than a final cleanup step.

## MVP 0 unit tests

The first tests are intentionally small and manually verifiable.

| Test | Expected result |
| --- | --- |
| Simple cube fits | Item `10×10×10` fits in `20×20×20`; XYZ is `0,0,0` |
| One dimension too large | Item `30×10×10` is rejected by `20×20×20` |
| Fall back to larger carton | Same item selects `40×20×20` when supplied |
| Rotation makes fit possible | Packing succeeds when an allowed 90-degree turn makes dimensions fit |
| Rotation restriction blocks fit | Upright-only item rejects a carton that requires changing vertical axis |
| Weight too high | Carton is rejected when item weight exceeds `max_weight` |
| Quantity expansion | Quantity `2` creates two physical item results and two cartons in MVP 0 |
| Smallest fitting carton | When several cartons fit, the lowest-volume carton is selected |
| Rectangular dimensions | Non-cube item and carton are checked dimension by dimension |
| No carton fits | Physical item is returned in `not_packed_items` |

The core MVP 0 assertion is:

> If any required X, Y or Z extent of an allowed orientation is larger than the usable carton extent on that axis, that orientation must be rejected.

## Planned test modules

```text
tests/
  test_models.py
  test_normalize.py
  test_orientation.py
  test_feasibility.py
  test_single_item.py
  test_solve_order.py
```

Later milestones add geometry, remaining-empty-space, First Fit, Best Fit, multi-carton and benchmark tests.

## Test rules

1. Every new solver module ships with unit tests.
2. Constructed geometry cases should be understandable by inspection.
3. Public request and response field names should remain stable once implementation begins.
4. Invalid inputs must fail clearly rather than being silently corrected.
5. Unpackable items must be reported explicitly.
6. Repeated execution with identical input and configuration should produce the same result for deterministic stages.
7. Historical iHub benchmark runs stay separate from normal unit tests because they measure solution quality and runtime rather than basic correctness.

The detailed future test contracts remain in [`../src/PRODUCT_SPEC.md`](../src/PRODUCT_SPEC.md).
