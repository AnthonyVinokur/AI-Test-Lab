# ATL-A.15.07 — Deterministic Fail-Closed Admission Decision

Produces stable `permitted`, `blocked`, `indeterminate`, or `invalid` semantics and sanitized
reason codes in a fixed order. `permitted` is the only success state; missing, unsupported,
exceptional, and uncertain states cannot create permission.
