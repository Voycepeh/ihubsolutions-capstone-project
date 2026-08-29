# Data

Project datasets stay local and are not committed to GitHub.

The current reference dataset is `data_sample_v1.json`, containing 2,000 masked real iHub order request and response pairs for benchmarking the team's 3D bin packing solution.

Place the local source file under:

```text
data/raw/
```

The repository `.gitignore` excludes data files while allowing README instruction files to remain tracked.

For the dataset fields, carton catalog, packing parameters and interpretation rules, see [`../docs/dataset-specification.md`](../docs/dataset-specification.md).
