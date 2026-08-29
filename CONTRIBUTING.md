# Contributing

This is a data and optimization capstone project, so keep the workflow simple and keep the supplied iHub data local.

## First time setup

1. Clone the repository.
2. Open it in your IDE, for example VS Code.
3. Create a local Python environment if needed.
4. Place the provided `data_sample_v1.json` file in `data/raw/`.
5. Install the packages listed in `requirements.txt`.

Expected local structure:

```text
project-root/
├── data/
│   └── raw/
│       └── data_sample_v1.json
├── notebooks/
├── src/
├── deployment/
└── docs/
```

## Where work belongs

| Work | Folder |
| --- | --- |
| Local datasets | `data/` |
| Exploration and solver experiments | `notebooks/` |
| Reusable solver and validation code | `src/` |
| Demo application or API | `deployment/` |
| Specifications, reports, presentation material and design notes | `docs/` |

## Data rule

Do not upload or commit the supplied JSON dataset or any derived order level datasets.

Although the supplied file contains masked identifiers and no PII, it is based on real iHub order data and should remain local. The repository `.gitignore` is configured to ignore data files.

Before committing, check that only project code, notebooks, documentation and other approved artifacts are included.

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
