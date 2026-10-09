# 3D Bin Packing Solver

NUS Industry 4.0 Master's capstone project for practical 3D carton recommendation using masked iHub order data.

The package takes an order and carton catalogue, applies configurable packing rules, and returns a validated carton recommendation with item orientations and XYZ placements.

<details>
<summary><h2>Public API</h2></summary>


```python
from bin_packing_3d import solve_order

result = solve_order(
    order=order,
    boxes=boxes,
    mode="fast",
    high_item_count_threshold=6,
    high_item_count_max_fill_pct=70,
    max_fill_pct=100,
    bin_buffer={"length": 0, "width": 0, "height": 6},
    max_runtime_ms=900,
    deterministic=True,
    logs=False,
    visualize=False,
)
```

Only `order` and `boxes` are required. The remaining arguments have defaults.

The normal solver choice is:

| Mode | Use when |
| --- | --- |
| `fast` | Low latency is the priority |
| `best` | Better carton optimization justifies additional computation |

Best starts from the Fast result, then uses its remaining runtime budget to search for a better packing. If the search budget is exhausted, the validated Fast result remains the fallback.


</details>

<details>
<summary><h2>Inputs</h2></summary>


### Order

The order contains identifiers and the items to pack.

```python
order = {
    "OrderId": 1,
    "OrderNo": "ORDER-001",
    "Items": [
        {
            "Code": "SKU-001",
            "Length": 120,
            "Width": 80,
            "Height": 50,
            "Weight": 0.5,
            "Quantity": 2,
            "VerticalRotation": 1,
        }
    ],
}
```

| Field | Meaning |
| --- | --- |
| `Code` | Item identifier |
| `Length`, `Width`, `Height` | Item dimensions in millimetres |
| `Weight` | Unit weight in kilograms |
| `Quantity` | Number of physical units |
| `VerticalRotation` | Whether vertical rotation is allowed |

`Quantity` is expanded into individual physical items before packing.

### Carton catalogue

Cartons are supplied by the caller. They are not hard coded into the package.

```python
boxes = [
    {
        "Code": "Box2",
        "Length": 270,
        "Width": 170,
        "Height": 115,
        "MaxWeight": 20,
    },
    {
        "Code": "Box4",
        "Length": 340,
        "Width": 260,
        "Height": 150,
        "MaxWeight": 20,
    },
]
```

Each carton requires a code, dimensions in millimetres, and maximum weight in kilograms.

### Packing configuration

The defaults reproduce the current project packing policy.

| Argument | Default | Meaning |
| --- | ---: | --- |
| `mode` | `"fast"` | `fast` or `best` solver |
| `high_item_count_threshold` | `6` | Item count after which the stricter fill limit applies |
| `high_item_count_max_fill_pct` | `70` | Maximum usable volume fill above the threshold |
| `max_fill_pct` | `100` | Normal maximum usable volume fill |
| `bin_buffer` | height `6` mm | Clearance removed from usable carton dimensions |
| `max_runtime_ms` | `900` | Search budget |
| `deterministic` | `True` | Use deterministic solver behavior |
| `logs` | `False` | Print packing decisions |
| `visualize` | `False` | Display the validated 3D packing |

With the defaults, six or fewer physical items may use up to 100% of usable carton volume. More than six are capped at 70%. Carton weight, usable dimensions, item rotation, collision, and fill constraints are enforced by the solver and final validator.


</details>

<details>
<summary><h2>Output</h2></summary>


`solve_order()` returns a `PackingResult`.

```python
print(result)

result.packed_boxes
result.placements
result.metrics
result.validation
result.optimality_proven
result.search_status
```

The result contains:

| Output | Meaning |
| --- | --- |
| `status` | Solver result status |
| `strategy` | Internal strategy used |
| `packed_boxes` | Selected carton instances and their placements |
| `placements` | Flattened item placements across cartons |
| `runtime_ms` | Measured solver runtime |
| `metrics` | Carton count, utilization, packed volume and per carton metrics |
| `validation` | Independent validation result |
| `optimality_proven` | Whether Best proved the selected carton objective |
| `search_status` | Heuristic, optimal, or time limit status |

Each placement records the physical item, selected orientation, and XYZ position in millimetres.

For a JSON compatible representation:

```python
payload = result.to_dict()
```


</details>

<details>
<summary><h2>Optional decision logs</h2></summary>


Enable logs when you want to inspect why cartons or placements were selected or rejected.

```python
result = solve_order(
    order=order,
    boxes=boxes,
    mode="fast",
    logs=True,
)
```

