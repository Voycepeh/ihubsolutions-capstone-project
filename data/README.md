# Data

Project data is ignored by default unless the team has explicitly approved a development dataset for version control.

## Approved development dataset

The current approved reference dataset is:

```text
data/raw/data_sample_v1.json
```

It contains 2,000 masked real iHub order request and response pairs for benchmarking the team's 3D bin packing solution. `OrderId`, `OrderNo` and item `Code` values are masked, and the supplied dataset documentation states that no PII is included.

The accompanying source documentation is kept at:

```text
data/raw/README.md
```

The repository `.gitignore` continues to ignore other files under `data/` by default. Only explicitly approved development datasets should be added as exceptions.

Do not commit raw production data, unmasked data, confidential data, PII, credentials or other sensitive material.

For the dataset fields, carton catalog, packing parameters and interpretation rules, see [`../docs/dataset-specification.md`](../docs/dataset-specification.md).
