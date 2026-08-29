# Raw Data

Place the provided `data_sample_v1.json` file in this folder for local analysis and development.

The file contains masked real iHub order data. `OrderId`, `OrderNo` and item `Code` values are masked and no PII is included, but the dataset must still remain local and must not be committed to GitHub.

Expected local path:

```text
data/raw/data_sample_v1.json
```

The supplied sample contains 2,000 request and response pairs from the existing iHub packing service. Use it as reference benchmark data, not as the only test suite.

See [`../../docs/dataset-specification.md`](../../docs/dataset-specification.md) for the full schema and packing constraints.