```text
=== 3D packing log ===

Order summary
Physical items         | 8
Total item volume      | 5,883,400 mm^3
Total item weight      | 2.5305 kg
Effective maximum fill | 70%

Candidate cartons
Box2 | REJECTED by volume
Box4 | PASSED screen; evaluated during 3D search
Box8 | PASSED screen; evaluated during 3D search

3D search decisions
9#1  | Box4 | PLACED | best-scoring new carton and 3D placement
30#1 | Box4 | PLACED | best-scoring feasible position

Final decision
Selected carton(s): Box4
```

Logging does not change the packing result.


</details>

<details>
<summary><h2>Optional 3D visualization</h2></summary>


Set `visualize=True` to display the validated item cuboids inside the selected carton.

```python
result = solve_order(
    order=order,
    boxes=boxes,
    mode="best",
    visualize=True,
)
```

![Validated Box4 packing for sample order 80](docs/images/order80_box4_visualization.png)

The visualization is for inspection and explanation. The XYZ coordinates establish a valid geometric packing and are not intended as exact instructions for a ground packer to reproduce.


</details>

<details>
<summary><h2>High level architecture</h2></summary>


```mermaid
flowchart LR
    I["Order + carton catalogue<br/>optional configuration"] --> API["solve_order()"]
    API --> N["Normalize inputs<br/>expand quantity<br/>apply rules"]
    N --> M{"Fast or Best"}

    M -->|Fast| F["Fast<br/>heuristic search"]
    M -->|Best| B["Best<br/>Fast fallback + configurable search"]

    F --> V["Independent validation"]
    B --> V
    V --> R["PackingResult<br/>cartons + XYZ + metrics"]
```

The public API owns normalization and orchestration. Fast and Best propose packing plans. The engine independently validates the selected plan before returning it.

> **Strategies propose. The engine validates.**

For implementation details, use the dedicated Fast and Best guides below rather than the README.


</details>

<details>
<summary><h2>Constraint validation: proving the solver respects our rules</h2></summary>

A packing recommendation is only useful if it is **valid**. Fast and Best may search differently, but both must pass the **same independent final validator** before their results are accepted. This is separate from benchmarking carton count and execution time: a faster or smaller packing is not a win if it violates a rule.

| Rule | What we verify |
| --- | --- |
| Carton dimensions and clearance | Every placed item stays inside the usable carton length, width, and height after the configured buffer (default: 6 mm height) |
| Physical placement | No two items overlap in three-dimensional space |
| Allowed orientations | Every item uses an orientation permitted by its `VerticalRotation` setting |
| Maximum carton weight | Sum of placed item weights does not exceed that carton's configured `MaxWeight` |
| Volume fill policy | Up to 6 physical items: at most 100% fill; above 6: at most 70% fill by default, calculated against usable carton volume |
| Complete, unique packing | Each physical unit (including expanded `Quantity`) is placed exactly once, with no missing or duplicated units |
| Configurable rules and catalogue | Changed carton dimensions, weights, fill thresholds, and clearance values are reflected in acceptance or rejection |

**How to see the rules in action:** Run the [Solver Guardrail Simulation](notebooks/Simulated%20Rule%20Proof.ipynb). Its Config + Items + Boxes scenarios exercise the real solver and show how a rule can cause a carton to be skipped, a different carton to be selected, or an order to be rejected. Inspect `result.validation` alongside `result.packed_boxes` and `result.placements` to distinguish validation from the solver's choice.

**How to assess correctness:** For each scenario, check both a valid boundary case and an invalid case, then assert the expected outcome. The independent validator should reject invalid coordinates, collisions, prohibited rotations, overweight cartons, excessive fill, and missing or duplicate units even if a search strategy proposes them. A solver returning no feasible packing is different from returning an invalid packing.

Only **validated** recommendations should be included when comparing Fast and Best on cartons used, utilization, or latency. This section describes the verification criteria and executable demonstration; it does **not** claim that every case above has already passed automated tests.

</details>

<details>
<summary><h2>Fast vs Best: Execution Time</h2></summary>


Best does more work because it starts with the Fast packing and then searches alternative carton combinations with an exact 3D feasibility model. As the order contains more items and the catalogue contains more carton types, there are more carton combinations, assignments, orientations, positions, and non-overlap relationships to evaluate.

### Escape hatch: bounded Best search

The public API lets callers bound how long Best is allowed to search using `max_runtime_ms`. Best always starts with a validated Fast packing, so the optimization search has a safe fallback. If the Best search reaches its configured time limit before finding or proving a better solution, the solver returns the validated Fast result rather than failing the order.

