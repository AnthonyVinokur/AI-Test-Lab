# ATL-A.15.08 — Atomic Permit Consumption and Enforcement Receipt

Adds a thread-safe reference state-store adapter that atomically enforces single-use,
idempotent retry, and concurrent-consumer behavior. Successful admission creates a frozen,
content-digested receipt proving what was permitted, not that deployment occurred.
