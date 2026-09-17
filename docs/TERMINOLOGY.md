# Packing Terminology

This page defines the technical terms used by the project once. After a term is introduced here, the rest of the repository should prefer the simpler wording shown in the final column unless the exact technical term is required for literature review or implementation detail.

| Technical term | What it means | Prefer in normal documentation |
| --- | --- | --- |
| **Empty Maximal Space** | A rectangular region of usable empty space remaining inside a carton after items have been placed. | **remaining empty space** or **empty rectangular space** |
| **Extreme Point** | A meaningful placement position created from carton boundaries or the faces of items already packed. It lets the solver test useful locations instead of every XYZ coordinate. | **candidate position** or **possible placement position** |
| **Heuristic** | A practical rule-based method that aims to find a good solution quickly without proving the mathematically best possible solution. | **packing strategy**, **method**, or **approach** |
| **Axis-aligned placement** | An item is kept parallel to the carton X, Y and Z axes rather than placed diagonally. | **90-degree placement** or **allowed orientation** |
| **Cuboid** | A rectangular box-shaped item with length, width and height. | **rectangular item** |
| **Feasible** | A carton or placement passes the required checks and is possible to try or use. | **possible**, **can fit**, or **valid** |
| **Pruning** | Removing spaces or options that can no longer be useful. | **remove unusable spaces/options** |
| **Collision detection** | Checking whether two packed items occupy the same 3D space. | **overlap check** |
| **Volumetric utilization** | The percentage of carton volume occupied by packed items. | **space utilization** |
| **Deterministic** | The same input and settings produce the same result each time. | Use the technical term once, then explain as **same input gives the same result** when useful. |
| **Lexicographic scoring** | Comparing placement preferences in a fixed order, such as lower height first, then tighter fit, then coordinates. | **compare priorities in order** |
| **Multi-start search** | Running the solver several times with different item orders or starting choices. | **try several starting orders** |
| **Backtracking / depth-first search** | Reversing earlier placement choices and trying alternatives when a later item cannot fit. | **go back and try a different earlier placement** |
| **Voxel / voxelization** | Representing items and cartons as a 3D grid of small cells. | **3D grid cells** |
| **Fast Fourier Transform (FFT)** | A mathematical technique used by some advanced voxel-based packing methods to speed up placement searches. | Keep the full term only in literature/future-work discussion. |
| **P95 latency** | The time within which 95% of orders finish. | **95% of orders finish within this time** |
| **Global optimum** | The mathematically best possible packing across all possible solutions. | **mathematically best possible packing** |

## Documentation rule

Use the real technical term when it first matters, explain it in plain English, then switch to the simpler wording for the rest of the page.

For example:

> **Empty Maximal Space** is the technical term for a useful rectangular region of empty space remaining inside a carton. From this point onward, we call these **remaining empty spaces**.

And:

> An **Extreme Point** is a useful candidate position created from carton or packed-item boundaries. From this point onward, we call these **candidate positions**.

Research-paper titles, citations, code identifiers that already exist, and exact algorithm names may keep their technical wording.