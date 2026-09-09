# Solver Approach and Literature Rationale

## Purpose

This document explains why the project is intentionally building a lightweight heuristic 3D cartonization solver rather than treating the capstone as a pure exact optimization exercise.

The distinction matters because three dimensional bin packing is a difficult combinatorial optimization problem. The project should acknowledge that complexity clearly, review relevant solution families, and then justify an engineering approach that is appropriate for the intended outcome: a reusable Python solver that returns valid packing decisions quickly and can later be exposed through an API.

Our objective is therefore not to claim that every returned packing is mathematically optimal. Our objective is to build and evaluate a practical solver that:

1. returns geometrically and operationally valid packings,
2. minimizes carton count as the primary objective,
3. produces good carton utilization as a secondary consideration,
4. respects the supplied business constraints,
5. runs quickly enough for practical use,
6. remains lightweight, explainable and maintainable,
7. can be improved through interchangeable heuristic strategies.

The quality of this approach should be demonstrated empirically rather than assumed. We will benchmark feasibility, carton count, utilization and runtime against the supplied iHub reference outputs, and where practical use lower bounds or stronger methods on small instances to estimate solution quality.

## Problem Context

The classical three dimensional bin packing problem asks how a set of rectangular items can be packed without overlap into the minimum number of three dimensional bins. This is already computationally difficult before additional operational constraints are introduced.

Martello, Pisinger and Vigo describe the 3D bin packing problem as strongly NP hard and develop an exact branch and bound method together with approximation procedures. Their computational study demonstrates that exact optimization is possible for some problem instances, while also illustrating the specialist algorithmic machinery required for exact solution methods [1].

Our project adds practical constraints that are present in the supplied iHub data:

* multiple candidate carton sizes,
* item dimensions and quantities,
* item level rotation restrictions,
* maximum carton weight,
* configurable carton buffer,
* configurable fill limits,
* single and multi carton orders.

The supplied benchmark contains 2,000 successful request and response pairs and uses `bins_number` as the optimization mode. This gives the project a useful real world benchmark, but the historical output should not be treated as proof of mathematical optimality.

## Literature Review

### 1. Exact optimization establishes the problem difficulty

Martello, Pisinger and Vigo formulate the 3D bin packing problem and develop an exact branch and bound algorithm. Their work is important to this project because it establishes two things. First, minimizing the number of three dimensional bins is a formal optimization problem with exact methods. Second, solving it exactly requires specialized algorithms and computation, particularly as instances become more difficult [1].

For this capstone, exact optimization is therefore useful as a conceptual reference and potentially as a benchmark for small test cases. It is not the required architecture for the operational solver.

### 2. Constructive heuristics are established solution methods

Lodi, Martello and Vigo study heuristic algorithms for 3D bin packing and present a tabu search framework that uses a constructive heuristic when evaluating candidate solutions [2]. This is relevant because it shows that practical 3D bin packing research does not rely only on exact mathematical optimization. Constructive heuristics can rapidly produce feasible packings and can also act as the foundation for more advanced search.

This supports the project direction of first producing a deterministic feasible packing and then improving the result when additional computation is worthwhile.

### 3. Greedy solutions can seed improvement search

Færø, Pisinger and Zachariasen propose a guided local search method for 3D bin packing. Their method starts from an upper bound produced by a greedy heuristic and then iteratively searches for packings that use fewer bins [3].

This pattern is highly relevant to our intended design:

```text
Fast feasible solution
        ↓
Current best solution
        ↓
Bounded improvement attempts
        ↓
Best valid solution found within the budget
```

This allows the same solver to return quickly when low latency matters, while supporting additional search when more computation is acceptable.

### 4. Placement strategy is a major part of 3D packing quality

Crainic, Perboli and Tadei introduce extreme point based heuristics for three dimensional bin packing. Their work emphasizes that identifying good candidate placement points inside a container strongly affects the performance of both heuristic and exact methods [4].

This is especially important for our implementation because carton selection alone is not sufficient. The solver also needs a practical geometric placement mechanism that determines where an item can be positioned without overlap and with a permitted orientation.

An extreme point or similar candidate position strategy is therefore a strong potential enhancement after the initial baseline solver is stable.

### 5. Hybrid methods are appropriate for larger and constrained instances

A study published in the JSME International Journal formulates the 3D bin packing problem using mixed integer programming for small instances and proposes a composite algorithm for larger instances with practical constraints [5].

This provides useful support for the project's core tradeoff. Exact formulations are valuable when instance size and computational cost allow them. For larger or operational settings, a composite or heuristic approach can be a more practical engineering choice.

### 6. Industry practice also emphasizes speed and quality tradeoffs

The 3DBinPacking industry article that prompted this review describes practical bin packing as a tradeoff between exact optimization, heuristics, runtime and implementation complexity. It recommends starting with proven heuristics and adding refinement where the business value justifies the additional computation [6].

This is not used as primary academic evidence. It is included as industry context because it aligns with the project's deployment goal: a solver that is useful as software, not only an optimization formulation.

## Chosen Project Position

The project will pursue a heuristic optimization architecture.

We are not saying that optimization is unimportant. We are separating the optimization objective from the requirement to guarantee a global optimum.

The solver should still optimize a clearly defined objective:

1. minimize the number of cartons used,
2. among solutions using the same carton count, prefer lower total carton volume or better utilization,
3. maintain practical runtime.

A simple lexicographic interpretation is:

```text
minimize:
    1. number of cartons
    2. total volume of cartons used
    3. unused carton space
```

subject to all packing constraints.

Runtime is measured alongside solution quality rather than hidden from the evaluation.

## Why This Is Appropriate for the Capstone

The project team is approaching the problem primarily from data and software engineering. The intended deliverable is a reusable Python component that can be integrated into another system.

