# Best speed-ups: large synthetic orders (5 carton types, 60 s cap)

Cases: 24

| Stage | Change | Median ms | Mean ms | P95 ms | Max ms | Total s | Not proven (time limit) | Objective differs from S0 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| S0 | Current Best (no speed-ups) | 13650.98 | 18343.92 | 59584.97 | 62181.47 | 440.25 | 2 | 0 |
| S1 | + #5 Start from Fast's layout | 13097.63 | 15512.07 | 28006.14 | 62707.69 | 372.29 | 1 | 0 |
| S2 | + #1 Don't redo Fast's work | 161.59 | 8796.33 | 28225.85 | 61611.82 | 211.11 | 1 | 0 |
| S3 | + #3 Identical cartons | 176.43 | 8463.16 | 27670.04 | 60306.94 | 203.12 | 1 | 0 |
| S4 | + #2 Identical items | 162.63 | 8168.06 | 29638.41 | 60179.13 | 196.03 | 1 | 0 |
| S5 | + #4 Impossible pairs (all on) | 237.55 | 8089.75 | 31106.02 | 38904.42 | 194.15 | 0 | 0 |

Median runtime (ms) by order size

| Order | S0 | S1 | S2 | S3 | S4 | S5 | S0 → S5 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 30 items, distinct | 360.4 | 1,195.9 | 120.6 | 122.9 | 124.4 | 106.6 | 3.4× |
| 50 items, distinct | 26,119.8 | 26,222.9 | 25,971.4 | 16,576.6 | 10,242.7 | 25,523.1 | 1.0× |
| 75 items, distinct | 10,972.5 | 8,835.8 | 154.3 | 153.8 | 154.6 | 154.6 | 71.0× |
| 100 items, distinct | 19,098.9 | 22,532.1 | 18,409.1 | 20,966.0 | 21,179.1 | 21,255.3 | 0.9× |
| 30 items, repeated | 1,825.8 | 1,862.6 | 37.8 | 39.4 | 42.6 | 42.2 | 43.3× |
| 50 items, repeated | 14,931.2 | 16,676.0 | 6,867.3 | 6,891.6 | 7,846.1 | 7,933.6 | 1.9× |
| 75 items, repeated | 16,565.1 | 12,362.2 | 97.3 | 95.0 | 95.0 | 91.8 | 180.5× |
| 100 items, repeated | 24,039.8 | 23,297.6 | 603.8 | 605.6 | 583.5 | 590.4 | 40.7× |
