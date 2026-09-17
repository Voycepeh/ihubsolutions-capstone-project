# Documentation

The root README stays intentionally short. Detailed behavior is split into focused documents here.

## Core product docs

| Document | Purpose |
| --- | --- |
| [`API.md`](API.md) | Request/response schemas, field types and FastAPI/OpenAPI direction |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Package structure, module boundaries and end-to-end flow |
| [`CONFIGURATION.md`](CONFIGURATION.md) | Runtime packing rules and defaults |
| [`TESTING.md`](TESTING.md) | Unit-test strategy and milestone test cases |
| [`ROADMAP.md`](ROADMAP.md) | Staged delivery from MVP 0 through later optimization |
| [`../src/PRODUCT_SPEC.md`](../src/PRODUCT_SPEC.md) | Detailed engineering source of truth |

## Supporting references

| Document | Purpose |
| --- | --- |
| [`TERMINOLOGY.md`](TERMINOLOGY.md) | Define technical packing terms once, then use plain language |
| [`solver-approach-and-literature.md`](solver-approach-and-literature.md) | Algorithm rationale and research references |
| [`dataset-specification.md`](dataset-specification.md) | Supplied benchmark dataset, fields and constraints |
| [`../data/raw/CHANGELOG.md`](../data/raw/CHANGELOG.md) | Benchmark dataset version history |

## Documentation rule

Keep each file focused on one concern. Do not grow the root README into the product specification.

Technical terms should be introduced accurately once and then replaced with simpler wording in normal explanation. Keep exact terminology only where it is required for research references, API field names or code identifiers.
