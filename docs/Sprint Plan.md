# Sprint Plan

## Project Goal

Deliver an MVP 3D bin-packing / cartonization solution that accepts order and box information, applies the required packing constraints, minimizes the number of boxes used, and returns an explainable packing result.

The core solution should be implemented as reusable Python modules and functions first. A simple script interface can be used for the MVP, with FastAPI added as a thin service layer once the core solver is stable.

## Tentative Sprint Timeline

| Sprint | Focus | MVP Deliverable |
|---|---|---|
| Sprint 0 | Data and requirements understanding | Initial EDA, constraints documented, reference benchmark established |
| Sprint 1 | Core data structures and validation | Orders, items, boxes, quantities, rotations and configuration represented cleanly in Python |
| Sprint 2 | Single-box packing | Solver can determine whether an order fits in one candidate box and return valid placements |
| Sprint 3 | Multi-box optimization | Solver supports multiple cartons and minimizes total box count |
| Sprint 4 | Business constraints and benchmarking | 70% fill rule, buffer, weight, rotation rules and reference comparison implemented |
| Sprint 5 | MVP packaging and API | Clean Python interface, tests, documentation and optional FastAPI endpoint |

## Sprint 0 — Data and Requirements

### Objectives

- Understand the supplied request / response dataset
- Confirm the available carton catalogue
- Understand item dimensions, quantity, weight and rotation fields
- Establish the current iHub service as a reference benchmark
- Separate historical behaviour from new requirements
- Agree on evaluation metrics

### Deliverables

- Initial EDA notebook
- Initial solver requirements list
- Reference benchmark metrics
- Identified clarification points for iHub

## Sprint 1 — Solver Foundation

### Objectives

Build the reusable Python foundation before implementing the 3D packing heuristic.

Suggested structure:

```text
src/
├── models/
│   ├── item.py
│   ├── box.py
│   └── order.py
├── constraints/
│   ├── rotation.py
│   ├── weight.py
│   ├── fill.py
│   └── buffer.py
└── solver/
    └── ...
```

### Core Features

- Item dimensions
- Item quantity
- Item weight
- Candidate box catalogue
- Allowed item orientations
- `VerticalRotation` handling
- Maximum box weight
- Configurable fill percentage
- Configurable fill threshold
- Configurable box buffer
- Input validation

### Sprint Outcome

Given an order and a candidate box, the application can determine whether the combination is potentially feasible based on the configured constraints.

## Sprint 2 — Single-Box 3D Packing

### Objectives

Implement the core geometric packing engine.

The solver should attempt to place all physical items into a single candidate carton while respecting dimensions, orientation and collision constraints.

### Core Features

- 3D item coordinates: `x`, `y`, `z`
- Item orientation
- Boundary checking
- Collision / overlap checking
- Quantity expansion
- Packing order heuristic, for example larger items first
- Valid single-box result

### Suggested Acceptance Target

Evaluate the solver against the supplied single-box reference cases and measure the proportion that can be reproduced with valid packing solutions.

## Sprint 3 — Multi-Box Packing and Carton Selection

### Objectives

Extend the single-box engine into a cartonization optimizer.

### Core Features

- Try available candidate cartons
- Determine whether one carton is sufficient
- Allocate items across multiple cartons when necessary
- Minimize total number of cartons
- Return all carton assignments

### Primary Objective

Minimize the number of boxes used.

### Possible Secondary Tie-Breakers

These should not block the MVP but can be considered once the primary objective works:

- Smaller total carton volume
- Higher volumetric utilization
- Fewer different carton types

### Sprint Outcome

The solver can handle both single-box and multi-box orders.

## Sprint 4 — Business Rules and Benchmarking

### Objectives

Ensure the solver satisfies the supplied business requirements rather than simply reproducing historical iHub output.

### Required Constraints

- Maximum box weight of 20 kg
- Upright-only items remain upright
- Configurable box buffer
- Configurable maximum fill percentage
- Configurable item-count threshold for the fill rule
- Correct handling of item quantities

The current requirement indicates a 70% maximum fill for orders above the configured threshold. This appears intended to leave sufficient free space for practical packing and avoid excessively tight arrangements.

### Benchmarking

Run the sample orders through our solver and compare results against the iHub reference output.

Suggested metrics:

| Metric | Description |
|---|---|
| Feasibility rate | Percentage of orders where every item is validly packed |
| Exact bin-count match | Percentage matching the reference number of cartons |
| Better than reference | Orders using fewer cartons than the reference |
| Worse than reference | Orders using more cartons than the reference |
| Selected-box match | Exact carton-code match rate |
| Space utilization | Average volumetric utilization |
| Constraint compliance | Weight, rotation, fill and buffer rules |
| Runtime | Median, P95 and maximum solver runtime |

## Sprint 5 — MVP Packaging and API

### Objectives

Package the solver as a reusable component that can be called by different interfaces.

The core solver should remain normal Python code rather than embedding packing logic directly inside an API implementation.

### Target Python Interface

```python
result = solve_order(order, boxes, config)
```

A simple command-line or script interface can be provided first:

```text
python main.py sample_order.json
```

### Example Result

```json
{
  "status": "success",
  "bins_used": 1,
  "bins": [
    {
      "code": "Box5",
      "used_space": 62.3,
      "weight": 4.2,
      "items": []
    }
  ]
}
```

### Optional FastAPI Layer

Once the Python solver is stable, expose the same reusable engine through an API endpoint such as:

```text
POST /pack
```

FastAPI should act as a thin wrapper that:

- accepts JSON input
- validates the request
- calls the underlying solver
- returns the solver result

The packing algorithm should remain reusable outside FastAPI.

## MVP Boundary

The MVP should focus on the packing engine and its reusable interface.

### In Scope

- Reusable Python solver
- Configurable box catalogue
- Configurable packing rules
- Single-box packing
- Multi-box packing
- Constraint validation
- Explainable result output
- Benchmarking against the supplied sample
- Script interface
- Optional FastAPI demonstration

### Not Required for the Initial MVP

- Production authentication
- Database integration
- User interface
- Cloud infrastructure
- Kubernetes
- Enterprise deployment architecture

## Design Direction for the Next Phase

The intended architecture should be configuration-driven and reusable.

A user should be able to provide:

- order data, for example JSON or CSV
- a list of available boxes
- configurable packing parameters

The underlying engine should handle the packing logic while allowing selected behaviour to be changed through configuration rather than requiring users to modify solver code.

Conceptually:

```text
Order data + Box catalogue + Configuration
                  ↓
          Reusable packing engine
                  ↓
        Packing result / API response
```

The next design step should define the feature requirements, supported configuration parameters, input / output contracts, and a simple solution flow showing how the script and FastAPI interfaces use the same underlying engine.
