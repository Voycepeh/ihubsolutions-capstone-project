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
<summary><h2>Why Best is computationally heavy</h2></summary>


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

### Fast vs Best latency: uncapped benchmark

The comparison below uses **20 available carton types** and shows Fast and Best in two side-by-side bar charts with the same vertical scale. Each bar is the **median of three runs**. Both modes receive the same synthetic order and carton catalogue for each case.

![Fast versus Best solver latency, side-by-side bars](benchmark_results/solver_scaling/solver_scaling_fast_vs_best.svg)

The benchmark covers **5, 10, 15, 20, 30, 50, 75, and 100 items**, **3, 5, 10, 15, and 20 available carton types**, **three repeats**, and both modes: **240 executions** in total. Each larger order retains all items from the smaller order for the same seed, with varied item dimensions, weights, and rotation settings. The benchmark passes `max_runtime_ms=None` so the solver search is **not capped**. This differs from the public API's default 900 ms search budget.

| Items (20 box types) | Fast median | Best median |
| ---: | ---: | ---: |
| 5 | 0.01 s | 0.02 s |
| 10 | 0.06 s | 0.11 s |
| 15 | 0.13 s | 0.24 s |
| 20 | 0.22 s | 0.41 s |
| 30 | 0.30 s | 0.73 s |
| 50 | 11.28 s | 19.21 s |
| 75 | 3.24 s | 16.40 s |
| 100 | 83.81 s | 105.83 s |

**Interpretation:** Best takes longer because it starts with Fast and evaluates additional packing alternatives. For 100 items and 20 carton types, the median was approximately **84 seconds for Fast** versus **106 seconds for Best**. Latency does not increase monotonically with item count because the packing difficulty and search branches can change as items are added. Best reported optimal solutions in all three repeats of that largest scenario. Optimality is about the carton-count objective, not proof that Best is the fastest mode.

These are **synthetic scaling results**, not production latency guarantees. The measured runtime covers solver execution, not full application request overhead. The benchmark records `cartons_used` for both modes so carton reduction can be assessed separately from latency.

**Reproducibility:** [Benchmark script](notebooks/benchmark_solver_scaling.py) · [Completed 240-run results and charts](https://github.com/Voycepeh/ihubsolutions-capstone-project/actions/runs/37873447275/artifacts/11591919183) · [Chart regeneration workflow](.github/workflows/tests.yml). Chart-only changes should reuse the completed CSV results rather than rerun the solver grid.

</details>

<details>
<summary><h2>Documentation</h2></summary>


| Document | Purpose |
| --- | --- |
| [Fast solver under the hood](docs/fast-solver-under-the-hood.md) | Fast heuristic, placement scoring and bounded carton search |
| [Best solver under the hood](docs/best-solver-under-the-hood.md) | Best search and Google OR-Tools Constraint Programming Satisfiability integration |
| [Product specification](src/PRODUCT_SPEC.md) | Detailed functional rules and API contract |
| [Solver approach and literature](docs/solver-approach-and-literature.md) | Research and solver design rationale |
| [Dataset specification](docs/dataset-specification.md) | Supplied development data and fields |
| [Solver Demo](notebooks/Solver%20Demo.ipynb) | Worked examples, Fast/Best/iHub comparisons, visualization, and the 2,000-order benchmark |
| [Solver Guardrail Simulation](notebooks/Simulated%20Rule%20Proof.ipynb) | Executable Config + Items + Boxes scenarios showing the real solver skipping cartons, choosing fallbacks, or rejecting orders when guardrails apply |

Historical iHub carton choices are used only as reference results for evaluation. They are not passed into `solve_order()` and do not determine the solver recommendation.


</details>