# Contributing

This is a data and optimization capstone project, so keep the workflow simple.

## First time setup

1. Clone the repository.
2. Open it in your IDE, for example VS Code.
3. Create a local Python environment if needed.
4. The approved benchmark dataset is available at `data/raw/data_sample_v1.json` once it has been added to the repository.
5. Install the packages listed in `requirements.txt`.

Expected structure:

```text
project-root/
├── data/
│   └── raw/
│       ├── README.md
│       └── data_sample_v1.json
├── notebooks/
├── src/
├── deployment/
└── docs/
```

## Where work belongs

| Work | Folder |
| --- | --- |
| Approved development datasets and local datasets | `data/` |
| Exploration and solver experiments | `notebooks/` |
| Reusable solver and validation code | `src/` |
| Demo application or API | `deployment/` |
| Specifications, reports, presentation material and design notes | `docs/` |

## Data rule

The supplied `data_sample_v1.json` benchmark is an explicitly approved development dataset for this repository. The source documentation states that `OrderId`, `OrderNo` and item `Code` are masked and that no PII is included.

Other data remains ignored by default. Do not commit raw production data, unmasked data, confidential data, PII, credentials or derived order level datasets unless the team has explicitly reviewed and approved them for version control.

Before committing, check that any new data file is intentionally approved rather than relying on a broad `.gitignore` exception.

## Packing logic

Before changing solver logic, read [`docs/dataset-specification.md`](docs/dataset-specification.md).

The implementation must account for the reference constraints, especially `VerticalRotation`, carton maximum weight, `BinMaxFillCheckMinItemQty`, `BinMaxFillPct` and `BinBuffer`.

Do not assume that matching the reference carton choice exactly is the only valid result. Multiple valid packing arrangements may exist. Benchmarking should distinguish feasibility, constraint compliance and optimization quality.

## Testing

The provided 2,000 records are all successful cases with no unpacked items. Add deliberate edge and failure cases as the solver develops.

When recording results, do not claim a test, benchmark or performance result unless it was actually run.

## Team workflow

Use your own branch for changes where practical and submit work back through a pull request. Keep changes focused and do not overwrite another teammate's work without agreement.

Never commit passwords, tokens, API keys or other secrets.

AI assisted work must be reviewed, understood and validated by a human teammate before submission. AI agents must follow [`AGENTS.md`](AGENTS.md).
