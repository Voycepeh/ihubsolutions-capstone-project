# Full benchmark audit

This audit preserves the complete 2,000-order benchmark as CSV, then uses a separate notebook to inspect the policy exceptions and Best wins.

The review flow is:

1. Read the preserved 2,000-row CSV.
2. Flag iHub rows that violate the supplied packing policy.
3. Confirm Best has no policy-compliant losses.
4. Filter to the 67 policy-compliant orders where Best beats iHub.
5. Select any winning Order ID and show why Best wins, the original item constraints, the validated XYZ packing plan, and the 3D visualization.

The comparison remains lexicographic: fewer cartons, then smaller largest carton, then lower total carton volume.

The generated CSV is committed so the audit notebook remains a read-only analysis layer.
