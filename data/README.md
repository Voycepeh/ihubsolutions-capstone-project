# Data

This project uses development datasets that may be committed to the repository so the team can work from the same reproducible inputs.

## Reference development dataset

The current reference dataset is:

```text
data/raw/data_sample_v1.json
```

It contains 2,000 masked real iHub order request and response pairs for benchmarking the team's 3D bin packing solution. `OrderId`, `OrderNo` and item `Code` values are masked, and the supplied dataset documentation states that no PII is included.

The accompanying source documentation is kept at:

```text
data/raw/README.md
```

Additional development datasets created for testing, edge cases or benchmarking may also be stored under `data/` where appropriate.

Do not commit production data, unmasked data, confidential or restricted data, PII, credentials, secrets or any dataset the team is not authorised to place in this repository.

For the dataset fields, carton catalog, packing parameters and interpretation rules, see [`../docs/dataset-specification.md`](../docs/dataset-specification.md).
