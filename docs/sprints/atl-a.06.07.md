# ATL-A.06.07 — Duplicate, Replay, and Conflict Handling

Identical retries return the existing entry as `already_recorded`. Duplicate evidence,
reused admissions, stale-head branches, mismatched chains, and sequence conflicts receive
distinct stable reasons. No conflicting operation mutates the ledger.
