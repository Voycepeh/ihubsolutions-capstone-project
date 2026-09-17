# Documentation

This folder contains the project specifications, design notes, evaluation material, reports and presentation assets for the iHub 3D bin packing capstone.

## Documentation style

Use [`TERMINOLOGY.md`](TERMINOLOGY.md) as the shared language guide.

Technical packing terms should be defined once when they first matter, then the rest of the documentation should use the simpler explanation. For example, define **Empty Maximal Space** once, then say **remaining empty space**. Define **Extreme Point** once, then say **candidate position**.

Keep exact technical wording where it is genuinely needed, such as research-paper titles, citations, algorithm references or code identifiers.

## Current references

- [`../src/PRODUCT_SPEC.md`](../src/PRODUCT_SPEC.md) is the functional source of truth for solver behavior, module responsibilities, tests and acceptance gates.
- [`TERMINOLOGY.md`](TERMINOLOGY.md) defines technical terms and their preferred plain-language wording.
- [`dataset-specification.md`](dataset-specification.md) documents the supplied benchmark dataset, including the request and response schema, candidate cartons, packing constraints, privacy notes and dataset limitations.
- [`solver-approach-and-literature.md`](solver-approach-and-literature.md) records the literature rationale and how those ideas map to the selected solver design.

As the project develops, keep major design decisions and evaluation methodology documented here so the implementation and final report remain traceable to the agreed project rules.
