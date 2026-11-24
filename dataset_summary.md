# Best speed-ups: 2,000 iHub orders (5 s Best budget)

Cases: 2000

| Stage | Change | Median ms | Mean ms | P95 ms | Max ms | Total s | Not proven (time limit) | Objective differs from S0 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| S0 | Current Best (no speed-ups) | 44.32 | 228.62 | 1169.62 | 5084.69 | 457.24 | 4 | 0 |
| S1 | + #5 Start from Fast's layout | 43.4 | 219.88 | 1190.98 | 5287.36 | 439.75 | 4 | 0 |
| S2 | + #1 Don't redo Fast's work | 3.95 | 82.89 | 325.33 | 5280.41 | 165.78 | 3 | 0 |
| S3 | + #3 Identical cartons | 3.85 | 79.76 | 291.69 | 5080.27 | 159.53 | 3 | 0 |
| S4 | + #2 Identical items | 3.91 | 67.93 | 304.33 | 5067.81 | 135.86 | 2 | 0 |
| S5 | + #4 Impossible pairs (all on) | 3.72 | 62.66 | 302.41 | 5113.11 | 125.32 | 2 | 0 |