A research grade exact 3D optimization solver would shift the project heavily toward specialized operations research and mathematical optimization. That is a valid research direction, but it is not necessary to demonstrate a useful engineering contribution.

The proposed approach is defendable because it does not ignore the optimization literature. Instead, it explicitly uses that literature to make a scoped design decision:

* understand the exact problem and its computational difficulty,
* implement a fast constructive baseline,
* validate every returned packing,
* introduce stronger geometric placement and local improvement strategies progressively,
* quantify the tradeoff between packing quality and runtime,
* avoid claiming mathematical optimality unless it has actually been established.

## Proposed Solver Architecture

The solver should remain modular so different team members can improve individual strategies without rewriting the complete packing engine.

```text
Order + Box catalogue + Configuration
                ↓
        Input normalization
                ↓
        Constraint validation
                ↓
          Item ordering
                ↓
      Candidate box selection
                ↓
        3D item placement
                ↓
       Fast feasible solution
                ↓
   Optional bounded improvement
                ↓
     Validate and score result
                ↓
       Explainable output
```

Suggested module boundaries:

```text
src/
├── models.py
├── constraints.py
├── scoring.py
├── solver.py
├── ordering/
│   ├── volume_desc.py
│   └── largest_dimension.py
├── placement/
│   ├── greedy.py
│   └── extreme_point.py
├── selection/
│   ├── first_fit.py
│   └── best_fit.py
└── improvement/
    └── local_search.py
```

The initial version does not need every module above. The important design decision is that ordering, placement, carton selection and improvement strategies should be replaceable rather than tightly coupled.

## Baseline and Progressive Improvement

### Baseline

The first working solver should prioritize correctness and speed:

1. expand item quantities into physical units,
2. generate permitted orientations,
3. sort items using a deterministic decreasing rule,
4. test candidate cartons,
5. place each item at feasible candidate positions,
6. reject overlap and constraint violations,
7. open another carton when required,
8. return a fully validated packing result.

A deterministic baseline is valuable because it is reproducible, easy to test and easy to benchmark.

### Improvement stage

Once the baseline is stable, the team can test enhancements such as:

* alternative item ordering,
* best fit carton selection,
* extreme point placement,
* multiple deterministic restarts with different orderings,
* local repacking,
* bounded local search,
* time budget based search.

The solver may eventually use an anytime style interface where a fast feasible result is produced first and additional computation improves the incumbent solution until a configured limit is reached.

## Evaluation Framework

The phrase "good enough" must be measurable.

The solver will therefore be evaluated across both correctness and optimization quality.

| Area | Proposed metric |
| --- | --- |
| Feasibility | Percentage of orders where every packed item satisfies geometry and business constraints |
| Packing success | Percentage of benchmark orders fully packed |
| Primary objective | Number of cartons used |
| Reference comparison | Carton count match rate against iHub output |
| Secondary quality | Total carton volume and volumetric utilization |
| Constraint compliance | Rotation, weight, fill and buffer violations |
| Multi carton quality | Performance on orders requiring more than one carton |
| Runtime | Median, P95 and maximum runtime |
| Stability | Same input and configuration gives reproducible baseline output |

### Comparing against the historical solution

The iHub output is a reference benchmark rather than mathematical ground truth.

For each order we can classify our result as:

* better than reference on the primary objective,
* equal to reference on carton count,
* worse than reference on carton count,
* invalid or incomplete.

Where carton count is equal, total selected carton volume and utilization can provide a secondary comparison.

### Stronger benchmark for small instances

If time permits, a small subset of simplified instances can be solved using a stronger exact or constraint based method, or compared with a computable lower bound. This would allow the team to estimate an optimality gap on instances where such a benchmark is practical.

This benchmark is valuable academically, but it should remain an evaluation tool rather than becoming a dependency of the lightweight operational solver.

## Scope Statement

A concise statement for the report and presentation is:

> This project develops and evaluates a computationally efficient heuristic 3D cartonization solver for real operational constraints. The solver optimizes carton count but does not guarantee a globally optimal packing for arbitrary instances. Instead, it prioritizes valid solutions, practical runtime, modularity and measurable packing quality, with stronger optimization methods used where appropriate for comparison and validation.

## References

1. Martello, S., Pisinger, D., & Vigo, D. (2000). The Three-Dimensional Bin Packing Problem. *Operations Research, 48*(2), 256 to 267. https://doi.org/10.1287/opre.48.2.256.12386
2. Lodi, A., Martello, S., & Vigo, D. (2002). Heuristic algorithms for the three-dimensional bin packing problem. *European Journal of Operational Research, 141*(2), 410 to 420. https://doi.org/10.1016/S0377-2217(02)00134-0
3. Færø, O., Pisinger, D., & Zachariasen, M. (2003). Guided Local Search for the Three-Dimensional Bin-Packing Problem. *INFORMS Journal on Computing, 15*(3), 267 to 283. https://doi.org/10.1287/ijoc.15.3.267.16080
4. Crainic, T. G., Perboli, G., & Tadei, R. (2008). Extreme Point-Based Heuristics for Three-Dimensional Bin Packing. *INFORMS Journal on Computing, 20*(3), 368 to 384. https://doi.org/10.1287/ijoc.1070.0250
5. Miyazawa, F. K., & Wakabayashi, Y. (2003). The Three-Dimensional Bin Packing Problem and Its Practical Algorithm. *JSME International Journal Series C, 46*(1), 60 to 66. https://www.jstage.jst.go.jp/article/jsmec/46/1/46_1_60/_article
6. 3DBinPacking. (2025). Bin Packing Optimization That Works. https://www.3dbinpacking.com/en/blog/bin-packing-optimization-strategies/
