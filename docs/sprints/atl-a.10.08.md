# ATL-A.10.08 — Freshness, Replay, and Rollback Protection

Adds deterministic status snapshots bound to the environment, exact identity, observation time,
authoritative chain length, and chain head. A once-valid but older `active` snapshot, shortened chain,
substituted status, cross-environment response, or manipulated observation time fails freshness.
