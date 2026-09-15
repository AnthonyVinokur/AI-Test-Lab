# ATL-A.07.03 — Authorized Ledger Selection

Selects only existing entries from a verified A.06 chain and provides a fail-closed
authorization callback boundary. Empty, missing, corrupt, unauthorized, or
non-self-contained selections are rejected rather than silently weakened.