```python
result = solve_order(
    order=order,
    boxes=boxes,
    mode="best",
    max_runtime_ms=5_000,  # 5 second Best search budget
)
```

This makes Best a deliberate tradeoff: callers can give the optimizer more time when carton reduction matters, or keep the search tightly bounded when response time matters.

### Solver execution time: Fast vs Best

The benchmark compares **8 order sizes × 5 box catalogue sizes × 2 solving modes × 3 repeats** (240 executions). Each larger synthetic order retains the items from the smaller order for the same seed. These runs use uncapped search (`max_runtime_ms=None`), so they are **not production API latency guarantees**. All three charts below use the committed [benchmark summary](benchmark_results/solver_scaling/summary.csv); each cell is the median of three runs.

#### 1. Fast execution time

![Fast solver execution-time heatmap](benchmark_results/solver_scaling/solver_scaling_fast_heatmap.svg)

#### 2. Best execution time

![Best solver execution-time heatmap](benchmark_results/solver_scaling/solver_scaling_best_heatmap.svg)

**Reading the heatmaps:** Rows show items per order; columns show available box types (3, 5, 10, 15, 20). Labels are median seconds. Both use the **same logarithmic teal color scale**: darker means slower. Compare matching cells across the two charts. The color scale is logarithmic to preserve differences between millisecond-scale and minute-scale scenarios.

#### 3. Fast baseline vs additional Best runtime

![Fast baseline and estimated additional Best runtime across all eight item counts](benchmark_results/solver_scaling/solver_scaling_best_breakdown.svg)

This chart focuses on **20 available box types**, across **all eight item counts**. Teal is the separately measured Fast median; orange is **Best median minus Fast median**. The full bar equals Best's median runtime. The orange portion is an **estimate of additional time**, not a directly instrumented stage within Best.

#### What the results tell us

- **Runtime is not proportional to item count.** With 20 box types, Fast takes **12.68 s for 50 items**, but **4.98 s for 75 items**. Packing difficulty and the alternatives searched matter more than item count alone.
- **Best generally takes longer.** It starts with Fast's valid solution, then uses an exact constraint solver to evaluate alternatives and prove the carton-count objective when possible. The additional work depends on carton combinations, orientations, and three-dimensional non-overlap constraints.
- **More box types can increase search cost.** A larger catalogue gives the solver more carton alternatives, although some scenarios can be rejected quickly.

**Profiling insight:** A separate six-case profiling investigation of 50 versus 75 items found median `feasible_placements()` call counts of **12,771** and **3,909**, respectively (about **3.3×** more checks for 50 items). Almost all profiled time occurred in the search for fewer cartons rather than the initial greedy packing. Early candidate rejection and changes in placement order are plausible mechanisms, but the profiler did not record the exact rejection points. See the [diagnostic workflow](https://github.com/Voycepeh/ihubsolutions-capstone-project/actions/runs/37878918335).

**Reproducibility:** [Benchmark script](notebooks/benchmark_solver_scaling.py) · [Committed summary](benchmark_results/solver_scaling/summary.csv) · [Individual runs](benchmark_results/solver_scaling/raw_results.csv) · [Original completed benchmark artifact](https://github.com/Voycepeh/ihubsolutions-capstone-project/actions/runs/37873447275/artifacts/11591919183). Chart values in this section are sourced from the committed summary; the original artifact should be reconciled separately before claiming the two are identical.

</details>

<details>
<summary><h2>Documentation</h2></summary>


| Document | Purpose |
| --- | --- |
| [Fast solver under the hood](docs/fast-solver-under-the-hood.md) | Fast heuristic, placement scoring and bounded carton search |
| [Best solver under the hood](docs/best-solver-under-the-hood.md) | Best search and Google OR-Tools Constraint Programming Satisfiability integration |
| [Product specification](src/PRODUCT_SPEC.md) | Detailed functional rules and API contract |
| [Research and literature](docs/solver-approach-and-literature.md) | Academic references and rationale for the chosen approach |
| [Development datasets](data/raw/README.md) | v1/v2 schemas, carton catalogues and packing parameters ([change log](data/raw/CHANGELOG.md)) |
| [Solver Demo](notebooks/Solver%20Demo.ipynb) | Worked examples, Fast/Best/iHub comparisons, visualization, and the 2,000-order benchmark |
| [Solver Guardrail Simulation](notebooks/Simulated%20Rule%20Proof.ipynb) | Executable Config + Items + Boxes scenarios showing the real solver skipping cartons, choosing fallbacks, or rejecting orders when guardrails apply |

Historical iHub carton choices are used only as reference results for evaluation. They are not passed into `solve_order()` and do not determine the solver recommendation.


</details>